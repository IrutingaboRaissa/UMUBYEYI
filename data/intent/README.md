# AMOD-derived bilingual intent data

`amod_kinyarwanda.csv` contains 724 rows of English mental-health questions, six
weak intent labels, and cached Kinyarwanda translations. After whitespace
normalisation, 596 distinct bilingual question pairs remain.

## Provenance

- Original question/response dataset: `Amod/mental_health_counseling_conversations`
  on Hugging Face.
- Pinned upstream revision: `d7e86f0813c5690181b41f97403c3674aa55dcef`.
- Upstream dataset size: 3,512 question/response rows and 995 unique English
  questions.
- Upstream license shown on the dataset card: OpenRAIL.
- The original data card says the questions and responses were collected from
  two online counselling and therapy platforms. It is English and is not a
  postpartum-specific or Rwandan dataset.

## Project transformations

1. Empty text was removed and repeated English questions were deduplicated.
2. Six intent labels were assigned with a project-authored English keyword
   lexicon. These are **weak labels**, not clinician or human annotations.
3. Out-of-scope keywords were filtered.
4. English questions were machine-translated with NLLB-200 and cached in
   `context_rw`. These are **machine translations**, not native-speaker data.

The file has 128 repeated question pairs after whitespace normalisation. Training
code removes these before splitting so equivalent English/Kinyarwanda text cannot
appear in both training and evaluation sets. Native-speaker review remains required.

Local file SHA-256:
`e2d4791cabefae22adef15dc5771329587f6a04bf835a6032e182003cd6d17a4`

Source: https://huggingface.co/datasets/Amod/mental_health_counseling_conversations
