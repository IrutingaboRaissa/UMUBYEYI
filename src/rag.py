"""
Umubyeyi — grounded generation (RAG) core, object-oriented. FULLY LOCAL: no external LLM API.

Scope: the EMOTIONAL WELLBEING of first-time mothers in Rwanda in the first 6 months
postpartum. Acute clinical questions are referred to a health worker.

`UmubyeyiRAG` encapsulates the whole pipeline — the validated bank, the three models we
trained (language detector, LogReg intent router, fine-tuned flan-t5 generator), and the
response policy — behind a single `answer()` method:

    language -> safety -> greeting -> clinical referral -> intent router -> retrieval
    -> OUR flan-t5 generates the English answer (Kinyarwanda served from validated text)
    -> disclaimer.

Safety-critical logic (crisis, referral) is deterministic and independent of the model.
A module-level singleton exposes a backward-compatible functional API (`answer`, `retrieve`,
`detect_language`, ...) used by the app, the tests, and the evaluation scripts.
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


class UmubyeyiRAG:
    """Fully-local retrieval-augmented generation pipeline for postpartum emotional wellbeing."""

    # ---- response policy (class-level constants) ----
    SIM_GATE = 0.25          # below this: ask to say more, rather than ground on a weak/off-topic match
    TOP_K = 3
    GEN_NOTES = 2            # notes fed to the generator at inference == what it was trained on
    CRISIS_LINE = "114"

    HEADER = ("You are Umubyeyi, a warm companion for the emotional wellbeing of first-time mothers "
              "in Rwanda in the first 6 months after birth. Using the validated notes, reply with "
              "warmth and empathy in English.\n")

    DISCLAIMER = {
        "rw": "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge.",
        "en": "This is general information, not medical advice. Please talk to a health worker if you are worried.",
    }

    DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby", "harm my baby",
              "kwiyahura", "kwiyica", "guhotora", "kwica umwana"]
    # acute medical / baby-care that we refer out rather than answer
    CLINICAL = ["bleeding", "haemorrhage", "hemorrhage", "fever", "stitches", "wound", "infection",
                "seizure", "convulsion", "not breathing", "unconscious", "amaraso", "umuriro"]

    GREET_WORDS = {"muraho", "mwaramutse", "mwiriwe", "mwiriweho", "murakaza", "bite", "amakuru",
                   "hi", "hello", "hey", "hallo", "hola", "yego"}
    GREET_PHRASES = ("good morning", "good afternoon", "good evening", "how are you", "muraho",
                     "mwaramutse", "mwiriwe", "amakuru", "murakaza neza", "uraho")
    # trailing small-talk fillers so "hi friend", "how are you today", "good morning dear" count as greetings
    GREET_FILLER = {"mama", "neza", "there", "everyone", "all", "friend", "today", "dear", "sis", "sister",
                    "my", "doing", "again", "so", "now", "how", "are", "you", "u", "ur"}

    # a few warm variants so greetings/small-talk/clarify don't repeat the exact same sentence
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
    CLARIFY = {
        "rw": ["Numva ibyo uvuga. Wambwira gato byinshi ku byo wiyumva, kugira ngo ngufashe neza?",
               "Ndi hano kukumva. Ni iki cyane cyane kigukoraho muri iki gihe?",
               "Mbwira uko wiyumva mu magambo yawe - agahinda, guhangayika, umunaniro? Ndashaka kugusobanukirwa."],
        "en": ["I hear you. Could you tell me a little more about how you're feeling, so I can help you better?",
               "I'm here for you. What's weighing on you most right now?",
               "Tell me in your own words how you're feeling - sad, anxious, overwhelmed, tired? I want to understand."],
    }

    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        # postpartum grounding bank (validated MOTHER + maternalcare + curated); fall back to legacy bank
        bank_path = self.root / "data" / "grounding_bank_postpartum.json"
        if not bank_path.exists():
            bank_path = self.root / "data" / "grounding_bank.json"
        self.bank = json.loads(bank_path.read_text(encoding="utf-8"))
        self.langdet = joblib.load(self.root / "models" / "lang_detector.joblib")
        self.gen_dir = self.root / "models" / "umubyeyi-generator"   # our fine-tuned flan-t5 generator
        self.clf_path = self.root / "models" / "intent_clf.joblib"   # our LogReg intent router

        # retrieval index over both language phrasings so en and rw queries both match
        search = [f'{b.get("question_en", "")} {b.get("question_rw", "")}' for b in self.bank]
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
        self._mat = self._vec.fit_transform(search)

        # lazily-loaded heavy models
        self._tok = self._model = None
        self._gen_tried = False
        self._router = None
        self._router_tried = False

    # ---------------------------------------------------------------- language
    def detect_language(self, text: str) -> str:
        try:
            return self.langdet.predict([text])[0]
        except Exception:
            return "en"

    # ------------------------------------------------------------- safety / scope
    def is_danger(self, text: str) -> bool:
        t = text.lower()
        return any(k in t for k in self.DANGER)

    def is_clinical(self, text: str) -> bool:
        t = text.lower()
        return any(k in t for k in self.CLINICAL)

    def is_greeting(self, text: str) -> bool:
        t = re.sub(r"[^\w\s]", " ", text.lower()).strip()
        if not t:
            return False
        had_greet = any(p in t for p in self.GREET_PHRASES) or any(w in self.GREET_WORDS for w in t.split())
        if not had_greet:
            return False
        for p in self.GREET_PHRASES:
            t = t.replace(p, " ")
        remaining = [w for w in t.split() if w not in (self.GREET_WORDS | self.GREET_FILLER)]
        return len(remaining) == 0

    def _greeting_reply(self, lang: str) -> str:
        return random.choice(self.GREETINGS.get(lang, self.GREETINGS["en"]))

    def _crisis_message(self, lang: str) -> str:
        if lang == "rw":
            return ("Ndumva ko ubu uri kunyura mu bihe bikomeye. Ntabwo uri wenyine. Nyamuneka vugana "
                    f"n'umuntu wizeye cyangwa umukozi w'ubuzima nonaha, cyangwa uhamagare: {self.CRISIS_LINE}.")
        return ("It sounds like you are going through something very hard. You are not alone. Please reach "
                f"out to someone you trust or a health worker now, or call: {self.CRISIS_LINE}.")

    def _clinical_message(self, lang: str) -> str:
        if lang == "rw":
            return ("Umubyeyi afasha ku byerekeye uko wiyumva. Ku bibazo by'umubiri cyangwa umwana "
                    "(kuva amaraso, umuriro, ibikomere), nyamuneka ganira n'umuforomo cyangwa umukozi "
                    "w'ubuzima vuba. Ese wowe ubwawe wiyumva ute muri iki gihe?")
        return ("Umubyeyi helps with how you are feeling. For physical or baby concerns (bleeding, fever, "
                "wounds), please see a nurse or health worker soon. How are you coping in yourself right now?")

    # ----------------------------------------------- our own ML: router + retrieval + generator
    def route_intent(self, text: str):
        """Our LogReg router tags the wellness topic (for the pipeline + analytics)."""
        if not self._router_tried:
            self._router_tried = True
            try:
                self._router = joblib.load(self.clf_path)
            except Exception:
                self._router = None
        if self._router is None:
            return None
        try:
            return str(self._router.predict([text])[0])
        except Exception:
            return None

    def retrieve(self, text: str, k: int = None):
        sims = cosine_similarity(self._vec.transform([text]), self._mat)[0]
        idx = sims.argsort()[::-1][:(k or self.TOP_K)]
        return [(self.bank[i], float(sims[i])) for i in idx]

    def _load_generator(self):
        """Load our fine-tuned flan-t5 once. Returns (tok, model) or (None, None) if unavailable."""
        if self._gen_tried:
            return self._tok, self._model
        self._gen_tried = True
        try:
            if not self.gen_dir.exists():
                print("[umubyeyi] generator not found -> retrieval-only mode", file=sys.stderr)
                return None, None
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(str(self.gen_dir))
            self._model = AutoModelForSeq2SeqLM.from_pretrained(str(self.gen_dir))
            print("[umubyeyi] loaded local generator ->", self.gen_dir, file=sys.stderr)
        except Exception as e:
            print(f"[umubyeyi] generator load failed ({type(e).__name__}) -> retrieval-only", file=sys.stderr)
            self._tok = self._model = None
        return self._tok, self._model

    def _generate_en(self, query: str, snippets) -> str:
        """Generate an English answer with our fine-tuned model, grounded on the notes.
        Returns a good draft, or "" if the model is unavailable / the draft looks poor."""
        tok, model = self._load_generator()
        if model is None:
            return ""
        notes = "\n".join(f"- {b['answer_en']}" for b, _ in snippets[:self.GEN_NOTES] if b.get("answer_en"))
        prompt = f"{self.HEADER}Notes:\n{notes}\nMother: {query}\nAnswer:"
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

    # ------------------------------------------------------------------- orchestration
    def answer(self, query: str, force_lang: str = None, history=None) -> dict:
        """Return {answer, language, danger, grounded, mode, intent, sources}. Fully local, no API."""
        lang = force_lang if force_lang in ("en", "rw") else self.detect_language(query)

        if self.is_danger(query):
            return {"answer": self._crisis_message(lang), "language": lang, "danger": True,
                    "grounded": False, "mode": "safety", "intent": "crisis", "sources": []}

        if self.is_greeting(query):
            return {"answer": self._greeting_reply(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "greeting", "intent": "greeting", "sources": []}

        if self.is_clinical(query):
            return {"answer": self._clinical_message(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "referral", "intent": "clinical", "sources": []}

        intent = self.route_intent(query)                 # our LogReg router tags the wellness topic
        snippets = self.retrieve(query)
        top, sim = snippets[0] if snippets else (None, 0.0)
        grounded = top is not None and sim >= self.SIM_GATE

        if not grounded:
            # no confident validated match: stay honest, invite her to say more (never fabricate)
            return {"answer": random.choice(self.CLARIFY.get(lang, self.CLARIFY["en"])), "language": lang,
                    "danger": False, "grounded": False, "mode": "clarify", "intent": intent, "sources": []}

        if lang == "rw":
            # serve the VALIDATED Kinyarwanda answer when we have it (higher quality than MT)
            body = (top.get("answer_rw") or "").strip() or (top.get("answer_en") or "").strip()
            mode = "retrieved_rw" if top.get("answer_rw") else "retrieved_en"
        else:
            # generation-primary: OUR fine-tuned flan-t5 generates the English answer, grounded on the notes
            draft = self._generate_en(query, snippets)
            if draft:
                body, mode = draft, "generative"
            else:
                body, mode = (top.get("answer_en") or "").strip(), "retrieved"   # validated fallback if generation fails

        text = f"{body}\n\n{self.DISCLAIMER.get(lang, self.DISCLAIMER['en'])}"
        return {"answer": text, "language": lang, "danger": False, "grounded": grounded, "mode": mode,
                "intent": intent,
                "sources": [{"topic": b.get("topic", ""), "source": b.get("source", ""), "sim": round(s, 2)}
                            for b, s in snippets]}


# ------- module-level singleton + backward-compatible functional API (app.py, tests, eval) -------
_default = UmubyeyiRAG()

answer = _default.answer
retrieve = _default.retrieve
detect_language = _default.detect_language
is_danger = _default.is_danger
is_clinical = _default.is_clinical
is_greeting = _default.is_greeting
route_intent = _default.route_intent

# constants some callers reference
HEADER = UmubyeyiRAG.HEADER
SIM_GATE = UmubyeyiRAG.SIM_GATE
CRISIS_LINE = UmubyeyiRAG.CRISIS_LINE
DISCLAIMER = UmubyeyiRAG.DISCLAIMER
GEN_DIR = _default.gen_dir
BANK = _default.bank
