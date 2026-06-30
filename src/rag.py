"""
Umubyeyi - grounded generation (RAG) core.

Scope: the EMOTIONAL WELLBEING of first-time mothers in Rwanda in the first 6 months
postpartum (mood, anxiety, overwhelm, loneliness, stress, adjustment, exhaustion, coping,
relationship strain). Clinical and baby-care questions are referred to a health worker.

Pipeline: detect language -> safety check -> retrieve the closest validated counselling
snippets (Amod counselling corpus + MOTHER emotional pairs) -> ask an LLM to answer IN THE
USER'S LANGUAGE grounded on those snippets -> append disclaimer. Grounding on the validated
ENGLISH text (then generating Kinyarwanda) avoids machine-translation corruption.
"""
import json
import os
import sys
import re
from pathlib import Path

import joblib
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]

BANK = json.loads((ROOT / "data" / "grounding_bank.json").read_text(encoding="utf-8"))
LANGDET = joblib.load(ROOT / "models" / "lang_detector.joblib")

# search over both language phrasings so en and rw queries both match
_SEARCH = [f'{b["question_en"]} {b["question_rw"]}' for b in BANK]
_VEC = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
_MAT = _VEC.fit_transform(_SEARCH)

SIM_GATE = 0.18          # below this we tell the LLM "no specific match -> be cautious"
TOP_K = 3

DISCLAIMER = {
    "rw": "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge.",
    "en": "This is general information, not medical advice. Please talk to a health worker if you are worried.",
}
CRISIS_LINE = "114"  # Rwanda health emergency line
DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby", "harm my baby",
          "kwiyahura", "kwiyica", "guhotora", "kwica umwana"]

GREET_WORDS = {"muraho", "mwaramutse", "mwiriwe", "mwiriweho", "murakaza", "bite", "amakuru",
               "hi", "hello", "hey", "hallo", "hola", "yego"}
GREET_PHRASES = ("good morning", "good afternoon", "good evening", "how are you", "muraho",
                 "mwaramutse", "mwiriwe", "amakuru", "murakaza neza", "uraho")


def is_greeting(text: str) -> bool:
    """True only for a PURE greeting -- if a real question follows, let it be answered."""
    t = re.sub(r"[^\w\s]", " ", text.lower()).strip()
    if not t:
        return False
    had_greet = any(p in t for p in GREET_PHRASES) or any(w in GREET_WORDS for w in t.split())
    if not had_greet:
        return False
    for p in GREET_PHRASES:                       # strip greeting phrases, then words
        t = t.replace(p, " ")
    remaining = [w for w in t.split() if w not in (GREET_WORDS | {"mama", "neza"})]
    return len(remaining) == 0                    # greeting only if nothing substantive is left


def _greeting_reply(lang: str) -> str:
    if lang == "rw":
        return ("Muraho, mama! Nishimiye kuvugana nawe. Ndi hano kugufasha ku byerekeye uko wiyumva "
                "cyangwa umwana wawe mu mezi 6 ya mbere nyuma yo kubyara. Wambwira icyo nakumarira?")
    return ("Hello, mama! I'm glad to talk with you. I'm here to help with how you're feeling or your "
            "baby in the first 6 months after birth. How can I help you today?")


def detect_language(text: str) -> str:
    try:
        return LANGDET.predict([text])[0]
    except Exception:
        return "en"


def is_danger(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in DANGER)


def retrieve(text: str, k: int = TOP_K):
    sims = cosine_similarity(_VEC.transform([text]), _MAT)[0]
    idx = sims.argsort()[::-1][:k]
    return [(BANK[i], float(sims[i])) for i in idx]


def _build_prompt(query: str, lang: str, snippets, history=None) -> str:
    lang_name = "Kinyarwanda" if lang == "rw" else "English"
    facts = "\n".join(f"- {b['answer_en']}" for b, _ in snippets) or "(no specific validated information for this question)"
    convo = ""
    if history:
        turns = [("Mother" if h.get("role") == "user" else "Assistant", (h.get("text") or "").strip())
                 for h in history[-6:] if (h.get("text") or "").strip()]
        if turns:
            convo = ("Conversation so far (most recent last) — use it for context, do not repeat yourself:\n"
                     + "\n".join(f"{who}: {t}" for who, t in turns) + "\n\n")
    return (
        "You are Umubyeyi, a warm companion for the EMOTIONAL WELLBEING of first-time mothers in "
        "Rwanda during the first 6 months (0-6mo) after giving birth. You focus ONLY on how she is "
        "feeling: sadness and low mood, anxiety and worry, feeling overwhelmed, changes in identity, "
        "loneliness, stress, adjusting to motherhood, exhaustion and sleep-related distress, coping, "
        "and relationship strain. You are NOT a medical or baby-care advisor.\n"
        "How to respond:\n"
        "- Greetings or small talk (hello, how are you): reply warmly and briefly, then gently invite "
        "her to share how she is feeling.\n"
        "- Feelings and emotional concerns (sadness, anxiety, overwhelm, loneliness, exhaustion, "
        "stress, adjustment, relationship strain): respond with warmth and empathy, gently normalize "
        "that such feelings are common after birth, draw on the validated counselling information "
        "below, and offer one kind, practical coping suggestion or one caring clarifying question. "
        "Never diagnose; if distress seems heavy, gently suggest talking to a health worker or someone "
        "she trusts.\n"
        "- CLINICAL or baby-care questions (feeding, breastfeeding, the baby's health, fever, crying, "
        "the cord, bleeding, wounds, stitches, physical recovery, medicines, doses): do NOT answer "
        "these. Warmly explain that you focus on how she is feeling emotionally, and that for medical "
        "or baby-care questions she should see a nurse, midwife, or health worker. Then invite her "
        "back to how she is coping.\n"
        "- OFF-TOPIC questions (malaria, COVID, farming, politics, school, math, news, anything not "
        "about a postpartum mother's emotional wellbeing): politely say that is outside what you help "
        "with, and steer back to how she is feeling. Do not answer them.\n"
        "- This companion is for mothers in Rwanda. Do not reference other countries. For anything "
        "location-specific (helplines, clinics, services), advise her to contact her nearest Rwandan "
        "health centre or a local health worker.\n"
        f"- Be brief (1-4 sentences), warm, and reply in {lang_name}.\n"
        "- Do NOT add your own disclaimer or 'this is general information / not medical advice' note; "
        "a disclaimer is appended automatically.\n\n"
        f"Validated counselling information:\n{facts}\n\n"
        f"{convo}"
        f"The mother now says: {query}\n\n"
        f"Your answer (in {lang_name}):"
    )


def _crisis_message(lang: str) -> str:
    if lang == "rw":
        return ("Ndumva ko ubu uri kunyura mu bihe bikomeye. Ntabwo uri wenyine. Nyamuneka vugana "
                f"n'umuntu wizeye cyangwa umukozi w'ubuzima nonaha, cyangwa uhamagare: {CRISIS_LINE}.")
    return ("It sounds like you are going through something very hard. You are not alone. Please reach "
            f"out to someone you trust or a health worker now, or call: {CRISIS_LINE}.")


def _has_key() -> bool:
    k = os.environ.get("GEMINI_API_KEY")
    return bool(k) and k != "your-gemini-api-key-here"


def _gemini(prompt: str) -> str:
    """Generate, resilient to transient 503/429: retry with backoff across a few models."""
    import time
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    models, seen = [], set()
    for m in (os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), "gemini-2.5-flash",
              "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        if m and m not in seen:
            seen.add(m); models.append(m)
    last = None
    for attempt in range(3):
        for m in models:
            try:
                txt = (client.models.generate_content(model=m, contents=prompt).text or "").strip()
                if txt:
                    return txt
            except Exception as e:
                last = e
        time.sleep(1.2 * (attempt + 1))
    raise last if last else RuntimeError("empty response")


_DISCLAIMER_MARKERS = (
    "general information", "not medical advice", "talk to a health worker",
    "amakuru rusange", "si inama z'ubuvuzi", "vugana n'umuganga",
)


def _strip_disclaimer(text: str) -> str:
    """Remove a trailing disclaimer the model may have added, so we don't show it twice."""
    lines = [ln for ln in text.strip().splitlines()]
    while lines:
        low = lines[-1].lower()
        if low.strip() and any(m in low for m in _DISCLAIMER_MARKERS):
            lines.pop()
        else:
            break
    return "\n".join(lines).strip()


def _unavailable_message(lang: str) -> str:
    # temporary generation hiccup (e.g. model busy) — honest, not a policy refusal, not raw drafts
    if lang == "rw":
        return ("Mbabarira, sinabashije gutegura igisubizo kuri ubu. Ongera ugerageze nyuma y'akanya gato. "
                "Niba bihutirwa cyangwa ufite impungenge, hamagara 114 cyangwa ugane umukozi w'ubuzima.")
    return ("Sorry, I couldn't put together an answer just now — please try again in a moment. "
            "If it's urgent or you're worried, call 114 or see a health worker.")


def answer(query: str, force_lang: str = None, history=None) -> dict:
    """Return {answer, language, danger, grounded, mode, sources}.
    The generalizing model (Gemini) is the responder; `history` (recent turns) gives it context so
    it stays coherent and does not loop. force_lang ('en'/'rw') overrides auto-detection."""
    lang = force_lang if force_lang in ("en", "rw") else detect_language(query)
    if is_danger(query):                             # deterministic safety path, independent of the model
        return {"answer": _crisis_message(lang), "language": lang, "danger": True,
                "grounded": False, "mode": "safety", "sources": []}

    snippets = retrieve(query)                       # greetings/small talk fall through to the model (with history)
    top, sim = snippets[0] if snippets else (None, 0.0)
    grounded = top is not None and sim >= SIM_GATE

    # The generalizing model (Gemini) is the ONLY responder. We never serve the raw machine-
    # translation drafts (that was the source of "butterflies"). If it is unavailable, say so.
    if not _has_key():
        print("[umubyeyi] GEMINI_API_KEY missing in environment -> fallback", file=sys.stderr, flush=True)
        return {"answer": _unavailable_message(lang), "language": lang, "danger": False,
                "grounded": grounded, "mode": "unavailable", "sources": []}
    try:
        body = _gemini(_build_prompt(query, lang, snippets if grounded else [], history))
    except Exception as e:
        print(f"[umubyeyi] generation failed -> {type(e).__name__}: {str(e)[:300]}", file=sys.stderr, flush=True)
        return {"answer": _unavailable_message(lang), "language": lang, "danger": False,
                "grounded": grounded, "mode": "unavailable", "sources": []}

    body = _strip_disclaimer(body)                    # drop any disclaimer the model added; we append the canonical one
    text = f"{body}\n\n{DISCLAIMER.get(lang, DISCLAIMER['en'])}"
    return {"answer": text, "language": lang, "danger": False, "grounded": grounded, "mode": "generative",
            "sources": [{"topic": b["topic"], "source": b["source"], "sim": round(s, 2)}
                        for b, s in snippets]}
