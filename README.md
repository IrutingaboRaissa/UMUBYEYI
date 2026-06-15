# Umubyeyi 🌷

**A Kinyarwanda AI chatbot supporting maternal mental wellbeing for first-time mothers in Rwanda.**

Author: Raissa IRUTINGABO · Supervisor: Samiratu Ntohsi · BSc Software Engineering

---

## What it does

A mother types in Kinyarwanda →
**NLLB-200** translates to English →
a **TF-IDF + ML classifier** routes the message to one of **6 maternal-wellness intents** →
the matching **expert-reviewed response template** (one per intent) is returned →
translated back to Kinyarwanda →
shown with a clinical disclaimer.

Two safety mechanisms wrap the pipeline:
- **Confidence gate** — low-confidence inputs fall back to a gentle general response.
- **Danger-sign override** — self-harm / emergency keywords bypass classification and surface a helpline message.

The 6 intents: `sadness_low_mood`, `anxiety_worry`, `sleep`, `overwhelmed_identity`, `relationship_support`, `self_care_coping`.

## Results (model ladder)

Trained on the Amod counseling corpus, mapped to the 6 intents, same stratified 80/20 split (macro-averaged F1):

| | Model | Language | Accuracy | F1 |
|---|-------|----------|----------|----|
| Baseline | Naive Bayes (reference, not deployed) | English | 0.39 | 0.22 |
| **Model 1** | TF-IDF + Logistic Regression *(deployed)* | English | **0.61** | **0.60** |
| Model 2 | MiniLM embeddings + MLP | Kinyarwanda | 0.42 | 0.40 |
| Model 3 | AfroXLMR fine-tune | Kinyarwanda | *trained on Colab — see below* | |

Model 1 is the deployed classifier. The Kinyarwanda-direct models quantify cross-lingual transfer (see the notebook's degradation analysis).

## Repository structure

```
data/        Amod corpus, intent labels, Kinyarwanda translations, response templates
notebooks/   umubyeyi.ipynb (full pipeline, Colab-ready)
src/         app.py (Streamlit chatbot) · build_slides.py (deck generator)
models/      intent_classifier.joblib · tfidf_vectorizer.joblib
reports/     metrics (JSON) and figures
docs/        capstone report + presentation
```

## Run locally

**App:**
```bash
pip install -r requirements.txt
# optional, for live Kinyarwanda translation (heavy): pip install transformers torch
streamlit run src/app.py
```

**Full pipeline (notebook):** open `notebooks/umubyeyi.ipynb` in Google Colab → set runtime to T4 GPU → Run All. It pulls the data from this repo and runs the baseline plus all three models (including the AfroXLMR fine-tune) end-to-end.

## Deployment notes

The app deploys on **Streamlit Community Cloud** (free) using `requirements.txt`. The free tier caps RAM at ~1 GB, so the **live NLLB translator (~2.4 GB) cannot run there** — `src/app.py` detects this and falls back to passing text straight to the classifier. For a full Kinyarwanda demo with live translation, run locally or on a host with more memory.

## Data & licensing

- **Amod** mental-health counseling conversations — classifier training + intent framing.
- Response templates are sourced from WHO / UNFPA maternal-health guidance.

## ⚠️ Disclaimer

Umubyeyi is an informational research prototype, **not a medical or diagnostic tool**. Every response carries a disclaimer and a safety pathway. It is not a substitute for professional mental-health care.
