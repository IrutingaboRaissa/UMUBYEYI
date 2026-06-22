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
# TODO(Raissa): replace with a VERIFIED Rwandan crisis/helpline number before the pilot.
CRISIS_LINE = "[ADD VERIFIED HELPLINE]"
DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby", "harm my baby",
          "kwiyahura", "kwiyica", "guhotora", "kwica umwana"]


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
    facts = "\n".join(f"- {b['answer_en']}" for b, _ in snippets) or "(no closely matching information)"
    return (
        "You are Umubyeyi, a warm, supportive assistant for first-time mothers in Rwanda, "
        "focused ONLY on the 0-6 months postpartum period (newborn care, feeding, physical "
        "recovery, and emotional wellbeing).\n"
        "Rules:\n"
        "1. For CLINICAL/medical questions, use ONLY the validated information below. Never invent "
        "medical facts, doses, or diagnoses.\n"
        "2. If the validated information does not cover a clinical question, gently say you do not "
        "have specific information and encourage speaking to a nurse, midwife, or health worker.\n"
        "3. For EMOTIONAL concerns (sadness, anxiety, feeling overwhelmed), respond with warmth: "
        "validate her feelings, reassure that such feelings are common after birth, give gentle "
        "general encouragement, and suggest talking to someone she trusts or a health worker. "
        "Never diagnose.\n"
        f"4. Be brief (2-4 sentences), kind, and practical. Reply in {lang_name}.\n\n"
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
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    resp = client.models.generate_content(model=model, contents=prompt)
    return (resp.text or "").strip()


def _no_match_message(lang: str) -> str:
    if lang == "rw":
        return ("Mbabarira, nta makuru ahagije mfite kuri icyo kibazo. Nyamuneka ganira "
                "n'umuforomokazi cyangwa umukozi w'ubuzima kugira ngo agufashe.")
    return ("Sorry, I don't have specific information on that. Please talk to a nurse, midwife, "
            "or health worker who can help you.")


def answer(query: str) -> dict:
    """Return {answer, language, danger, grounded, mode, sources}.
    Generative (Gemini) if a key is set; otherwise extractive (returns the validated answer)."""
    lang = detect_language(query)
    if is_danger(query):
        return {"answer": _crisis_message(lang), "language": lang, "danger": True,
                "grounded": False, "mode": "safety", "sources": []}

    snippets = retrieve(query)
    top, sim = snippets[0] if snippets else (None, 0.0)
    grounded = top is not None and sim >= SIM_GATE

    if _has_key():                                   # generative, grounded
        body = _gemini(_build_prompt(query, lang, snippets if grounded else []))
        mode = "generative"
    elif grounded:                                   # no key -> return the validated answer directly
        body = top["answer_rw"] if lang == "rw" else top["answer_en"]
        mode = "retrieval"
    else:                                            # no key, no good match
        body = _no_match_message(lang)
        mode = "retrieval"

    text = f"{body}\n\n{DISCLAIMER.get(lang, DISCLAIMER['en'])}"
    return {"answer": text, "language": lang, "danger": False, "grounded": grounded, "mode": mode,
            "sources": [{"topic": b["topic"], "source": b["source"], "sim": round(s, 2)}
                        for b, s in snippets]}
