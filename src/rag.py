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
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from finetuned_generator import FineTunedGenerator
from gemini_generator import GeminiGenerator
from topic_classifier import TopicClassifier

ROOT = Path(__file__).resolve().parents[1]


class UmubyeyiRAG:
    """Fully-local retrieval-augmented generation pipeline for postpartum emotional wellbeing."""

    # ---- response policy (class-level constants) ----
    SIM_GATE = 0.12          # below this: redirect (not in wellbeing scope). Low enough that conversational/
                             # filler-laden emotional messages still answer, high enough that off-topic deflects.
    RW_SIM_GATE = 0.20       # focused source-document bank: abstain below a meaningful text match
    WELLBEING_INTENTS = {"self_care_coping", "sleep", "overwhelmed_identity",
                         "sadness_low_mood", "anxiety_worry", "relationship_support"}
    INTENT_TOPIC_IDS = {
        "self_care_coping": ("emotional_changes", "daily_functioning", "professional_help"),
        "sleep": ("sleep_fatigue",),
        "overwhelmed_identity": ("overwhelmed", "bonding", "irritability_anger"),
        "sadness_low_mood": ("persistent_sadness", "self_blame_guilt", "loss_grief"),
        "anxiety_worry": ("anxiety_worry", "professional_help"),
        "relationship_support": ("social_support", "partner_relationship"),
    }
    TOP_K = 3
    CRISIS_LINE = "114"
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

    DISCLAIMER = {
        "rw": "Aya ni amakuru rusange, si inama z'ubuvuzi. Vugana n'umuganga niba ufite impungenge.",
        "en": "This is general information, not medical advice. Please talk to a health worker if you are worried.",
    }

    DANGER = [
        "kill myself", "end my life", "take my life", "suicide", "suicidal",
        "hurt myself", "harm myself", "want to die", "wish i were dead", "plan to die",
        "dont want to live", "do not want to live", "not want to be alive",
        "better off without me", "cannot keep myself safe", "cant keep myself safe",
        "hurt my baby", "harm my baby", "kill my baby",
        "kwiyahura", "kwiyica", "ndashaka gupfa", "nifuza gupfa", "sinshaka kubaho",
        "kwikomeretsa", "gukomeretsa umwana", "kwica umwana", "guhotora",
    ]
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

    # An honest availability notice, used only when conversational generation fails.
    GREETING_FAILURE = {
        "rw": "Ubu sinshoboye gutangiza ikiganiro. Ongera ugerageze mu kanya.",
        "en": "I couldn't start the conversation just now. Please try again in a moment.",
    }
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        # Source-attributed postpartum wellbeing documents used by retrieval.
        bank_path = self.root / "data" / "knowledge" / "postpartum_wellbeing.json"
        if not bank_path.exists():
            raise FileNotFoundError(f"Runtime grounding bank not found: {bank_path}")
        self.bank = json.loads(bank_path.read_text(encoding="utf-8"))
        self.langdet = joblib.load(self.root / "models" / "lang_detector.joblib")
        self.finetuned_generator = FineTunedGenerator(
            self.root / "models" / "umubyeyi-mt5-lora"
        )
        self.gemini_generator = GeminiGenerator()
        self.topic_classifier = TopicClassifier(self.root / "models" / "topic_classifier.joblib")
        self._bank_by_id = {row["id"]: row for row in self.bank}

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
        self._gemini_context = {
            lang: " ".join(
                (row.get(f"text_{lang}") or "").strip()
                for row in self.bank if (row.get(f"text_{lang}") or "").strip()
            )
            for lang in ("en", "rw")
        }
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
        t = unicodedata.normalize("NFKC", text).lower().replace("'", "").replace("’", "")
        t = t.translate(str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}))
        t = re.sub(r"[^a-z\s]", " ", t)
        t = re.sub(r"\bk\s+i\s+l\s+l\b", "kill", t)
        t = " ".join(t.split())
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
        # Explicit first-person feeling language is itself in scope; the trained topic
        # classifier then decides which evidence categories apply. Do not reject a short
        # disclosure merely because lexical similarity is just below the retrieval gate.
        if self.has_feeling_language(text):
            return True
        if sim < self.SIM_GATE:
            return False
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

    def classify_topics(self, text: str, k: int = 3) -> list[dict]:
        """Return ranked coarse intents from the supervised AMOD-derived classifier."""
        return self.topic_classifier.predict(text, k=k)

    def _classified_evidence(self, text: str, lang: str) -> tuple[str, list[dict]]:
        """Map coarse intent predictions to reviewed postpartum evidence topics."""
        predictions = self.classify_topics(text, k=3)
        passages = []
        usable_predictions = []
        for prediction in predictions:
            intent = prediction.get("intent", "")
            mapped_topics = []
            for topic_id in self.INTENT_TOPIC_IDS.get(intent, ()):
                row = self._bank_by_id.get(topic_id)
                body = (row or {}).get(f"text_{lang}", "").strip()
                if not row or not body:
                    continue
                passages.append(f"Topic {row['id']} ({row['topic']}): {body}")
                mapped_topics.append({"topic_id": row["id"], "topic": row["topic"]})
            if mapped_topics:
                usable_predictions.append({
                    "intent": intent,
                    "score": round(prediction["score"], 4),
                    "mapped_topics": mapped_topics,
                })
        return "\n".join(passages), usable_predictions

    def _generate_ollama(self, query: str, evidence: str, lang: str, history=None) -> str:
        """Ask local Ollama to phrase a fresh answer; return empty text on any failure."""
        if (os.environ.get("VERCEL") == "1" or
                os.environ.get("UMU_DISABLE_OLLAMA") == "1" or
                os.environ.get("UMU_ENABLE_OLLAMA") != "1"):
            return ""
        if not self._ollama_checked:
            self._ollama_checked = True
            try:
                tags_url = self.OLLAMA_URL.rsplit("/api/", 1)[0] + "/api/tags"
                with urllib.request.urlopen(tags_url, timeout=1.5) as response:
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
            timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "8"))
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            draft = ((result.get("message") or {}).get("content") or "").strip()
            return draft if len(draft.split()) >= 6 else ""
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            return ""

    def _generate_grounded(self, query: str, evidence: str, lang: str, history=None,
                           gemini_evidence: str | None = None) -> tuple[str, str]:
        """Use grounded Gemini, project-fine-tuned fallback, optional Ollama, then retrieval."""
        # Gemini receives only this message and classifier-selected reviewed evidence. Conversation
        # history is intentionally kept local because it can contain sensitive details.
        try:
            draft = self.gemini_generator.generate(query, gemini_evidence or evidence, lang)
        except Exception:
            draft = ""
        if not draft and self.gemini_generator.available and self.gemini_generator.last_error:
            # Sanitized operational evidence only: never log the key, message, or passage.
            print(f"Gemini fallback: {self.gemini_generator.last_error}", file=sys.stderr, flush=True)
        if draft:
            return draft, "gemini_grounded"
        try:
            draft = self.finetuned_generator.generate(query, evidence, lang)
        except Exception:
            # Optional model/dependency failures must never become an HTTP 500.
            draft = ""
        if draft:
            return draft, "finetuned_grounded"
        # The configured Ollama model did not pass Kinyarwanda quality review.
        # Fail directly to the retrieved RW passage unless a developer explicitly
        # opts into experimental local RW generation.
        if lang == "rw" and os.environ.get("UMU_ALLOW_RW_OLLAMA") != "1":
            return "", ""
        try:
            draft = self._generate_ollama(query, evidence, lang, history)
        except Exception:
            draft = ""
        if draft:
            return draft, "ollama_grounded"
        return "", ""

    # ------------------------------------------------------------------- orchestration
    def answer(self, query: str, force_lang: str = None, history=None) -> dict:
        """Return the routed, source-attributed response contract."""
        lang = force_lang if force_lang in ("en", "rw") else self.detect_language(query)

        if self.is_danger(query):
            return {"answer": self._crisis_message(lang), "language": lang, "danger": True,
                    "grounded": False, "mode": "safety", "intent": "crisis", "sources": []}

        if self.is_greeting(query):
            try:
                social = self.gemini_generator.generate_social(query, lang)
            except Exception:
                social = ""
            if not social and self.gemini_generator.available and self.gemini_generator.last_error:
                print(
                    f"Gemini conversation fallback: {self.gemini_generator.last_error}",
                    file=sys.stderr,
                    flush=True,
                )
            mode = "gemini_conversation" if social else "greeting_fallback"
            return {"answer": social or self.GREETING_FAILURE.get(lang, self.GREETING_FAILURE["en"]),
                    "language": lang, "danger": False, "grounded": False,
                    "mode": mode, "intent": "greeting", "sources": []}

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

        classified_evidence, topic_predictions = self._classified_evidence(query, lang)

        if lang == "rw":
            body = (top.get("text_rw") or "").strip()
            if body:
                draft, generated_mode = self._generate_grounded(
                    query, body, lang, history,
                    gemini_evidence=classified_evidence or self._gemini_context[lang]
                )
                body, mode = (draft, generated_mode) if draft else (body, "retrieved_rw")
            else:
                return {"answer": self._redirect(lang), "language": lang, "danger": False,
                        "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}
        else:
            body = (top.get("text_en") or "").strip()
            if not body:
                return {"answer": self._redirect(lang), "language": lang, "danger": False,
                        "grounded": False, "mode": "offtopic", "intent": intent, "sources": []}
            draft, generated_mode = self._generate_grounded(
                query, body, lang, history,
                gemini_evidence=classified_evidence or self._gemini_context[lang]
            )
            body, mode = (draft, generated_mode) if draft else (body, "retrieved")

        text = f"{body}\n\n{self.DISCLAIMER.get(lang, self.DISCLAIMER['en'])}"
        return {"answer": text, "language": lang, "danger": False, "grounded": True, "mode": mode,
                "intent": intent, "topic_predictions": topic_predictions,
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
