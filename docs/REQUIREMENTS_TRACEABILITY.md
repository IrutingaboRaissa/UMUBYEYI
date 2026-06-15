# Umubyeyi — Requirements & Claims Traceability

**Purpose:** every substantive claim in `Umubyeyi_Final_Capstone.docx` is listed here with
the evidence that backs it in this repo, a status, and the action needed before submission.
Use it as the pre-submission checklist so nothing is *claimed-but-not-built* and the document
never contradicts the code.

_Last cross-checked: 2026-06-10 against the capstone doc + current repo._

### Status legend
- ✅ **DONE** — claim is backed by a real artifact in the repo.
- 🟡 **PARTIAL** — partly implemented; finish or soften the wording.
- 🔴 **NOT YET** — claimed/planned but not built (some are legitimately later in the timeline).
- ⚠️ **MISMATCH** — the document states something the code/reality does *not* match. **Fix one side.** Highest risk in a viva.

---

## ⭐ Top priorities before submission (the risky ones)
1. ⚠️ **Knowledge base size** — doc claims **80–120 entries** (Table 5: ~40 WHO + ~25 UNFPA); repo has **8**. Either build the KB up or restate the number honestly.
2. ⚠️ **Dense NN framework** — doc + Dev-Tools table say **TensorFlow/Keras** with dropout 0.3 / 50 epochs; code uses **scikit-learn `MLPClassifier`** (no Keras, no dropout). TensorFlow is not used anywhere.
3. ⚠️ **TF-IDF vocabulary** — doc §3.5.1 & Fig 3.2 say **5,000 features**; code uses **`max_features=8000`**.
4. ⚠️ **Doc contradicts itself on persistence** — §3.5/§3.9 say *stateless, no DB, nothing logged*, but the **Sequence Diagram (Fig 3.6) still shows `log_query_to_db()`** and the **Use-Case Admin has "Review Query Logs."** Remove these.
5. 🔴 **Cross-lingual degradation coefficient** — the *central scientific contribution* (RQ2/Obj4) is **not yet measured**. No experiment script produces a coefficient.
6. 🔴 **Gold labels + Cohen's Kappa** — results are still on **weak/silver labels**; manual labeling + κ>0.70 not done (toolkit is ready).
7. 🔴 **MIT license / GitHub** — no `LICENSE`, no `README`, **no commits pushed** (remote exists). Doc claims an open MIT repo.

---

## A. Specific Objectives (§1.4) & deliverables

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| A1 | Lit review across 5 areas; **KB of 80–120 validated Q&A** by Wk2 | Lit review ✅ (Ch.2). KB = **8 entries** at `data/knowledge_base/mental_wellness_kb.json` | 🟡 lit done / 🔴 KB far short |
| A2 | Filter+label Amod → **800–1,200 entries**, **10% inter-rater κ>0.70** by Wk3 | Weak/silver labels only (724). Gold toolkit built (`src/make_gold_labeling_sheet.py`, `data/gold/`, `src/eval_gold.py`) but **not labeled**, κ not computed | 🔴 NOT YET |
| A3 | Train **3 models** (LR, SVM, dense NN) on TF-IDF; acc + macro-F1; 80/20 stratified by Wk6 | ✅ `src/train_baseline.py` → `reports/baseline_metrics.json` (LR 0.61 acc/0.60 F1, SVM, MLP). **On weak labels** (see A2) and model specifics differ (see C) | ✅ done / on silver labels |
| A4 | NLLB pipeline + **degradation coefficient** by Wk7 | NLLB wired ✅ (`src/app.py`, `src/translate_kb.py`). **Coefficient experiment not run** | 🟡 pipeline / 🔴 measurement |
| A5 | Streamlit UI + **SUS study, 10 proxy users, mean >70** by Wk9 | UI ✅ (`src/app.py`). SUS study not done | 🟡 UI / 🔴 study (timeline) |

## B. Dataset & preparation (§3.3)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| B1 | Amod = **3,512 rows / 995 unique** questions | ✅ verified; `data/raw/amod_full.csv`, dedup in `train_baseline.py` | ✅ |
| B2 | De-duplicate on unique questions → no train/test leakage | ✅ `drop_duplicates(subset="Context")` + stratified split | ✅ |
| B3 | Keyword filtering removes off-scope (trauma, addiction, PTSD…) | ✅ `EXCLUDE` list in `train_baseline.py` | ✅ |
| B4 | Manual intent labeling into 6 categories | 🔴 weak keyword labels only (gold pending, see A2) | 🔴 |
| B5 | Cohen's κ > 0.70 inter-rater | 🔴 not computed (`eval_gold.py` ready to compute it) | 🔴 |

## C. ML pipeline specifics (§3.5) — high viva-risk detail

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| C1 | TF-IDF **5,000 features** (§3.5.1, Fig 3.2) | code `max_features=8000` (≈4,438 used) | ⚠️ MISMATCH |
| C2 | TF-IDF ngram 1–2, sublinear TF | ✅ matches code | ✅ |
| C3 | Stopwords via **NLTK** corpus | code uses sklearn `stop_words="english"` | ⚠️ minor MISMATCH |
| C4 | LR L2, **C grid [0.01,0.1,1,10], 5-fold CV** | code fixed `C=1.0`, **no grid search** | ⚠️ MISMATCH |
| C5 | SVM linear, balanced weights, **calibrated** probabilities | ✅ `CalibratedClassifierCV(LinearSVC(class_weight="balanced"))` | ✅ |
| C6 | Dense NN: **TensorFlow/Keras**, dropout 0.3, 50 epochs early-stop, batch 32 | code = sklearn `MLPClassifier(256,128)`, L2 `alpha`, `max_iter=300`, **no Keras/dropout** | ⚠️ MAJOR MISMATCH |
| C7 | 80/20 stratified split; acc, macro-F1, per-class P/R/F1 | ✅ matches | ✅ |
| C8 | Selective prediction (coverage vs accuracy) | ✅ in `baseline_metrics.json` | ✅ |

## D. Knowledge base (§3.3.1, §3.4, Fig 3.5, Table 5)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| D1 | **80–120** entries (~40 WHO + ~25 UNFPA, Table 5) | **8 entries** total | ⚠️ MISMATCH |
| D2 | Sourced from **WHO + UNFPA** | ✅ `sources` fields + `SOURCES.md`. **But** §2.7 & Fig 3.1 still say "WHO/UNFPA/**RBC**" (RBC was dropped per §3.3.3) | 🟡 leftover RBC mentions |
| D3 | JSON schema (id, intent, trigger_examples, empathy, guidance, when_to_seek_help, danger_flag, sources) | ✅ exact match to actual KB | ✅ |
| D4 | KB **pre-translated to Kinyarwanda + human-validated** | MT done ✅ (`translate_kb.py` → `*_rw` fields); **human validation pending** | 🟡 |

## E. Translation & the central contribution (§3.5.5–3.5.6, §2.6)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| E1 | NLLB-200 translates input Kinyarwanda→English | ✅ `kin_to_eng()` in `app.py` (cached) | ✅ |
| E2 | Output is pre-translated KB, **no live output MT** | ✅ app shows `*_rw`; matches §3.5.6 design | ✅ |
| E3 | **Cross-lingual degradation coefficient** (English-direct vs Kinyarwanda round-trip) | 🔴 **not measured** — no experiment/script produces it. (Anecdote: NLLB dropped a negation in testing — useful illustration, not a measurement) | 🔴 |
| E4 | **Back-translation input check** (Fig table 12, §3.5.6) | 🔴 not implemented | 🔴 |

## F. Safety & confidence (§3.4, §3.5.6, §3.7, §3.9)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| F1 | Confidence **<0.40 → general fallback** | ✅ `CONF_GATE` in `app.py` | ✅ |
| F2 | **Ranking gate**: KB entries ranked by relevance, returned only above a threshold (second gate) | 🔴 app picks first entry per intent; **no ranking / no relevance threshold** | 🔴 |
| F3 | Danger keywords → bypass → **Rwanda Hotline 114** | 🟡 keyword override + escalation message exist, but **"114" is not in the message** | ⚠️ add 114 |
| F4 | Visible disclaimer on every response | ✅ footer present. Wording differs from §3.9's quoted Kinyarwanda text | 🟡 align text |
| F5 | **Un-skippable onboarding disclaimer** each session | 🔴 only a greeting + per-reply footer; no onboarding screen | 🔴 |
| F6 | Empty/short-input & NLLB-timeout handlers (Table 12) | 🔴 not implemented | 🔴 |

## G. Architecture & app (§3.4, §3.6)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| G1 | Streamlit 4-layer modular pipeline | ✅ `app.py` (input→translate→classify→retrieve) | ✅ |
| G2 | **Stateless; no query/personal data persisted** | ✅ app keeps only `st.session_state`; nothing written to disk | ✅ |
| G3 | Sequence Diagram (Fig 3.6) ends with **`log_query_to_db()`** | ⚠️ **contradicts G2** and the no-DB design — remove from figure | ⚠️ MISMATCH (internal) |
| G4 | Admin use cases: Update KB, **Review Query Logs** | 🔴 no admin UI; "Review Query Logs" also contradicts G2 | 🔴 / ⚠️ |
| G5 | Model artifacts persisted as joblib, loaded at startup | ✅ `models/*.joblib`, loaded in `app.py` | ✅ |

## H. Ethics, tooling, deployment, reproducibility (§3.8, §3.9, Tables 1 & 13)

| # | Claim (doc) | Evidence / reality | Status |
|---|---|---|---|
| H1 | Open-source **MIT license on GitHub**; code + data + docs published | 🔴 no `LICENSE`, no `README`, **0 commits pushed** (remote = github.com/IrutingaboRaissa/UMUBYEYI) | 🔴 |
| H2 | Reproducible pipeline | 🟡 scripts run, but **no `requirements.txt`** | 🟡 |
| H3 | **Python 3.10** (Table 13) | actual env = **Python 3.13** | ⚠️ minor MISMATCH |
| H4 | **Google Colab Pro** for GPU NN training (Budget) | NN trained on **CPU** via sklearn; no GPU/Colab used | ⚠️ budget item moot |
| H5 | SUS via anonymous questionnaires; consent forms (PU-01..10) | 🔴 study not yet run (Wk9 timeline) | 🔴 (timeline) |
| H6 | Deploy on **Streamlit Community Cloud** | 🔴 runs locally only | 🔴 (timeline) |
| H7 | Disclaimer footer text (exact Kinyarwanda in §3.9) | app footer present but **different wording** | 🟡 align |

---

## How to use this before submission
1. **Fix every ⚠️ MISMATCH** — these are the items where the document literally disagrees with the code; an examiner can catch them by reading both. Either change the code to match the doc, or change the doc to match reality (often easier + still honest).
2. **Decide scope on each 🔴** — for genuinely-later-timeline items (SUS, deployment), make sure the doc frames them as *planned*, not *done*. For the central contribution (E3) and gold labels (A2/B4), these are the high-value pieces still to build.
3. Re-run this check after edits — update the Status column so the final doc and repo agree line-for-line.
