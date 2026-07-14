# Umubyeyi

Umubyeyi is a bilingual English/Kinyarwanda postpartum emotional-well-being assistant for first-time
mothers. It combines trained screening-risk classifiers, source-grounded retrieval, deterministic
safety rules, a reproducible project fine-tuning pipeline, a guided check-in, mood history, and
self-care support. It is a research prototype and does not diagnose or replace a health professional.

## Submission links

- **Deployed application:** https://firstmumassist-six.vercel.app/
- **Five-minute technical demo:** `ADD VIDEO URL BEFORE SUBMISSION`
- **Repository:** https://github.com/IrutingaboRaissa/UMUBYEYI

The production URL was verified as publicly accessible without Vercel authentication on July 14, 2026.
The video placeholder must be replaced after the final commit is deployed and recorded.

## Core functionality

- English and Kinyarwanda emotional-well-being conversations
- deterministic crisis, acute-health, baby-care, and unrelated-topic routing
- same-language character n-gram TF-IDF retrieval across 14 source-attributed topics
- project-trained bilingual six-intent classifier mapped to reviewed evidence topics
- mT5 LoRA fine-tuning on genuine ESConv and AMOD responses
- coverage-controlled grounded Gemini generation with one corrective retry
- model-generated greetings/small talk; no canned conversational response list
- strict generated-output grounding validation and direct-passage fallback
- response-path provenance retained in API metadata and evaluation logs, without a user-facing model badge
- optional Ollama phrasing as a secondary local path
- 15-input guided screening-risk check-in with a non-diagnostic disclaimer
- browser-local mood and conversation history
- self-care guidance, affirmations, feedback, and mobile navigation

## Architecture

```text
Free-text message                         Guided check-in
       |                                        |
Safety and scope rules                    15 validated answers
       |                                        |
Language detection                        preprocessing pipeline
       |                                        |
trained intent classifier: category        trained Logistic Regression
       |                                        |
Top-3 knowledge-base matches               non-diagnostic result
       |
answer generation constrained by the selected evidence
       |
grounding/coverage validation -> response or evidence fallback
```

The 800 participant records train screening classifiers. They are never used as chatbot answers.

The project-trained models have distinct responsibilities. The screening classifier estimates the
guided check-in risk category. The bilingual intent classifier predicts one of six coarse emotional
categories learned from the AMOD-derived weak labels; those categories map to the 14 reviewed
postpartum topics. Retrieval then finds the most relevant reviewed passages. Finally, a generator expresses that selected evidence
as a clear, supportive response; it does not independently choose medical facts. Safety-critical
crisis and referral decisions remain deterministic rather than being delegated to a text generator.

In the hosted application, Gemini performs the final natural-language realization because it produced
clearer and more empathetic bilingual wording in development. It is constrained by the topics and
evidence selected by the project pipeline, and its output must pass project-owned concern-coverage and
grounding checks. The local mT5 path is enabled only after the new ESConv/AMOD Colab run produces an
adapter with the matching provenance manifest; otherwise the system falls back to reviewed evidence.

## Prerequisites

- Windows 10/11, macOS, or Linux
- Python 3.11–3.13
- Node.js 20 or newer and npm
- Git
- enough memory to load the 300M-parameter mT5-small base model for local generation
- Ollama, optional secondary generation path only

## Installation from a fresh clone

### 1. Clone and enter the repository

```powershell
git clone https://github.com/IrutingaboRaissa/UMUBYEYI.git
cd UMUBYEYI
```

### 2. Create and activate a Python environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-local.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-local.txt
```

### 3. Install the web dependencies

```powershell
npm ci
```

### 4. Configure the environment

```powershell
Copy-Item .env.example .env.local
```

Analytics are optional. The application uses a local SQLite file when no `DATABASE_URL` is provided.
Create a fresh Gemini API key and put it only in the git-ignored `.env.local` file as
`GEMINI_API_KEY=...`. Never commit or paste a real key into source code, a notebook, or the report.
Without a key, the app safely continues through its local/retrieval paths.

### 5. Fine-tuned local response model

Run `notebooks/umubyeyi.ipynb` on a Colab T4 to produce the current `esconv-amod-v1` LoRA adapter.
The application deliberately refuses to load the superseded adapter trained on templated prompts.
After extracting the new artifact under `models/umubyeyi-mt5-lora/`, Transformers downloads the
`google/mt5-small` base checkpoint and applies the adapter. Set `UMU_DISABLE_FINETUNED=1` when
intentionally testing retrieval fallback.

Optional secondary Ollama path:

```powershell
ollama pull gemma3:4b
ollama create umubyeyi -f ollama/Modelfile
$env:OLLAMA_MODEL = "umubyeyi"
```

`ollama create` applies project instructions and does not fine-tune Ollama weights. This is distinct
from the mT5 LoRA adapter, whose trainable weights were updated by this project. If neither generator
returns an answer that passes grounding validation, the application returns the retrieved passage.

Gemini receives only the current message and three reviewed passages selected by the project-trained
topic classifier, not conversation history. Its structured response must enumerate the concerns it
identified, confirm each concern was covered, identify the exact factual sentences in its answer, cite
supporting evidence, and pass local coverage and grounding validation. A rejected response receives one
corrective retry before the system falls back to the project-fine-tuned model or source passage.
It is an external inference component and is not described as project-fine-tuned.
The verified default is `gemini-3.1-flash-lite`; it can be changed with `GEMINI_MODEL`.

Ordinary greetings are generated by Gemini and recorded internally with `gemini_conversation` mode
metadata; they are not selected from canned greeting variants and no model badge is shown in the UI.
If Gemini is unavailable, the app returns an availability notice.
Fixed application text is restricted to safety, clinical referral, scope redirection, disclaimer, and
failure handling. These controls are intentionally deterministic and are not presented as learned output.

### 6. Start the complete local application

```powershell
npm run dev
```

`npm run dev` starts both the Next.js interface and local Python API adapter. Open the URL printed by
Next.js, normally http://localhost:3000. If port 3000 is occupied, it selects another port.

## Verification

### Automated tests

```powershell
python -m pytest -q
```

Current verified result: **67 tests passed**. Strategies include unit, parameterized, boundary-value,
invalid-input, offline/fallback, bilingual retrieval, safety, response-contract, dependency-injection,
HTTP integration, indirect/obfuscated crisis messages, Gemini failure fallback, generation-data
leakage control, layered-evaluation integrity, and generated-output grounding validation.

### Layered model evaluation

```powershell
python evaluate_system_layers.py
```

No single accuracy score describes the system because classification, retrieval, generation, and
safety routing are different tasks. The command writes auditable cases, JSON metrics, and figures to
`reports/system_evaluation/`.

| Layer | Evaluation evidence | Primary result |
|---|---|---:|
| Full screening classifier | 120 untouched participant rows | F1 0.7890 |
| Practical check-in classifier | 120 untouched participant rows | F1 0.7544 |
| Bilingual intent classifier | 180 untouched bilingual cases | English macro-F1 0.7180; Kinyarwanda 0.2762* |
| English question-to-topic retrieval | 14 controlled paraphrases | Top-1 0.6429; Top-3 0.9286 |
| Kinyarwanda question-to-topic retrieval | 14 controlled project-authored cases | Top-1 1.0000* |
| ESConv/AMOD generator | conversation/question-grouped test | Metrics pending the documented Colab run |
| Safety/scope routing | 16 controlled cases across five categories | Accuracy 1.0000* |

`*` Controlled results are software/behavior evidence, not real-user or clinical validity. The
Kinyarwanda retrieval cases share domain vocabulary with the knowledge bank and require native review,
so their perfect score must not be presented as proof of generalization. English Top-1 performance also
shows that the lexical retriever can confuse indirect paraphrases even when the right topic is usually
within its Top-3 results.

### Project-trained intent classifier

```powershell
python train_topic_classifier.py
```

The persisted `models/topic_classifier.joblib` pipeline combines word and character TF-IDF with the
best of seven probabilistic classifiers. It uses 596 deduplicated bilingual question pairs derived
from `Amod/mental_health_counseling_conversations`: 417 train, 89 validation, and 90 untouched test
rows. English and Kinyarwanda versions always remain in the same split. The labels are keyword weak
labels and the Kinyarwanda text is NLLB-200 machine translation, so the scores measure reproduction of
project labels rather than clinical validity. Runtime maps the Top-3 coarse intents to reviewed
postpartum evidence topics.

The unified notebook also prepares a zero-shot NLLB translation-pivot experiment using
`facebook/nllb-200-distilled-600M` (`kin_Latn` ↔ `eng_Latn`). It compares direct Kinyarwanda intent
classification with Kinyarwanda-to-English translation followed by classification and exports cases
for native-speaker review. NLLB fine-tuning remains gated on independently sourced or human-corrected
parallel data; retraining NLLB on its own cached translations would be circular. The official
[Hugging Face NLLB documentation](https://huggingface.co/docs/transformers/en/model_doc/nllb) is
recorded in `docs/REFERENCES.md` for the final report.

Automatic text metrics cannot establish whether a response is empathetic, natural, or culturally
appropriate. The Colab artifact `generator_human_review_cases.csv` contains held-out
outputs and blank 1–5 review fields for relevance, fluency, empathy, grounding, safety, and language
correctness. Scores must only be reported after named reviewers complete the sheet; blank fields are
deliberately not replaced with model-generated ratings.

### Production build

```powershell
npm run build
npm run start
```

The current Next.js production build completes successfully.

### Reproduce model training

```powershell
python train_ppd_classifier.py
python train_checkin_classifier.py
python train_grounded_generator.py
```

These commands regenerate the screening pipelines and bilingual mT5 LoRA generator. Generator training
writes its adapter under `models/umubyeyi-mt5-lora/` and evidence under `reports/generator/`. Use
`--smoke` only to verify the pipeline quickly; the reported metrics come from the complete run. The
tabular PPD participant data is never used as generator supervision.

The project now has one end-to-end notebook: `notebooks/umubyeyi.ipynb`. Open it in Google Colab,
select **Runtime -> Change runtime type -> T4 GPU**, and choose **Runtime -> Run all**. It clones the
project data automatically and runs data auditing, missing-value preprocessing, seven-model classifier
comparisons, confusion matrices, explainability, bilingual retrieval, LoRA generator fine-tuning,
loss curves, held-out evaluation, and artifact export. No API key or manual knowledge-file upload is
required. The downloaded zip contains the fitted pipelines, LoRA adapter, metrics, loss history, and
English/Kinyarwanda human-review cases.

### Performance benchmark

```powershell
python benchmark_system.py
```

The command records OS, Python version, processor, logical CPU count and 100-run latency summaries in
`reports/performance/local_benchmark.json`. Run it on a second machine or operating system before the
defense and retain both result files for cross-environment evidence.

Current Windows 11 / Python 3.13.7 / 8-logical-CPU fallback-mode medians:

| Runtime path | Median latency |
|---|---:|
| Crisis safety routing | 0.002 ms |
| Greeting | 0.013 ms |
| English retrieval response | 3.955 ms |
| Kinyarwanda retrieval response | 3.335 ms |
| Guided check-in prediction | 15.301 ms |

These are steady-state fallback measurements and exclude fine-tuned mT5, Gemini network, and Ollama
generation latency.

## Supervised machine-learning experiments

The licensed dataset contains 800 postpartum participant records from Bangladesh: Raisa and Kaiser,
*Data for Postpartum Depression Prediction in Bangladesh*, Mendeley Data version 3,
DOI `10.17632/4nznnrk8cg.3`, CC BY 4.0.

The binary target is elevated EPDS screening risk: High versus Low/Medium. All concurrent EPDS/PHQ
items, totals, and derived labels are excluded to prevent target leakage.

### Data preparation and missing values

The raw file contains 800 rows, 70 columns, no duplicate rows and 4,312 missing cells. Rows with
missing predictors were not discarded, because doing so would unnecessarily reduce an already modest
dataset. Preprocessing is part of each scikit-learn `Pipeline`:

1. The target is converted to `elevated` for EPDS High and `not_elevated` for EPDS Low/Medium.
2. The identifier, target, concurrent questionnaire items, totals and derived results are removed to
   prevent target leakage, leaving 46 predictors for the full experiment.
3. The data is stratified into 560 training, 120 validation and 120 untouched test rows before any
   imputation is learned.
4. Numeric predictors use median imputation followed by standardisation.
5. Categorical predictors use most-frequent imputation followed by one-hot encoding. Unknown test or
   production categories are ignored safely, and categories seen fewer than twice are grouped.
6. Each candidate pipeline learns its imputation values, scaling values and category vocabulary only
   from its training input. The untouched test data therefore cannot influence preprocessing or model
   selection.
7. After validation F1 selects the winning algorithm, that configuration is refitted on training plus
   validation rows and evaluated once on the test set.

![Features with the most missing values](reports/ppd_classifier/figures/03_missing_values.png)

- stratified split: 560 training / 120 validation / 120 untouched test
- seed: 42
- candidates: Dummy, Logistic Regression, Decision Tree, Random Forest, Extra Trees, SVM, and KNN
- selection: validation F1-score for the `elevated` class

### Full 46-predictor model comparison — validation set

| Candidate | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Dummy baseline | 0.5667 | 0.0000 | 0.0000 | 0.0000 |
| Logistic Regression | 0.6750 | 0.6066 | 0.7115 | 0.6549 |
| Decision Tree | 0.6333 | 0.5952 | 0.4808 | 0.5319 |
| **Random Forest — selected** | **0.7583** | **0.7091** | **0.7500** | **0.7290** |
| Extra Trees | 0.7417 | 0.6780 | 0.7692 | 0.7207 |
| Support Vector Machine | 0.7417 | 0.6721 | 0.7885 | 0.7257 |
| K-Nearest Neighbors | 0.7583 | 0.8710 | 0.5192 | 0.6506 |

![Full screening model validation comparison](reports/ppd_classifier/figures/05_validation_model_comparison.png)

### Reduced 15-input check-in comparison — validation set

| Candidate | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Dummy baseline | 0.5667 | 0.0000 | 0.0000 | 0.0000 |
| **Logistic Regression — selected** | **0.7417** | **0.6780** | **0.7692** | **0.7207** |
| Decision Tree | 0.7250 | 0.6792 | 0.6923 | 0.6857 |
| Random Forest | 0.7250 | 0.6727 | 0.7115 | 0.6916 |
| Extra Trees | 0.7000 | 0.6379 | 0.7115 | 0.6727 |
| Support Vector Machine | 0.7250 | 0.6667 | 0.7308 | 0.6972 |
| K-Nearest Neighbors | 0.7000 | 0.6667 | 0.6154 | 0.6400 |

![Guided check-in model validation comparison](reports/ppd_checkin/figures/05_validation_model_comparison.png)

### Selected models — untouched test set

| Experiment | Selected model | Accuracy | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| Full 46-predictor research model | Random Forest | 0.8083 | 0.7679 | 0.8113 | 0.7890 |
| Reduced 15-input check-in | Logistic Regression | 0.7667 | 0.7049 | 0.8113 | 0.7544 |

These are held-out experimental results, not clinical validation.


## Fine-tuned grounded generator

The current notebook fine-tunes `google/mt5-small` with LoRA on genuine conversational targets rather
than generated templates:

- **ESConv:** original supporter turns from 1,300 emotional-support conversations, capped at six
  supporter turns per conversation. Official commit
  `f262d062ad74cb39b17ea476facc81568ddcba24`; academic research use only.
- **AMOD:** original counselor responses for questions retained by the project's six weak intent
  labels. Hugging Face revision `d7e86f0813c5690181b41f97403c3674aa55dcef`.
- **Postpartum knowledge base:** 14 reviewed English/Kinyarwanda topics used only for retrieval. It is
  not expanded into templated training conversations.

Complete ESConv conversations and repeated AMOD questions are assigned to one split, preventing turns
or alternate counselor responses from crossing training and evaluation. The notebook evaluates the
base and fine-tuned model with held-out ROUGE-L, Distinct-2, loss curves, and blank human-review fields.
No post-change generator score is claimed until the unified Colab notebook is executed and its artifact
is retained.

Both conversational datasets are English and are not postpartum-specific. Consequently, the trained
generator is presented as an English emotional-support adaptation, not a bilingual clinical model.
AMOD's Kinyarwanda questions support intent-classification research only; they do not provide
Kinyarwanda answer targets. The hosted application therefore keeps grounded Gemini/direct retrieval
for Kinyarwanda and discloses that Gemini is an external model.

### Data provenance

Detailed source, license, version, transformation, and checksum information is stored in
`data/external/README.md` and `data/intent/README.md`. ESConv is downloaded from its official
repository at runtime and verified with SHA-256. The repository does not redistribute the corpus.

## Deployment plan

### Why mT5 is not loaded by the current Vercel function

The LoRA adapter is compact, but it cannot run alone: inference must also load the complete
`google/mt5-small` base checkpoint. The PyTorch checkpoint is approximately 1.2 GB, before adding
PyTorch, Transformers, PEFT, SentencePiece and runtime memory. The current Vercel Python function is
deliberately lightweight, configured for a 45-second request and excludes those local dependencies.
The standard Python function bundle limit is 500 MB, so this model stack does not fit that deployment
path. See the [Vercel Python runtime limits](https://vercel.com/docs/functions/runtimes/python) and the
[mT5-small checkpoint files](https://huggingface.co/google/mt5-small/tree/main).

Vercel introduced large Functions of up to 5 GB on Fluid Compute in June 2026, so mT5 on Vercel is no
longer categorically impossible. It would still require a separate deployment experiment covering
large-function eligibility, memory, cold-start latency, CPU inference time and cost. Enabling it just
before the defense would change the tested production architecture, so the present design keeps mT5
as the reproducible local/Colab fine-tuning path and uses the lighter grounded hosted path.

1. Run tests and the production build locally.
2. Commit and push the exact tested revision.
3. Import the GitHub repository into Vercel.
4. Configure optional `DATABASE_URL` in project environment variables.
5. Deploy using `vercel.json`; set a fresh `GEMINI_API_KEY` in project environment variables. The
   hosted build uses grounded Gemini plus retrieval fallback because local mT5/Ollama dependencies
   are intentionally excluded from the serverless function.
6. Verify `/`, `/api/chat`, `/api/screen`, crisis routing, English/RW retrieval, and mobile layout.
7. Confirm that the URL at the top of this README is publicly accessible without Vercel authentication.
8. Record the demo against that exact deployed revision.

Present the hosted Gemini/retrieval path and local fine-tuned-generator mode as intentionally
different environments.

## Five-minute demonstration plan

1. Problem, intended user, and strict emotional-well-being scope — 30 seconds
2. Dataset, split, seven algorithms, and selected metrics — 40 seconds
3. English and Kinyarwanda reformulated emotional messages — 60 seconds
4. Guided check-in with varied inputs — 35 seconds
5. Crisis, clinical/baby-care, and unrelated-topic routing — 45 seconds
6. Fine-tuned mT5, grounded Gemini RW, strict validation, and retrieval fallback — 35 seconds
7. Tests, benchmark, limitations, and recommendations — 55 seconds

Do not focus the video on authentication or visual styling; demonstrate algorithms, varied data,
failure handling, safety, and evidence.

## Repository map

```text
api/                         deployment Python endpoints
app/, components/, lib/      Next.js user interface
data/postpartum_depression/  licensed participant data and dictionary
data/intent/                 AMOD-derived weak labels and machine translations
data/translation/            schema and review gate for NLLB parallel fine-tuning data
data/external/               pinned ESConv provenance (corpus downloaded at runtime)
data/knowledge/              bilingual source-attributed grounding collection
models/                      fitted language and screening pipelines
models/umubyeyi-mt5-lora/    project-trained LoRA adapter and training manifest
notebooks/umubyeyi.ipynb     unified Colab ML, retrieval, fine-tuning, and evaluation workflow
ollama/Modelfile             local response-model instructions
reports/                     metrics, figures, and performance evidence
docs/REFERENCES.md           technical sources reserved for the final report bibliography
train_grounded_generator.py  reproducible ESConv/AMOD LoRA fine-tuning
evaluate_system_layers.py    layered metrics, auditable cases, and consolidated figures
src/generation_data.py       generator dataset construction and grouped splits
src/finetuned_generator.py   lazy inference and strict grounding validator
src/rag.py                   conversational pipeline and safety policy
src/screening.py             OOP check-in service
src/visualizations.py        OOP experiment visualizer
tests/                       automated unit and integration tests
local_api.py                 OOP local HTTP adapter
benchmark_system.py          reproducible runtime benchmark
```

## Limitations and responsible use

- The participant data is from Bangladesh, covers up to 24 months postpartum, and is not restricted
  to first-time mothers; it cannot validate performance for the intended Rwandan population.
- The system estimates screening risk, not diagnosis.
- The 14-topic grounding collection is deliberately focused and should be expanded with permitted,
  Rwanda-relevant evidence.
- Project-produced Kinyarwanda passages require native-speaker and maternal-health review.
- No reviewed Kinyarwanda gold evaluation set or formal Rwandan user study has been completed.
- ESConv and AMOD provide genuine English responses but are neither postpartum-specific nor Rwandan;
  their use teaches general response behaviour rather than clinical or local validity.
- The intent labels are keyword weak labels, and the cached Kinyarwanda questions are NLLB-200 machine
  translations. The untouched Kinyarwanda macro-F1 is 0.2762 and requires substantial improvement.
- No human-authored Kinyarwanda response corpus is used for generator fine-tuning. The current hybrid
  therefore uses grounded Gemini when configured and falls back to the source passage if the API or
  its output fails validation.
- Gemini is an externally hosted model, not a project-trained model. Sending a message to it requires
  clear user disclosure, data minimization, secure key handling, and documented API availability/cost.
- The optional Ollama model remains pretrained and instruction-configured, not fine-tuned.
- Deterministic safety rules may miss novel paraphrases and do not replace emergency assessment.

Future work should prioritize ethical Rwanda-specific data collection, professional and native-speaker
review, usability testing, model calibration, fairness analysis, multilingual semantic retrieval, and a
human-authored Kinyarwanda conversational responses for a stronger multilingual fine-tuning experiment.

## Safety notice

Umubyeyi provides general educational and emotional-support information only. It is not emergency or
medical care. Crisis wording, acute physical symptoms and possible postpartum psychosis bypass the
ordinary conversational path and direct the user to immediate human support.
