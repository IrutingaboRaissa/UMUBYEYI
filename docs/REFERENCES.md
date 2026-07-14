# Project References

This file records technical and dataset sources that must be cited in the final report. The final
bibliography should be updated only after the corresponding experiment has been run and its results
have been verified.

## NLLB

- Hugging Face. *NLLB — Transformers documentation*.
  https://huggingface.co/docs/transformers/en/model_doc/nllb
- Model used for the reproducible baseline: `facebook/nllb-200-distilled-600M`.
- Project role: Kinyarwanda (`kin_Latn`) ↔ English (`eng_Latn`) translation experiment. NLLB is a
  translation model, not the chatbot response generator.

The report must distinguish zero-shot NLLB translation from project fine-tuning. Fine-tuning should
only be claimed after training on an independently sourced or human-corrected parallel corpus and
evaluating on held-out human-authored translations. The existing `context_rw` column was generated
with NLLB and must not be presented as native-speaker ground truth.
