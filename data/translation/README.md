# NLLB Human-Reviewed Parallel Data

The unified notebook exports `nllb_human_review_cases.csv`. A fluent Kinyarwanda reviewer should:

1. compare `source_rw`, `nllb_english`, and `original_english`;
2. enter a faithful English translation in `target_en`;
3. score meaning preservation, English fluency, and Kinyarwanda source naturalness from 1 to 5;
4. set `approved` to `yes` only after checking or correcting the translation; and
5. add reviewer notes where meaning, emotional tone, or cultural wording is uncertain.

After review, save the file as `data/translation/nllb_human_reviewed_parallel.csv`. The notebook
requires at least 100 approved unique pairs before enabling NLLB LoRA fine-tuning. This reviewed file
must not be committed without the reviewers' permission. It contains project text, not participant
records, but reviewer attribution and consent should still be documented separately.

The original `data/intent/amod_kinyarwanda.csv` translations were produced by NLLB. They are useful
as weak supervision, but they are not independent fine-tuning targets or native-speaker ground truth.
