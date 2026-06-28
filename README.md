<!-- Hugging Face Space config (read by HF when this repo is deployed as a Space; GitHub ignores it). -->
---
title: Umubyeyi
emoji: 🌷
colorFrom: pink
colorTo: purple
sdk: streamlit
sdk_version: 1.48.1
app_file: src/app.py
pinned: false
short_description: Bilingual grounded-generation chatbot for postpartum support of Rwandan mothers
---

# Umubyeyi 🌷

**A bilingual (Kinyarwanda / English) chatbot that supports first-time mothers in Rwanda during the 0–6 month postpartum window — answering their questions with safe, validated, language-matched information.**

Author: **Raissa IRUTINGABO** · Supervisor: **Samiratu Ntohsi** · BSc Software Engineering, African Leadership University

---

## Why this project

In Rwanda, antenatal care is comparatively well-attended and most deliveries are supervised, but **postnatal contact drops sharply after birth** — the WHO calls the postnatal period the most neglected phase of maternal care. Yet the **0–6 months after birth** is exactly when postpartum depression, breastfeeding difficulties, recovery complications, and newborn-care anxiety peak. First-time mothers are the most exposed, and they often lack timely, trustworthy information **in Kinyarwanda**. Umubyeyi is a small, safe, deployable assistant for that gap.

---

## What it does

You type a question in **Kinyarwanda or English**, and Umubyeyi replies **in the same language** with a warm, on-topic answer grounded in a medically-validated maternal knowledge base — wrapped in safety mechanisms.

- 🗣️ **Bilingual & auto-detected** — no language switch; each message is detected and answered in its own language.
- 📚 **Grounded answers** — clinical answers are drawn from validated content, not invented.
- 💛 **Emotional support** — for feelings (sadness, anxiety, overwhelm) it responds with empathy and gentle, non-diagnostic guidance.
- 🛟 **Safety first** — a danger-sign override surfaces a crisis referral; every answer carries a disclaimer; off-topic questions (malaria, COVID, farming…) are politely declined.
- 🎯 **Scoped** — strictly 0–6 months postpartum, informational only (never diagnostic).

---

## How it works (architecture)

A **layered, retrieval-augmented-generation (RAG)** design. Safety-critical logic is deterministic and kept independent of the language model.

![Umubyeyi layered system architecture](assets/system_architecture_layered.png)

*Layered system architecture — tiers, components, technologies, and inter-layer protocols.*

```
User message (Kinyarwanda or English)
   │
   ├─ 1. Language detector  (char n-gram model, 99.95% accuracy) → reply language
   ├─ 2. Safety check       (danger keywords → crisis referral, bypasses the LLM)
   ├─ 3. Retrieve           (TF-IDF char n-grams + cosine → closest validated snippet)
   ├─ 4. Generate           (Gemini writes the answer IN THE USER'S LANGUAGE,
   │                          using ONLY the validated fact; stays on-domain, no diagnosis)
   └─ 5. Disclaimer         (appended) → rendered  (+ optional 👍/👎 feedback)

   Graceful fallback: if no API key / the API errors, the validated answer is
   returned extractively — the system never fails open.
```

| Tier | Component | Technology |
|---|---|---|
| Presentation | Streamlit chat — consent gate, bilingual chat, feedback | Streamlit |
| Application | Orchestrator + language detector + safety module | Python, scikit-learn |
| Knowledge | Retriever over the validated answer bank | TF-IDF (char n-grams) + cosine |
| External | In-language answer generation | Google Gemini (`gemini-flash-latest`) |

---

## Results

**Product metric (the deployed system).** Retrieval over the validated 158-pair bank, evaluated with paraphrased real-style questions:

| Metric | Score |
|---|---|
| Recall@1 | 0.88 |
| **Recall@3** | **0.94** |
| MRR | 0.91 |

> *The assistant returns the correct validated answer ~94 % of the time (top-3).*

**Analysis — classification model comparison** (6-intent task, held-out test, English, word + char TF-IDF). This study *motivated* the RAG design and is retained as analysis:

| Model | Role | Macro-F1 |
|---|---|---|
| ComplementNB | Baseline | 0.45 |
| Logistic Regression | Standalone | 0.64 |
| Linear SVM | Standalone | 0.66 |
| **Random Forest** | **Best (classical)** | **0.71** |
| AfroXLMR / AfriBERTa | Fine-tuned transformers — *negative result* | 0.24 / 0.45 |

**Key findings:** simple classical models **beat fine-tuned transformers** in this low-resource, weakly-labelled setting (transformers overfit ~580 examples); and **machine translation measurably degrades performance** — English macro-F1 ≈ 0.72 → Kinyarwanda ≈ 0.56 (**ΔF1 0.16, a 22 % relative drop**). Together these justify retrieving validated content and generating from it, rather than training a classifier for the product.

---

## Repository structure

```
src/
  app.py            Streamlit frontend (consent gate, bilingual chat, feedback)
  rag.py            core: language detect → safety → retrieve → Gemini → disclaimer
data/
  grounding_bank.json          158 validated postpartum Q&A (the answer bank)
  mother/                       MOTHER source data + postpartum subset (+ Kinyarwanda)
  raw/amod_full.csv            Amod counselling corpus (analysis only)
notebooks/
  umubyeyi.ipynb    full analysis: data prep → model comparison → degradation → retrieval
  amod_kinyarwanda.csv         translated/labelled modelling data
models/
  lang_detector.joblib         English/Kinyarwanda detector (used by the app)
  intent_classifier.joblib     classifier from the analysis (not used by the product)
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
- **Without a key the app still runs** — it falls back to returning the validated answer directly (English is clean; Kinyarwanda uses machine-translated drafts). With a key, answers are generated fluently in-language.
- The full analysis notebook (`notebooks/umubyeyi.ipynb`) is Colab-ready: set a GPU runtime and Run All.

## Deployment

Deploys on **Streamlit Community Cloud** from this repo (`src/app.py`). Add the key under **Settings → Secrets**:

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-flash-latest"
```

The app is lightweight (scikit-learn + a small index; no translation model at runtime), so it fits the free tier. See `DEPLOY.md` for full steps incl. optional feedback-to-Google-Sheet.

---

## Data & licensing

- **MOTHER** (Eyobu et al., *BMC Research Notes*, 2025; Harvard Dataverse `10.7910/DVN/EZLCH3`; CC BY 4.0) — medically-validated maternal Q&A (**data source: Uganda**), filtered to 158 postpartum pairs and used as the **validated answer bank**. The tool is built **for Rwandan mothers**; Rwanda-specific clinical validation is future work.
- **Amod** mental-health counselling corpus — used for the **analysis/model comparison only** (not served to users).

## Safety & ethics

Informational only, never diagnostic. A one-time **consent screen**, a **danger-sign crisis referral**, a per-answer **disclaimer**, **domain bounding**, and **no collection of personal/identifying data**. Intended for testing with proxy users / consenting volunteers, not as deployed clinical care.

## Limitations & future work

The answer bank is Ugandan-sourced and partly machine-translated → needs **Rwandan clinician / native-speaker validation**; the product depends on an external LLM API; the evaluation is small. Future work: a Rwanda-validated knowledge base, clinician sign-off, a larger user study, and WhatsApp/SMS or offline channels.

## ⚠️ Disclaimer

Umubyeyi is a **student research prototype**, **not a medical or diagnostic tool** and not a substitute for professional care. If you are worried about your health or your baby's, contact a nurse, midwife, or health worker. In a crisis, contact local emergency services.
