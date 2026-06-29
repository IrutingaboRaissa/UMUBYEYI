<!-- Hugging Face Space config (read by HF when this repo is deployed as a Space; GitHub ignores it). -->
---
title: Umubyeyi
emoji: U
colorFrom: green
colorTo: gray
sdk: streamlit
sdk_version: 1.48.1
app_file: src/app.py
pinned: false
short_description: Bilingual grounded-generation chatbot for postpartum support of Rwandan mothers
---

# Umubyeyi

**A bilingual (Kinyarwanda / English) chatbot that supports first-time mothers in Rwanda during the 0–6 month postpartum window — answering their questions with safe, validated, language-matched information.**

Author: **Raissa IRUTINGABO** · Supervisor: **Samiratu Ntohsi** · BSc Software Engineering, African Leadership University

---

## Why this project

In Rwanda, antenatal care is comparatively well-attended and most deliveries are supervised, but **postnatal contact drops sharply after birth** — the WHO calls the postnatal period the most neglected phase of maternal care. Yet the **0–6 months after birth** is exactly when postpartum depression, breastfeeding difficulties, recovery complications, and newborn-care anxiety peak. First-time mothers are the most exposed, and they often lack timely, trustworthy information **in Kinyarwanda**. Umubyeyi is a small, safe, deployable assistant for that gap.

---

## What it does

You type a question in **Kinyarwanda or English**, and Umubyeyi replies **in the same language** with a warm, on-topic answer grounded in a medically-validated maternal knowledge base — wrapped in safety mechanisms.

- **Bilingual and auto-detected** — no language switch; each message is detected and answered in its own language.
- **Grounded answers** — clinical answers are drawn from validated content, not invented.
- **Emotional support** — for feelings (sadness, anxiety, overwhelm) it responds with empathy and gentle, non-diagnostic guidance.
- **Safety first** — a danger-sign override surfaces a crisis referral; every answer carries a disclaimer; off-topic questions (malaria, COVID, farming) are politely declined.
- **Scoped** — strictly 0–6 months postpartum, informational only (never diagnostic).

---

## System architecture

Umubyeyi is built as a **layered, retrieval-augmented-generation (RAG)** system. Each layer has a single responsibility and a defined interface to the next, and the **safety-critical logic is deterministic and kept independent of the language model** — so a model outage, a bad key, or a hallucination can never bypass the crisis path or the disclaimer.

![Umubyeyi layered system architecture](assets/system_architecture_layered.png)

*Layered system architecture — tiers, components, technologies, and inter-layer data flow.*

### Layers, responsibilities, and technologies

| Layer | Responsibility | Key modules / functions | Technology | Input → Output |
|---|---|---|---|---|
| **Presentation** | Render the chat, gate consent, collect input, hold per-session history | `src/app.py` (Streamlit) | Streamlit 1.48, HTML/CSS (responsive) | user text → `rag.answer()` call |
| **Application / Orchestration** | Drive the pipeline; decide the response *mode* | `rag.answer()` | Python 3 | query + history → response dict |
| **Safety (cross-cutting)** | Deterministic danger detection, disclaimer, domain bounding | `is_danger()`, `_crisis_message()`, `DISCLAIMER`, prompt guardrails | keyword match + rules | query → crisis short-circuit / appended disclaimer |
| **Language** | Detect EN vs RW to choose the reply language | `detect_language()`, `models/lang_detector.joblib` | char n-gram TF-IDF + Logistic Regression (99.95% acc.) | text → `"en"`/`"rw"` |
| **Knowledge / Retrieval** | Find the closest validated fact(s) | `retrieve()`, `data/grounding_bank.json` | TF-IDF `char_wb` (3–5) + cosine similarity | query → top-k snippets + scores |
| **Generation (external)** | Write the answer *in the user's language* from the validated fact | `_gemini()`, `_build_prompt()` | Google Gemini (`gemini-2.5-flash`) via `google-genai` | prompt → answer text |

### Request lifecycle (technical)

`rag.answer(query, force_lang=None, history=None)` executes a deterministic pipeline:

1. **Language resolution** — `force_lang` if the user pinned RW/EN, else `detect_language()` (char-n-gram LogReg classifier) returns `"en"`/`"rw"`.
2. **Safety short-circuit** — `is_danger()` matches a curated EN+RW self-harm lexicon. On a hit, the pipeline returns `_crisis_message()` (referral to **114**, Rwanda's health line) **before any model or retrieval call**. This path is unconditionally reachable and cannot be overridden by the LLM.
3. **Retrieval** — the query is vectorised with the fitted `TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)` and scored by cosine similarity against the precomputed matrix of all 158 bank entries (each indexed on *both* its English and Kinyarwanda phrasing, so either language matches). The top-3 are returned with scores.
4. **Grounding gate** — if the top score ≥ `SIM_GATE` (0.18) the answer is marked `grounded` and the validated facts are injected into the prompt; otherwise the model is told there is no specific match and instructed to be cautious and defer to a health worker.
5. **Key check** — `_has_key()` verifies a real `GEMINI_API_KEY`. If absent, the pipeline returns a graceful "unavailable" message (and logs the cause) — it never serves raw machine-translated drafts.
6. **Constrained generation** — `_build_prompt()` assembles a system instruction (role, domain bounds, Rwanda context, no-diagnosis rule, no self-added disclaimer), the **validated facts**, the **recent conversation turns** (for multi-turn coherence), and the new question. `_gemini()` calls the model with **retry + multi-model fallback** (see Resilience).
7. **Post-processing** — any disclaimer the model added is stripped, then the **canonical disclaimer** for the detected language is appended exactly once.
8. **Response contract** — the function returns a typed dict consumed by the UI:

```python
{
  "answer":   str,            # text shown to the mother (+ disclaimer)
  "language": "en" | "rw",
  "danger":   bool,           # True only on the crisis path
  "grounded": bool,           # True if a validated fact met the gate
  "mode":     "safety" | "generative" | "unavailable",
  "sources":  [{"topic": str, "source": str, "sim": float}, ...]
}
```

### Data contract — the validated answer bank

`data/grounding_bank.json` is an array of 158 records, each:

```json
{
  "question_en": "...", "answer_en": "...",
  "question_rw": "...", "answer_rw": "...",
  "topic": "...", "source": "MOTHER"
}
```

Generation grounds on `answer_en` (the clean, validated English text) and produces fluent Kinyarwanda at request time — avoiding the corruption seen in pre-translated answers.

### Cross-cutting concerns

- **Resilience** — `_gemini()` iterates a fallback chain (`gemini-2.5-flash` → `flash-lite` → `flash-latest` → `2.0-flash`) across 3 retry rounds with backoff, so transient `503`/`429` errors degrade to "try again" rather than a crash. Failures are logged to stderr for diagnosis.
- **Configuration / secrets** — the key is read from `.env` locally and from `st.secrets` in deployment, bridged into `os.environ` at startup; it is never committed.
- **State** — the app is stateless server-side; conversation history lives in Streamlit `session_state` and is passed into each call, so horizontal restarts lose nothing critical.
- **No PII** — the consent screen asks users not to enter identifying information; nothing personal is stored.

### Deployment topology

Single Streamlit process on **Streamlit Community Cloud**, serving `src/app.py` from this repository. The only external dependency at runtime is the Gemini API (HTTPS). The retrieval index and language model are small in-memory artifacts built at startup, so the app fits the free tier (no GPU, no translation model at runtime).

---

## Results

**Product metric (the deployed system).** Retrieval over the validated 158-pair bank, evaluated with paraphrased real-style questions:

| Metric | Score |
|---|---|
| Recall@1 | 0.88 |
| **Recall@3** | **0.94** |
| MRR | 0.91 |

> *The assistant returns the correct validated answer about 94% of the time (top-3).*

**Analysis — classification model comparison** (6-intent task, held-out test, English, word + char TF-IDF). This study *motivated* the RAG design and is retained as analysis:

| Model | Role | Macro-F1 |
|---|---|---|
| ComplementNB | Baseline | 0.45 |
| Logistic Regression | Standalone | 0.64 |
| Linear SVM | Standalone | 0.66 |
| **Random Forest** | **Best (classical)** | **0.71** |
| AfroXLMR / AfriBERTa | Fine-tuned transformers — *negative result* | 0.24 / 0.45 |

**Key findings:** simple classical models **beat fine-tuned transformers** in this low-resource, weakly-labelled setting (transformers overfit ~580 examples); and **machine translation measurably degrades performance** — English macro-F1 ≈ 0.72 to Kinyarwanda ≈ 0.56 (**ΔF1 0.16, a 22% relative drop**). Together these justify retrieving validated content and generating from it, rather than training a classifier for the product.

---

## Repository structure

```
src/
  app.py            Streamlit frontend (consent gate, bilingual chat, responsive UI)
  rag.py            core: language detect -> safety -> retrieve -> Gemini -> disclaimer
data/
  grounding_bank.json          158 validated postpartum Q&A (the answer bank)
  mother/                       MOTHER source data + postpartum subset (+ Kinyarwanda)
  raw/amod_full.csv            Amod counselling corpus (analysis only)
notebooks/
  umubyeyi.ipynb    full analysis: data prep -> model comparison -> degradation -> retrieval
  amod_kinyarwanda.csv         translated/labelled modelling data
models/
  lang_detector.joblib         English/Kinyarwanda detector (used by the app)
  intent_classifier.joblib     classifier from the analysis (not used by the product)
assets/
  system_architecture_layered.png   the architecture figure shown above
docs/                          capstone report, slides, pilot pack (kept local)
.env.example                   template for the Gemini key (copy to .env)
```

---

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env          # then put a Gemini API key in .env
streamlit run src/app.py
```

- Get a free Gemini API key from <https://aistudio.google.com/apikey> and set `GEMINI_API_KEY` in `.env`.
- **Without a key the app still runs** but returns a graceful "unavailable" message instead of a generated answer. With a key, answers are generated fluently in-language.
- The full analysis notebook (`notebooks/umubyeyi.ipynb`) is Colab-ready: set a GPU runtime and Run All.

## Deployment

Deploys on **Streamlit Community Cloud** from this repo (`src/app.py`). Add the key under **Settings → Secrets** (TOML):

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-2.5-flash"
```

The app is lightweight (scikit-learn + a small index; no translation model at runtime), so it fits the free tier.

---

## Data and licensing

- **MOTHER** (Eyobu et al., *BMC Research Notes*, 2025; Harvard Dataverse `10.7910/DVN/EZLCH3`; CC BY 4.0) — medically-validated maternal Q&A (**data source: Uganda**), filtered to 158 postpartum pairs and used as the **validated answer bank**. The tool is built **for Rwandan mothers**; Rwanda-specific clinical validation is future work.
- **Amod** mental-health counselling corpus — used for the **analysis/model comparison only** (not served to users).

## Safety and ethics

Informational only, never diagnostic. A one-time **consent screen**, a **danger-sign crisis referral**, a per-answer **disclaimer**, **domain bounding**, and **no collection of personal/identifying data**. Intended for testing with proxy users / consenting volunteers, not as deployed clinical care.

## Limitations and future work

The answer bank is Ugandan-sourced and partly machine-translated, so it needs **Rwandan clinician / native-speaker validation**; the product depends on an external LLM API; the evaluation is small. Future work: a Rwanda-validated knowledge base, clinician sign-off, a larger user study, and WhatsApp/SMS or offline channels.

## Disclaimer

Umubyeyi is a **student research prototype**, **not a medical or diagnostic tool** and not a substitute for professional care. If you are worried about your health or your baby's, contact a nurse, midwife, or health worker. In a crisis, contact local emergency services.
