# Conversational dataset search record

Search reviewed: 13 July 2026.

## Required characteristics

A preferred generator-training dataset needed to be:

- real or transparently collected conversational question/answer data;
- specifically relevant to postpartum emotional wellbeing;
- available in Kinyarwanda, ideally paired with English;
- licensed for adaptation and redistribution in an academic project;
- sufficiently documented to assess consent, provenance, and response quality.

No reviewed candidate met all five criteria. This finding is limited to the documented search and must
not be stated as proof that no suitable dataset exists anywhere.

## Examined adjacent resources

| Resource | Useful property | Reason not used as Umubyeyi conversation supervision |
|---|---|---|
| [Mental Health Conversations](https://huggingface.co/datasets/ShivomH/Mental-Health-Conversations) | English multi-turn mental-health data; Apache-2.0 metadata | English rather than Kinyarwanda and not specifically postpartum; limited provenance description on the card |
| [Maternal Health Conversations](https://huggingface.co/datasets/tuc111/mhgen-maternal-health-convos) | Maternal/postpartum scenarios; MIT license | The card states that all 1,193 conversations are GPT-4o-generated and English, so it would not solve the real-data or Kinyarwanda limitation |
| [Kinyarwanda-English tourism translation data](https://huggingface.co/datasets/fair-forward/test) | Human-translated bilingual sentences with validation scores | Tourism/web text rather than postpartum emotional-support dialogue; some scenarios were GPT-generated |
| [Kinyarwanda speech 1000h](https://huggingface.co/datasets/badrex/kinyarwanda-speech-1000h) | Large CC-licensed Kinyarwanda speech/transcription collection | Intended for automatic speech recognition across broad domains, not paired emotional-support questions and answers |
| [Postpartum family-planning preliminary dataset](https://datadryad.org/dataset/doi:10.7272/Q6D21VR2) | Rwanda study involving local-language interviews | Family-planning research rather than a licensed chatbot-response corpus for postpartum emotional wellbeing |

## Project decision

Umubyeyi therefore uses synthetic **prompt augmentation**, not synthetic medical knowledge. Six question
forms per language are attached to each of 14 source-attributed knowledge passages. The supervised target
is a short acknowledgement plus that passage. Topic-level splitting prevents paraphrases of one passage
from appearing across training, validation, and test partitions.

This choice supports a reproducible fine-tuning experiment but does not establish real-world language,
empathy, safety, or clinical performance. Those claims require native-speaker review and ethically
approved evaluation with the intended population.
