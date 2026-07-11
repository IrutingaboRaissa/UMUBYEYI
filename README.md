# Umubyeyi

Umubyeyi is a bilingual English/Kinyarwanda postpartum emotional-well-being assistant for first-time
mothers. It combines trained screening-risk classifiers, source-grounded retrieval, deterministic
safety rules, an optional locally running Ollama model, a guided check-in, mood history, and self-care
support. It is a research prototype and does not diagnose or replace a health professional.

## Submission links

- **Deployed application:** `ADD VERIFIED DEPLOYMENT URL BEFORE SUBMISSION`
- **Five-minute technical demo:** `ADD VIDEO URL BEFORE SUBMISSION`
- **Repository:** https://github.com/IrutingaboRaissa/UMUBYEYI

The first two placeholders must be replaced only after the final commit is deployed and recorded.

## Core functionality

- English and Kinyarwanda emotional-well-being conversations
- deterministic crisis, acute-health, baby-care, and unrelated-topic routing
- same-language character n-gram TF-IDF retrieval across 14 source-attributed topics
- optional local Ollama response phrasing constrained to retrieved evidence
- direct retrieved-passage fallback when Ollama is unavailable
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
English/RW TF-IDF retrieval               trained Logistic Regression
       |                                        |
confidence gate                           non-diagnostic result
       |
local Ollama phrasing OR retrieval fallback
       |
sources + general-information disclaimer
```

The 800 participant records train screening classifiers. They are never used as chatbot answers.

## Prerequisites

- Windows 10/11, macOS, or Linux
- Python 3.11–3.13
- Node.js 20 or newer and npm
- Git
- Ollama, only when local generated phrasing is required

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
Copy-Item .env.example .env
```

Analytics are optional. The application uses a local SQLite file when no `DATABASE_URL` is provided.
Do not commit `.env`.

### 5. Optional: install the local response model

```powershell
ollama pull gemma3:4b
ollama create umubyeyi -f ollama/Modelfile
$env:OLLAMA_MODEL = "umubyeyi"
```

`ollama create` applies project instructions; it does not fine-tune model weights. Without Ollama,
the application safely returns the retrieved evidence passage.

### 6. Start the complete local application

```powershell
$env:OLLAMA_MODEL = "umubyeyi"   # omit when testing fallback mode
npm run dev
```

`npm run dev` starts both the Next.js interface and local Python API adapter. Open the URL printed by
Next.js, normally http://localhost:3000. If port 3000 is occupied, it selects another port.

## Verification

### Automated tests

```powershell
python -m pytest -q
```

Current verified result: **32 tests passed**. Strategies include unit, parameterized, boundary-value,
invalid-input, offline/fallback, bilingual retrieval, safety, response-contract, dependency-injection,
and HTTP integration testing.

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
```

These commands regenerate saved pipelines, metrics, training timings, model comparisons, and confusion
matrices. The complete executed workflow is also available in `notebooks/umubyeyi.ipynb`.

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

These are steady-state local measurements and exclude browser/network latency and Ollama generation.

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

## Deployment plan

1. Run tests and the production build locally.
2. Commit and push the exact tested revision.
3. Import the GitHub repository into Vercel.
4. Configure optional `DATABASE_URL` in project environment variables.
5. Deploy using `vercel.json`; Vercel runs retrieval fallback because it cannot reach the local Ollama
   process on the developer's computer.
6. Verify `/`, `/api/chat`, `/api/screen`, crisis routing, English/RW retrieval, and mobile layout.
7. Add the verified URL at the top of this README.
8. Record the demo against that exact deployed revision.

For an installable local demonstration with Ollama, use the fresh-clone instructions above. The hosted
fallback and local Ollama modes should be presented as two intentionally different environments.

## Five-minute demonstration plan

1. Problem, intended user, and strict emotional-well-being scope — 30 seconds
2. Dataset, split, seven algorithms, and selected metrics — 40 seconds
3. English and Kinyarwanda reformulated emotional messages — 60 seconds
4. Guided check-in with varied inputs — 35 seconds
5. Crisis, clinical/baby-care, and unrelated-topic routing — 45 seconds
6. Ollama-enabled response and retrieval fallback — 35 seconds
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
notebooks/umubyeyi.ipynb     complete executed ML/retrieval workflow
ollama/Modelfile             local response-model instructions
reports/                     metrics, figures, and performance evidence
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
- The local Ollama model is pretrained and instruction-configured, not fine-tuned by this project.
- Deterministic safety rules may miss novel paraphrases and do not replace emergency assessment.

Future work should prioritize ethical Rwanda-specific data collection, professional and native-speaker
review, usability testing, model calibration, fairness analysis, multilingual semantic retrieval, and a
reviewed bilingual conversational corpus before language-model fine-tuning.

## Safety notice

Umubyeyi provides general educational and emotional-support information only. It is not emergency or
medical care. Crisis wording, acute physical symptoms and possible postpartum psychosis bypass the
ordinary conversational path and direct the user to immediate human support.
