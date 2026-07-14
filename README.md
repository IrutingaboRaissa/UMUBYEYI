# Umubyeyi

Umubyeyi is a bilingual English/Kinyarwanda postpartum emotional-well-being assistant for first-time
mothers. It combines trained screening-risk classifiers, source-grounded retrieval, deterministic
safety rules, a project-fine-tuned multilingual generator, a guided check-in, mood history, and
self-care support. It is a research prototype and does not diagnose or replace a health professional.

## Submission links

- **Deployed application:** https://firstmumassist-dwc0as2j0-raiss-irutingabos-projects.vercel.app/
- **Five-minute technical demo:** `ADD VIDEO URL BEFORE SUBMISSION`
- **Repository:** https://github.com/IrutingaboRaissa/UMUBYEYI

The video placeholder must be replaced after the final commit is deployed and recorded. Before sharing
the application with examiners, confirm that Vercel Deployment Protection does not redirect external
visitors to a Vercel sign-in page.

## Core functionality

- English and Kinyarwanda emotional-well-being conversations
- deterministic crisis, acute-health, baby-care, and unrelated-topic routing
- same-language character n-gram TF-IDF retrieval across 14 source-attributed topics
- project-trained bilingual topic classifier selecting the three strongest evidence topics
- locally fine-tuned mT5 LoRA generator constrained to retrieved evidence
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
trained topic classifier: category         trained Logistic Regression
       |                                        |
Top-3 knowledge-base matches               non-diagnostic result
       |
answer generation constrained by the selected evidence
       |
grounding/coverage validation -> response or evidence fallback
```

The 800 participant records train screening classifiers. They are never used as chatbot answers.

The project-trained models have distinct responsibilities. The screening classifier estimates the
guided check-in risk category. The bilingual topic classifier determines which of the 14 emotional
well-being categories best match a free-text message. Retrieval then finds the most relevant reviewed
passages already present in the knowledge base. Finally, a generator expresses that selected evidence
as a clear, supportive response; it does not independently choose medical facts. Safety-critical
crisis and referral decisions remain deterministic rather than being delegated to a text generator.

In the hosted application, Gemini performs the final natural-language realization because it produced
clearer and more empathetic bilingual wording in development. It is constrained by the topics and
evidence selected by the project pipeline, and its output must pass project-owned concern-coverage and
grounding checks. In the local research path, the project-fine-tuned mT5 model can perform this
generation step before the system falls back to a reviewed source passage.

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

The repository includes the compact Umubyeyi LoRA adapter. On first local generation,
Transformers downloads the Apache-2.0 `google/mt5-small` base checkpoint and applies the adapter.
Set `UMU_DISABLE_FINETUNED=1` only when intentionally testing retrieval fallback.

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

Current verified result: **66 tests passed**. Strategies include unit, parameterized, boundary-value,
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
| Bilingual topic classifier | 28 controlled paraphrases | Top-1 0.8571; Top-3 0.9643; macro-F1 0.8599* |
| English question-to-topic retrieval | 14 controlled paraphrases | Top-1 0.6429; Top-3 0.9286 |
| Kinyarwanda question-to-topic retrieval | 14 controlled project-authored cases | Top-1 1.0000* |
| Fine-tuned generator | 24 examples from two untouched topics | ROUGE-L 0.4862; overlap 0.6687 |
| Generator strict quality gate | same 24 examples | English 0.75; Kinyarwanda 0.00 |
| Safety/scope routing | 16 controlled cases across five categories | Accuracy 1.0000* |

`*` Controlled results are software/behavior evidence, not real-user or clinical validity. The
Kinyarwanda retrieval cases share domain vocabulary with the knowledge bank and require native review,
so their perfect score must not be presented as proof of generalization. English Top-1 performance also
shows that the lexical retriever can confuse indirect paraphrases even when the right topic is usually
within its Top-3 results.

### Project-trained topic classifier

```powershell
python train_topic_classifier.py
```

The persisted `models/topic_classifier.joblib` pipeline combines word and character TF-IDF with
balanced multinomial Logistic Regression. It trains on 168 labelled project-authored prompt examples
and 70 alternative representations already present in the reviewed knowledge bank (238 total; 14
topics). A stratified validation split selects the representation; the final model is evaluated on 28
separately phrased controlled cases. These are reproducible software-evaluation cases, not real-user
conversations or evidence of clinical validity. Runtime generation uses its Top-3 predictions so a
multi-concern message can bring several relevant passages into one answer.

Automatic text metrics cannot establish whether a response is empathetic, natural, or culturally
appropriate. `reports/system_evaluation/generator_human_review_template.csv` contains all 24 held-out
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

For faster GPU training, open `notebooks/umubyeyi_colab_finetuning.ipynb` in Google Colab, select a
T4 GPU, and upload the existing `data/knowledge/postpartum_wellbeing.json` when prompted. The notebook
contains dataset construction, topic-grouped splitting, LoRA training, held-out evaluation, manifest
creation, and adapter download. Extract its zip into `models/umubyeyi-mt5-lora/` to use it in the app.

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

- stratified split: 560 training / 120 validation / 120 untouched test
- seed: 42
- candidates: Dummy, Logistic Regression, Decision Tree, Random Forest, Extra Trees, SVM, and KNN
- selection: validation F1-score for the `elevated` class

| Experiment | Selected model | Accuracy | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| Full 46-predictor research model | Random Forest | 0.8083 | 0.7679 | 0.8113 | 0.7890 |
| Reduced 15-input check-in | Logistic Regression | 0.7667 | 0.7049 | 0.8113 | 0.7544 |

These are held-out experimental results, not clinical validation.

## Fine-tuned grounded generator

`google/mt5-small` was adapted with supervised LoRA fine-tuning for bilingual evidence-conditioned
postpartum support generation. This is genuine parameter training: 344,064 adapter parameters were
updated, rather than only changing a prompt or Modelfile.

- generator examples: 168 (84 English / 84 Kinyarwanda)
- split unit: complete knowledge topic, preventing paraphrases of one answer crossing splits
- train / validation / untouched test: 120 / 24 / 24 examples across 10 / 2 / 2 topics
- validation loss: 11.42 after epoch 1 to 1.034 after epoch 12
- held-out ROUGE-L F1: 0.0050 base to 0.4862 fine-tuned
- held-out mean evidence overlap: 0.0729 base to 0.6687 fine-tuned

Raw generation review is still mandatory. The strict validator accepted 9/24 held-out outputs; all
accepted outputs were English, while Kinyarwanda raw generation remained insufficiently fluent and
therefore routes to grounded Gemini when configured, then to the source passage on API/validation
failure. This is a documented limitation, not evidence of bilingual clinical readiness. Metrics and
raw generations are retained in `reports/generator/` for audit.

This deployment decision followed evaluation rather than replacing the fine-tuning experiment. LoRA
substantially improved factual overlap, but the held-out Kinyarwanda outputs did not pass the strict
quality gate and often communicated the evidence too mechanically for an emotionally supportive
conversation. Because the product goal is to help a mother feel heard as well as to transmit grounded
information, the hosted prototype uses Gemini to phrase the project-selected evidence in a more
natural and accessible way. Gemini is an external generator and was not trained by this project; the
project contribution is the trained classification, evidence selection, validation, fallback and
safety pipeline around it.

### Why synthetic augmentation was used

The 168 generator examples are not real mother-chatbot conversations. They are six project-authored
question templates per language applied to 14 source-attributed evidence topics; target facts remain
the corresponding evidence passage. This provides reproducible supervised fine-tuning without using
sensitive patient conversations, but it limits linguistic diversity and external validity.

A scoped dataset search found adjacent resources—English mental-health dialogue, English synthetic
maternal dialogue, Kinyarwanda speech, and tourism translation—but no resource identified that was
simultaneously real conversational data, Kinyarwanda, postpartum-emotional-wellbeing-specific,
appropriately licensed, and suitable for answer generation. This is recorded as “no suitable dataset
identified under the project criteria,” not “no such dataset exists.” See
`data/knowledge/DATASET_SEARCH_RECORD.md` for the inclusion criteria and examined alternatives.

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
data/knowledge/              bilingual source-attributed grounding collection
models/                      fitted language and screening pipelines
models/umubyeyi-mt5-lora/    project-trained LoRA adapter and training manifest
notebooks/umubyeyi.ipynb     complete executed ML/retrieval workflow
ollama/Modelfile             local response-model instructions
reports/                     metrics, figures, and performance evidence
train_grounded_generator.py  reproducible bilingual generator fine-tuning
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
- The mT5 LoRA adapter is fine-tuned by this project, but its 168 augmented examples originate from
  only 14 evidence topics and do not constitute clinical conversational validation.
- Raw Kinyarwanda generation did not pass the strict quality gate in held-out evaluation; the current
  hybrid therefore uses grounded Gemini when configured and falls back to the source passage if the
  API or its output fails validation.
- Gemini is an externally hosted model, not a project-trained model. Sending a message to it requires
  clear user disclosure, data minimization, secure key handling, and documented API availability/cost.
- The optional Ollama model remains pretrained and instruction-configured, not fine-tuned.
- Deterministic safety rules may miss novel paraphrases and do not replace emergency assessment.

Future work should prioritize ethical Rwanda-specific data collection, professional and native-speaker
review, usability testing, model calibration, fairness analysis, multilingual semantic retrieval, and a
larger reviewed bilingual conversational corpus for a stronger second fine-tuning experiment.

## Safety notice

Umubyeyi provides general educational and emotional-support information only. It is not emergency or
medical care. Crisis wording, acute physical symptoms and possible postpartum psychosis bypass the
ordinary conversational path and direct the user to immediate human support.
