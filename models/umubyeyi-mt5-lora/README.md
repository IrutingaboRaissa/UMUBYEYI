---
base_model: google/mt5-small
library_name: peft
language:
- en
- rw
license: apache-2.0
tags:
- peft
- lora
- text2text-generation
- postpartum
---

# Umubyeyi mT5 LoRA generator

This adapter is the project-fine-tuned generator for Umubyeyi, a research prototype for
English/Kinyarwanda postpartum emotional-well-being support. It generates from a retrieved,
source-attributed passage; it is not intended to answer from model memory.

## Training

- Base: `google/mt5-small` (300,520,832 total parameters)
- Method: supervised LoRA fine-tuning with PEFT
- Updated parameters: 344,064 (0.1145%)
- Data: 168 project-authored augmented examples grounded in 14 WHO-attributed knowledge topics
- Languages: 84 English and 84 Kinyarwanda examples
- Split: 120 train / 24 validation / 24 test
- Leakage control: complete topics, not individual paraphrases, are assigned to one split
- Seed: 42
- Training: 12 epochs on CPU, best checkpoint selected by validation loss

The 800-row tabular Bangladesh PPD dataset is not conversational data and was not used to
fine-tune this generator.

## Held-out results

The test set contains two complete topics never used for training or model selection.

| Metric | Base model | Fine-tuned adapter |
|---|---:|---:|
| ROUGE-L F1 | 0.0050 | 0.4862 |
| Mean evidence-word overlap | 0.0729 | 0.6687 |

Strict sentence-level grounding validation accepted 9/24 raw generations: 9/12 English and
0/12 Kinyarwanda. Accordingly, the application enables adapter generation for English only;
Kinyarwanda uses the retrieved source passage until a stronger reviewed model passes the same gate.
Raw held-out generations are retained in `reports/generator/test_generations.json`.

## Intended use

Load this adapter through `src/finetuned_generator.py`, supply the mother's message together with
retrieved evidence, then run the strict grounding validator. Deterministic crisis, clinical,
baby-care, and scope rules must execute before generation.

## Prohibited use and limitations

- Do not use for diagnosis, treatment, emergency assessment, or autonomous care decisions.
- Do not expose unvalidated raw generations directly to users.
- The 14-topic training source is small and augmented, not a clinical conversation study.
- Kinyarwanda passages and generated language require native-speaker and maternal-health review.
- No Rwanda-specific clinical validation or formal postpartum-mother field study has occurred.

See `training_manifest.json`, `train_grounded_generator.py`, and `reports/generator/` for complete
reproducibility evidence.
