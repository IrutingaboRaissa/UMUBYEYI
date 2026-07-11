"""
Umubyeyi — local, retrieval-first postpartum wellbeing core.

Scope: the EMOTIONAL WELLBEING of first-time mothers in Rwanda in the first 6 months
postpartum. Acute clinical questions are referred to a health worker.

`UmubyeyiRAG` encapsulates the source-attributed knowledge bank, language detector,
retriever, and response policy behind a single `answer()` method:

    language -> safety -> greeting -> clinical referral -> retrieval -> disclaimer.

Safety-critical logic (crisis, referral) is deterministic and independent of the model.
A module-level singleton exposes a backward-compatible functional API (`answer`, `retrieve`,
`detect_language`, ...) used by the app, the tests, and the evaluation scripts.
"""
import json
import os
import random
import re
import urllib.error
import urllib.request
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]


class UmubyeyiRAG:
    """Fully-local retrieval-augmented generation pipeline for postpartum emotional wellbeing."""

    # ---- response policy (class-level constants) ----
    SIM_GATE = 0.12          # below this: redirect (not in wellbeing scope). Low enough that conversational/
                             # filler-laden emotional messages still answer, high enough that off-topic deflects.
    RW_SIM_GATE = 0.20       # focused source-document bank: abstain below a meaningful text match
    WELLBEING_INTENTS = {"self_care_coping", "sleep", "overwhelmed_identity",
                         "sadness_low_mood", "anxiety_worry", "relationship_support"}
    TOP_K = 3
    CRISIS_LINE = "114"
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

    DISCLAIMER = {
        "rw": "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge.",
        "en": "This is general information, not medical advice. Please talk to a health worker if you are worried.",
    }

    DANGER = ["kill myself", "end my life", "suicide", "hurt myself", "hurt my baby", "harm my baby",
              "kwiyahura", "kwiyica", "guhotora", "kwica umwana"]
    # acute medical / baby-care that we refer out rather than answer
    CLINICAL = ["bleeding", "haemorrhage", "hemorrhage", "fever", "stitches", "wound", "infection",
                "seizure", "convulsion", "not breathing", "unconscious", "amaraso", "umuriro"]
    # baby / child care (not the mother's emotional wellbeing) -> redirect
    BABY_CARE = ["my baby", "the baby", "baby's", "infant", "newborn", "toddler", "diaper", "breastfeed",
                 "breast milk", "bottle feed", "colic", "vaccin", "immuniz", "weaning", "teething",
                 "umwana wanjye", "umwana wawe", "umwana", "umwanya", "uruhinja", "gususura", "indembe",
                 "amata y'umwana", "gutwara inda"]
    # signals the mother is talking about her own feelings or emotional wellbeing
    FEELING = ["i feel", "i'm feeling", "im feeling", "feeling", "felt", "sad", "anxious", "worry",
               "worried", "overwhelm", "lonely", "depressed", "worthless", "scared", "stressed",
               "cope", "coping", "umutima", "wiyumva", "agahinda", "impungenge", "guhangayika",
               "umunaniro", "ndumva", "mfite agahinda", "nshobora", "nabuze", "gusinda",
               "sleep", "insomnia", "tired", "exhaust", "can't sleep", "cant sleep", "crying",
               "cry", "alone", "hopeless", "panic", "miserable", "numb", "sinzi", "gusinzira"]
    # clearly non-wellbeing topics -> politely redirect (matched as whole words, so "car" != "care")
    OFFTOPIC = {"weather", "rain", "forecast", "temperature", "football", "soccer", "basketball",
                "sport", "sports", "match", "tournament", "politics", "election", "president", "vote",
                "government", "news", "movie", "film", "cinema", "song", "recipe", "cook", "cooking",
                "homework", "exam", "math", "mathematics", "programming", "python", "code", "laptop",
                "computer", "phone", "car", "vehicle", "flight", "airport", "hotel", "restaurant",
                "bitcoin", "stock", "salary", "tax", "dog", "cat", "football"}

    GREET_WORDS = {"muraho", "mwaramutse", "mwiriwe", "mwiriweho", "murakaza", "bite", "amakuru",
                   "hi", "hello", "hey", "hallo", "hola", "yego"}
    GREET_PHRASES = ("good morning", "good afternoon", "good evening", "how are you", "muraho",
                     "mwaramutse", "mwiriwe", "amakuru", "murakaza neza", "uraho")
    # trailing small-talk fillers so "hi friend", "how are you today", "good morning dear" count as greetings
    GREET_FILLER = {"mama", "neza", "there", "everyone", "all", "friend", "today", "dear", "sis", "sister",
                    "my", "doing", "again", "so", "now", "how", "are", "you", "u", "ur"}

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
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        # Source-attributed postpartum wellbeing documents used by retrieval.
        bank_path = self.root / "data" / "knowledge" / "postpartum_wellbeing.json"
        if not bank_path.exists():
            raise FileNotFoundError(f"Runtime grounding bank not found: {bank_path}")
        self.bank = json.loads(bank_path.read_text(encoding="utf-8"))
        self.langdet = joblib.load(self.root / "models" / "lang_detector.joblib")

        # Keep language indexes separate. Each index contains every complete same-language pair
        # in the scoped postpartum bank. Do not silently filter Kinyarwanda rows using English
        # keywords: that previously reduced 102 complete pairs to only six at runtime.
        self._indices = {}
        self._vecs = {}
        self._mats = {}
        for lang in ("en", "rw"):
            qkey, akey = f"queries_{lang}", f"text_{lang}"
            indices = [i for i, row in enumerate(self.bank)
                       if (row.get(qkey) or "").strip() and (row.get(akey) or "").strip()]
            search = [f"{self.bank[i].get(qkey, '')} {self.bank[i].get(akey, '')}".strip()
                      for i in indices]
            vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
            self._indices[lang] = indices
            self._vecs[lang] = vec
            self._mats[lang] = vec.fit_transform(search)
        self._ollama_checked = False
        self._ollama_ready = False

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

    def is_offtopic(self, text: str) -> bool:
        words = set(re.findall(r"[a-z]+", text.lower()))
        return bool(words & self.OFFTOPIC)

    def has_feeling_language(self, text: str) -> bool:
        t = text.lower()
        return any(k in t for k in self.FEELING)

    def is_baby_care(self, text: str) -> bool:
        """True when the query is about baby/child care, not the mother's emotional wellbeing."""
        t = text.lower()
        if not any(k in t for k in self.BABY_CARE):
            return False
        return not self.has_feeling_language(text)

    def is_wellbeing_scope(self, text: str, intent: str, sim: float) -> bool:
        """True only when the query is clearly about the mother's emotional wellbeing."""
        if self.is_baby_care(text):
            return False
        if sim < self.SIM_GATE:
            return False
        if self.has_feeling_language(text):
            return True
        # Indirect wording (for example, "I never sleep") requires a stronger
        # source-document match even when it does not contain an explicit feeling phrase.
        return sim >= 0.18

    def _redirect(self, lang: str) -> str:
        return self._offtopic_message(lang)

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

    def _offtopic_message(self, lang: str) -> str:
        if lang == "rw":
            return ("Umubyeyi ari hano ku byerekeye uko wiyumva nk'umubyeyi mushya mu mezi ya mbere - "
                    "sinshobora gufasha ku bindi bibazo. Ariko ndumva: hari ikiguhangayikishije mu mutima?")
        return ("Umubyeyi is here for how you're feeling as a new mother in these early months - I can't "
                "help with other topics. But I'm listening: is something weighing on your heart?")

    # ------------------------------------------------ topic routing + retrieval
    def route_intent(self, text: str):
        """Return the topic of the closest source document for analytics."""
        lang = self.detect_language(text)
        matches = self.retrieve(text, k=1, lang=lang)
        return matches[0][0].get("topic") if matches else None

    def retrieve(self, text: str, k: int = None, lang: str = "en"):
        """Return same-language grounded matches; never cross language for a final answer."""
        lang = lang if lang in self._indices else "en"
        sims = cosine_similarity(self._vecs[lang].transform([text]), self._mats[lang])[0]
        local_idx = sims.argsort()[::-1][:(k or self.TOP_K)]
        return [(self.bank[self._indices[lang][i]], float(sims[i])) for i in local_idx]

    def _generate_grounded(self, query: str, evidence: str, lang: str, history=None) -> str:
        """Ask local Ollama to phrase a fresh answer; return empty text on any failure."""
        if os.environ.get("VERCEL") == "1" or os.environ.get("UMU_DISABLE_OLLAMA") == "1":
            return ""
        if not self._ollama_checked:
            self._ollama_checked = True
            try:
                tags_url = self.OLLAMA_URL.rsplit("/api/", 1)[0] + "/api/tags"
                with urllib.request.urlopen(tags_url, timeout=2) as response:
                    installed = json.loads(response.read().decode("utf-8")).get("models", [])
                names = {item.get("name") for item in installed} | {item.get("model") for item in installed}
                # Ollama reports custom models as ``name:latest`` even when the
                # request model is simply ``name``.
                requested = self.OLLAMA_MODEL
                self._ollama_ready = requested in names or f"{requested}:latest" in names
            except (OSError, TimeoutError, ValueError, urllib.error.URLError):
                self._ollama_ready = False
        if not self._ollama_ready:
            return ""
        language = "Kinyarwanda" if lang == "rw" else "English"
        messages = [{
            "role": "system",
            "content": (
                "You are Umubyeyi, a warm emotional-wellbeing assistant for first-time mothers "
                "during the first six months after childbirth. Use only the supplied evidence. "
                "Do not diagnose, prescribe, or invent facts. Reply concisely in the requested "
                "language. Acknowledge feelings and give practical evidence-supported next steps. "
                "The application adds its own disclaimer."
            ),
        }]
        for item in (history or [])[-4:]:
            role = "assistant" if item.get("role") == "bot" else "user"
            content = (item.get("text") or "").strip()
            if content:
                messages.append({"role": role, "content": content[:1000]})
        messages.append({
            "role": "user",
            "content": f"Language: {language}\nEvidence:\n{evidence}\n\nMother's message: {query}",
        })
        payload = json.dumps({
            "model": self.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 180, "num_ctx": 4096},
        }).encode("utf-8")
        request = urllib.request.Request(
            self.OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            draft = ((result.get("message") or {}).get("content") or "").strip()
            return draft if len(draft.split()) >= 6 else ""
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            return ""

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

        if self.is_offtopic(query):
            return {"answer": self._offtopic_message(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "offtopic", "intent": "offtopic", "sources": []}

        if self.is_baby_care(query):
            return {"answer": self._clinical_message(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "referral", "intent": "clinical", "sources": []}

        snippets = self.retrieve(query, lang=lang)
        top, sim = snippets[0] if snippets else (None, 0.0)
        intent = top.get("topic") if top else None

        if lang == "rw" and sim < self.RW_SIM_GATE:
            return {"answer": self._redirect(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}

        if not self.is_wellbeing_scope(query, intent, sim):
            return {"answer": self._redirect(lang), "language": lang, "danger": False,
                    "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}

        if lang == "rw":
            body = (top.get("text_rw") or "").strip()
            if body:
                draft = self._generate_grounded(query, body, lang, history)
                body, mode = (draft, "ollama_grounded") if draft else (body, "retrieved_rw")
            else:
                return {"answer": self._redirect(lang), "language": lang, "danger": False,
                        "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}
        else:
            body = (top.get("text_en") or "").strip()
            if not body:
                return {"answer": self._redirect(lang), "language": lang, "danger": False,
                        "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}
            draft = self._generate_grounded(query, body, lang, history)
            body, mode = (draft, "ollama_grounded") if draft else (body, "retrieved")

        text = f"{body}\n\n{self.DISCLAIMER.get(lang, self.DISCLAIMER['en'])}"
        return {"answer": text, "language": lang, "danger": False, "grounded": True, "mode": mode,
                "intent": intent,
                "sources": [{"topic": b.get("topic", ""), "source": b.get("source", ""),
                             "url": b.get("url", ""), "sim": round(s, 2)}
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
SIM_GATE = UmubyeyiRAG.SIM_GATE
CRISIS_LINE = UmubyeyiRAG.CRISIS_LINE
DISCLAIMER = UmubyeyiRAG.DISCLAIMER
BANK = _default.bank
