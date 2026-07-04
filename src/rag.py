"""
Umubyeyi - grounded generation (RAG) core. FULLY LOCAL: no external LLM API.

Scope: the EMOTIONAL WELLBEING of first-time mothers in Rwanda in the first 6 months
postpartum (mood, anxiety, overwhelm, loneliness, stress, adjustment, exhaustion, coping,
relationship strain). Acute clinical questions are referred to a health worker.

Pipeline (all local, all our own models):
  detect language -> safety check -> intent router (LogReg) -> retrieve closest VALIDATED
  postpartum snippet -> our fine-tuned generator (flan-t5) rephrases it conversationally
  -> append disclaimer.
Robustness: if the fine-tuned generator is unavailable or produces a poor draft, we fall
back to the VALIDATED retrieved answer (English generated, Kinyarwanda served from the
validated Kinyarwanda text). The chatbot therefore always returns correct, on-domain text
and NEVER calls a commercial API.
"""
import json
import random
import re
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]

# postpartum grounding bank (validated MOTHER + maternalcare pairs); fall back to legacy bank
_BANK_PATH = ROOT / "data" / "grounding_bank_postpartum.json"
if not _BANK_PATH.exists():
    _BANK_PATH = ROOT / "data" / "grounding_bank.json"
BANK = json.loads(_BANK_PATH.read_text(encoding="utf-8"))
LANGDET = joblib.load(ROOT / "models" / "lang_detector.joblib")

GEN_DIR = ROOT / "models" / "umubyeyi-generator"      # our fine-tuned flan-t5 generator
CLF_PATH = ROOT / "models" / "intent_clf.joblib"      # our LogReg intent router

# search over both language phrasings so en and rw queries both match
_SEARCH = [f'{b.get("question_en","")} {b.get("question_rw","")}' for b in BANK]
_VEC = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
_MAT = _VEC.fit_transform(_SEARCH)

SIM_GATE = 0.25          # below this: ask to say more, rather than ground on a weak/off-topic match
RETRIEVE_GATE = 0.30     # at/above this: serve the VALIDATED answer (richer, safest); below: generate
TOP_K = 3
GEN_NOTES = 2            # notes fed to the generator at inference == what it was trained on

HEADER = ("You are Umubyeyi, a warm companion for the emotional wellbeing of first-time mothers "
          "in Rwanda in the first 6 months after birth. Using the validated notes, reply with "
          "warmth and empathy in English.\n")

DISCLAIMER = {
    "rw": "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge.",
    "en": "This is general information, not medical advice. Please talk to a health worker if you are worried.",
}
CRISIS_LINE = "114"
DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby", "harm my baby",
          "kwiyahura", "kwiyica", "guhotora", "kwica umwana"]
# acute medical / baby-care that we refer out rather than answer
CLINICAL = ["bleeding", "haemorrhage", "hemorrhage", "fever", "stitches", "wound", "infection",
            "seizure", "convulsion", "not breathing", "unconscious", "amaraso", "umuriro"]

GREET_WORDS = {"muraho", "mwaramutse", "mwiriwe", "mwiriweho", "murakaza", "bite", "amakuru",
               "hi", "hello", "hey", "hallo", "hola", "yego"}
GREET_PHRASES = ("good morning", "good afternoon", "good evening", "how are you", "muraho",
                 "mwaramutse", "mwiriwe", "amakuru", "murakaza neza", "uraho")


def is_greeting(text: str) -> bool:
    t = re.sub(r"[^\w\s]", " ", text.lower()).strip()
    if not t:
        return False
    had_greet = any(p in t for p in GREET_PHRASES) or any(w in GREET_WORDS for w in t.split())
    if not had_greet:
        return False
    for p in GREET_PHRASES:
        t = t.replace(p, " ")
    # trailing small-talk fillers so "hi friend", "how are you today", "good morning dear" count as greetings
    FILLER = {"mama", "neza", "there", "everyone", "all", "friend", "today", "dear", "sis", "sister",
              "my", "doing", "again", "so", "now", "how", "are", "you", "u", "ur"}
    remaining = [w for w in t.split() if w not in (GREET_WORDS | FILLER)]
    return len(remaining) == 0


# a few warm variants so greetings/small-talk don't repeat the exact same sentence
GREETINGS = {
    "rw": ["Muraho, mama! Nishimiye kuvugana nawe. Ndi hano ku byerekeye uko wiyumva mu mezi 6 ya mbere nyuma yo kubyara. Umeze ute uyu munsi?",
           "Muraho neza, mama. Nishimiye ko uje. Wambwira uko umutima wawe umeze - agahinda, guhangayika, umunaniro, cyangwa ikindi.",
           "Bite, mama? Ndi hano kukumva nta kugucira urubanza. Ni iki wiyumva muri iki gihe?",
           "Mwaramutse, mama. Nishimiye kuba turi kumwe. Wambwira uko byakugendekeye - uko wiyumva?"],
    "en": ["Hello, mama! I'm glad to talk with you. I'm here for how you're feeling in the first 6 months after birth. How are you today?",
           "Hi there, mama. I'm really glad you're here. Tell me how you're feeling - low, worried, tired, or anything on your heart.",
           "Hello, dear. It's good to have you here, and there's no judgement in this space. How is your heart today?",
           "Hi, mama. I'm listening. What's on your mind or weighing on you right now?"],
}


def _greeting_reply(lang: str) -> str:
    return random.choice(GREETINGS.get(lang, GREETINGS["en"]))


def detect_language(text: str) -> str:
    try:
        return LANGDET.predict([text])[0]
    except Exception:
        return "en"


def is_danger(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in DANGER)


def is_clinical(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in CLINICAL)


def retrieve(text: str, k: int = TOP_K):
    sims = cosine_similarity(_VEC.transform([text]), _MAT)[0]
    idx = sims.argsort()[::-1][:k]
    return [(BANK[i], float(sims[i])) for i in idx]


# ------------------------------------------------------------------ our own models (lazy)
_GEN = {"tok": None, "model": None, "tried": False}
_CLF = {"pipe": None, "tried": False}


def _load_generator():
    """Load our fine-tuned flan-t5 once. Returns (tok, model) or (None, None) if unavailable."""
    if _GEN["tried"]:
        return _GEN["tok"], _GEN["model"]
    _GEN["tried"] = True
    try:
        if not GEN_DIR.exists():
            print("[umubyeyi] generator not found -> retrieval-only mode", file=sys.stderr)
            return None, None
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        _GEN["tok"] = AutoTokenizer.from_pretrained(str(GEN_DIR))
        _GEN["model"] = AutoModelForSeq2SeqLM.from_pretrained(str(GEN_DIR))
        print("[umubyeyi] loaded local generator ->", GEN_DIR, file=sys.stderr)
    except Exception as e:
        print(f"[umubyeyi] generator load failed ({type(e).__name__}) -> retrieval-only", file=sys.stderr)
        _GEN["tok"], _GEN["model"] = None, None
    return _GEN["tok"], _GEN["model"]


def _load_router():
    if _CLF["tried"]:
        return _CLF["pipe"]
    _CLF["tried"] = True
    try:
        _CLF["pipe"] = joblib.load(CLF_PATH)
    except Exception:
        _CLF["pipe"] = None
    return _CLF["pipe"]


def route_intent(text: str):
    """Our LogReg router tags the wellness topic (for the pipeline + analytics)."""
    pipe = _load_router()
    if pipe is None:
        return None
    try:
        return str(pipe.predict([text])[0])
    except Exception:
        return None


def _generate_en(query: str, snippets) -> str:
    """Generate an English answer with our fine-tuned model, grounded on the notes.
    Returns a good draft, or "" if the model is unavailable / the draft looks poor."""
    tok, model = _load_generator()
    if model is None:
        return ""
    notes = "\n".join(f"- {b['answer_en']}" for b, _ in snippets[:GEN_NOTES] if b.get("answer_en"))
    prompt = f"{HEADER}Notes:\n{notes}\nMother: {query}\nAnswer:"
    try:
        ids = tok(prompt, return_tensors="pt", truncation=True, max_length=512).input_ids
        out = model.generate(ids, max_new_tokens=200, num_beams=4, no_repeat_ngram_size=3)
        draft = tok.decode(out[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"[umubyeyi] generation error ({type(e).__name__}) -> fallback", file=sys.stderr)
        return ""
    # quality gate: reject empty / too-short / degenerate output so we can fall back to validated text
    words = draft.split()
    if len(words) < 6 or len(set(words)) < len(words) * 0.5:
        return ""
    return draft


def _crisis_message(lang: str) -> str:
    if lang == "rw":
        return ("Ndumva ko ubu uri kunyura mu bihe bikomeye. Ntabwo uri wenyine. Nyamuneka vugana "
                f"n'umuntu wizeye cyangwa umukozi w'ubuzima nonaha, cyangwa uhamagare: {CRISIS_LINE}.")
    return ("It sounds like you are going through something very hard. You are not alone. Please reach "
            f"out to someone you trust or a health worker now, or call: {CRISIS_LINE}.")


def _clinical_message(lang: str) -> str:
    if lang == "rw":
        return ("Umubyeyi afasha ku byerekeye uko wiyumva. Ku bibazo by'umubiri cyangwa umwana "
                "(kuva amaraso, umuriro, ibikomere), nyamuneka ganira n'umuforomo cyangwa umukozi "
                "w'ubuzima vuba. Ese wowe ubwawe wiyumva ute muri iki gihe?")
    return ("Umubyeyi helps with how you are feeling. For physical or baby concerns (bleeding, fever, "
            "wounds), please see a nurse or health worker soon. How are you coping in yourself right now?")


def answer(query: str, force_lang: str = None, history=None) -> dict:
    """Return {answer, language, danger, grounded, mode, intent, sources}. Fully local, no API."""
    lang = force_lang if force_lang in ("en", "rw") else detect_language(query)

    if is_danger(query):
        return {"answer": _crisis_message(lang), "language": lang, "danger": True,
                "grounded": False, "mode": "safety", "intent": "crisis", "sources": []}

    if is_greeting(query):
        return {"answer": _greeting_reply(lang), "language": lang, "danger": False,
                "grounded": False, "mode": "greeting", "intent": "greeting", "sources": []}

    if is_clinical(query):
        return {"answer": _clinical_message(lang), "language": lang, "danger": False,
                "grounded": False, "mode": "referral", "intent": "clinical", "sources": []}

    intent = route_intent(query)                     # our LogReg router tags the wellness topic
    snippets = retrieve(query)
    top, sim = snippets[0] if snippets else (None, 0.0)
    grounded = top is not None and sim >= SIM_GATE

    if not grounded:
        # no confident validated match: stay honest, invite her to say more (never fabricate)
        opts = {"rw": ["Numva ibyo uvuga. Wambwira gato byinshi ku byo wiyumva, kugira ngo ngufashe neza?",
                       "Ndi hano kukumva. Ni iki cyane cyane kigukoraho muri iki gihe?",
                       "Mbwira uko wiyumva mu magambo yawe - agahinda, guhangayika, umunaniro? Ndashaka kugusobanukirwa."],
                "en": ["I hear you. Could you tell me a little more about how you're feeling, so I can help you better?",
                       "I'm here for you. What's weighing on you most right now?",
                       "Tell me in your own words how you're feeling - sad, anxious, overwhelmed, tired? I want to understand."]}
        return {"answer": random.choice(opts.get(lang, opts["en"])), "language": lang, "danger": False,
                "grounded": False, "mode": "clarify", "intent": intent, "sources": []}

    if lang == "rw":
        # serve the VALIDATED Kinyarwanda answer when we have it (higher quality than MT)
        body = (top.get("answer_rw") or "").strip() or (top.get("answer_en") or "").strip()
        mode = "retrieved_rw" if top.get("answer_rw") else "retrieved_en"
    elif sim >= RETRIEVE_GATE:
        # strong match: serve the VALIDATED answer verbatim — richer, warmer, and safest
        body, mode = (top.get("answer_en") or "").strip(), "retrieved"
    else:
        draft = _generate_en(query, snippets)        # novel phrasing: our fine-tuned generator adapts
        if draft:
            body, mode = draft, "generative"
        else:
            body, mode = (top.get("answer_en") or "").strip(), "retrieved"   # validated fallback

    text = f"{body}\n\n{DISCLAIMER.get(lang, DISCLAIMER['en'])}"
    return {"answer": text, "language": lang, "danger": False, "grounded": grounded, "mode": mode,
            "intent": intent,
            "sources": [{"topic": b.get("topic", ""), "source": b.get("source", ""), "sim": round(s, 2)}
                        for b, s in snippets]}
