"""
Umubyeyi - grounded generation (RAG) core.

Pipeline: detect language -> safety check -> retrieve validated maternal snippets
(MOTHER + KB) -> ask an LLM to answer IN THE USER'S LANGUAGE using ONLY those snippets
-> append disclaimer. Grounding on the validated ENGLISH text (then generating Kinyarwanda)
avoids the machine-translation corruption in the pre-translated answers.

Used by both the Streamlit app and the FastAPI backend (src/api.py).
"""
import json
import os
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


def _build_prompt(query: str, lang: str, snippets) -> str:
    lang_name = "Kinyarwanda" if lang == "rw" else "English"
    facts = "\n".join(f"- {b['answer_en']}" for b, _ in snippets) or "(no specific validated information for this question)"
    return (
        "You are Umubyeyi, a warm, friendly assistant for first-time mothers in Rwanda, focused on "
        "the first 6 months (0-6mo) after giving birth: newborn care, feeding, physical recovery, "
        "and emotional wellbeing.\n"
        "How to respond:\n"
        "- Greetings or small talk (hello, how are you): reply warmly and briefly, then invite her "
        "to ask about her wellbeing or her baby.\n"
        "- Vague feelings or emotional concerns ('I feel weird', sadness, anxiety, exhaustion): "
        "respond with empathy, gently normalize that such feelings are common after birth, ask one "
        "kind clarifying question or suggest talking to a health worker. Never diagnose.\n"
        "- Clinical/medical questions about the mother or baby: answer using ONLY the validated "
        "information below; never invent medical facts or doses. If it is not covered, say you do "
        "not have specific information and suggest a nurse, midwife, or health worker.\n"
        "- OFF-TOPIC questions (e.g. malaria, COVID, farming, politics, school, math, news, anything "
        "not about a postpartum mother or her baby): politely say that is outside what you help with, "
        "and steer back to postpartum support. Do not answer them.\n"
        "- This assistant is for mothers in Rwanda. Do not reference other countries. For anything "
        "location-specific (helplines, clinics, services), advise her to contact her nearest Rwandan "
        "health centre or a local health worker.\n"
        f"- Be brief (1-4 sentences), kind, and reply in {lang_name}.\n\n"
        f"Validated information:\n{facts}\n\n"
        f"Mother's question: {query}\n\n"
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
    for m in (os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-2.5-flash", "gemini-2.0-flash"):
        if m not in seen:
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


def _unavailable_message(lang: str) -> str:
    # shown only if the generative model is not configured — we never serve raw translation drafts
    if lang == "rw":
        return ("Mbabarira, serivisi ntiboneka neza ubu. Ongera ugerageze nyuma gato. "
                "Niba bihutirwa, hamagara 114 cyangwa ugane umukozi w'ubuzima.")
    return ("Sorry, the assistant is not available right now. Please try again shortly. "
            "If it is urgent, call 114 or see a health worker.")


def answer(query: str, force_lang: str = None) -> dict:
    """Return {answer, language, danger, grounded, mode, sources}.
    Generative (Gemini) if a key is set; otherwise extractive (returns the validated answer).
    force_lang ('en'/'rw') overrides auto-detection."""
    lang = force_lang if force_lang in ("en", "rw") else detect_language(query)
    if is_danger(query):
        return {"answer": _crisis_message(lang), "language": lang, "danger": True,
                "grounded": False, "mode": "safety", "sources": []}
    if is_greeting(query):                           # warm hello (works in any mode, no disclaimer)
        return {"answer": _greeting_reply(lang), "language": lang, "danger": False,
                "grounded": False, "mode": "greeting", "sources": []}

    snippets = retrieve(query)
    top, sim = snippets[0] if snippets else (None, 0.0)
    grounded = top is not None and sim >= SIM_GATE

    # The generalizing model (Gemini) is the ONLY responder. We never serve the raw machine-
    # translation drafts (that was the source of "butterflies"). If it is unavailable, say so.
    if not _has_key():
        return {"answer": _unavailable_message(lang), "language": lang, "danger": False,
                "grounded": grounded, "mode": "unavailable", "sources": []}
    try:
        body = _gemini(_build_prompt(query, lang, snippets if grounded else []))
    except Exception:
        return {"answer": _unavailable_message(lang), "language": lang, "danger": False,
                "grounded": grounded, "mode": "unavailable", "sources": []}

    text = f"{body}\n\n{DISCLAIMER.get(lang, DISCLAIMER['en'])}"
    return {"answer": text, "language": lang, "danger": False, "grounded": grounded, "mode": "generative",
            "sources": [{"topic": b["topic"], "source": b["source"], "sim": round(s, 2)}
                        for b, s in snippets]}
