"""Build leakage-controlled bilingual examples for grounded generator fine-tuning.

The 800-row PPD table is intentionally not used here: it has risk-factor columns,
not conversational answers.  Generator supervision is derived from the separate,
source-attributed postpartum knowledge collection.  Prompt variations are synthetic;
the answer content remains the corresponding evidence passage.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "data" / "knowledge" / "postpartum_wellbeing.json"

PROMPT_TEMPLATES = {
    "en": [
        "I need emotional support with {terms}.",
        "After giving birth, I have been struggling with {terms}.",
        "Can you help me understand {terms}?",
        "I am a new mother dealing with {terms}.",
        "What can I do when I experience {terms}?",
        "Please support me with {terms}.",
    ],
    "rw": [
        "Nkeneye ubufasha ku bijyanye na {terms}.",
        "Nyuma yo kubyara ndimo guhangana na {terms}.",
        "Wamfasha gusobanukirwa {terms}?",
        "Ndi umubyeyi mushya mpanganye na {terms}.",
        "Nakora iki iyo mfite {terms}?",
        "Mfasha ku bijyanye na {terms}.",
    ],
}

ACKNOWLEDGEMENTS = {
    "en": [
        "Thank you for sharing this.",
        "I hear that this is difficult.",
        "You are not alone in facing this.",
    ],
    "rw": [
        "Urakoze kubivuga.",
        "Ndumva ko ibi bikugoye.",
        "Nturi wenyine muri ibi.",
    ],
}


def format_generator_input(query: str, evidence: str, lang: str) -> str:
    """Return the exact evidence-conditioned format used in training and inference."""
    language = "Kinyarwanda" if lang == "rw" else "English"
    return (
        "Generate a brief, empathetic postpartum emotional-support answer. "
        "Use only the evidence and answer in the requested language. Do not diagnose.\n"
        f"Language: {language}\nEvidence: {evidence.strip()}\n"
        f"Mother: {query.strip()}\nAnswer:"
    )


def topic_splits(topic_ids: list[str], seed: int = 42) -> dict[str, str]:
    """Split by complete topic so held-out answers are not seen during training."""
    ids = sorted(set(topic_ids))
    random.Random(seed).shuffle(ids)
    n = len(ids)
    n_test = max(1, round(n * 0.15))
    n_validation = max(1, round(n * 0.15))
    result: dict[str, str] = {}
    for index, topic_id in enumerate(ids):
        if index < n_test:
            result[topic_id] = "test"
        elif index < n_test + n_validation:
            result[topic_id] = "validation"
        else:
            result[topic_id] = "train"
    return result


def build_generation_examples(
    bank_path: Path = DEFAULT_BANK, variants_per_language: int = 6, seed: int = 42
) -> list[dict]:
    """Create bilingual examples with provenance and topic-grouped splits."""
    bank = json.loads(Path(bank_path).read_text(encoding="utf-8"))
    if not 1 <= variants_per_language <= len(PROMPT_TEMPLATES["en"]):
        raise ValueError("variants_per_language must be between 1 and 6")
    required = {"id", "topic", "source", "url", "text_en", "text_rw", "queries_en", "queries_rw"}
    for row in bank:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"Knowledge row {row.get('id', '<unknown>')} missing: {sorted(missing)}")

    splits = topic_splits([row["id"] for row in bank], seed)
    examples: list[dict] = []
    for row in bank:
        for lang in ("en", "rw"):
            evidence = row[f"text_{lang}"].strip()
            terms = row[f"queries_{lang}"].strip()
            if not evidence or not terms:
                continue
            for variant, template in enumerate(PROMPT_TEMPLATES[lang][:variants_per_language]):
                query = template.format(terms=terms)
                acknowledgement = ACKNOWLEDGEMENTS[lang][variant % len(ACKNOWLEDGEMENTS[lang])]
                target = f"{acknowledgement} {evidence}"
                example_id = hashlib.sha256(
                    f"{row['id']}|{lang}|{variant}|{seed}".encode("utf-8")
                ).hexdigest()[:16]
                examples.append({
                    "id": example_id,
                    "topic_id": row["id"],
                    "topic": row["topic"],
                    "language": lang,
                    "split": splits[row["id"]],
                    "input": format_generator_input(query, evidence, lang),
                    "target": target,
                    "query": query,
                    "evidence": evidence,
                    "source": row["source"],
                    "url": row["url"],
                    "supervision": "project-authored prompt augmentation + source-grounded passage",
                    "review_status": row.get("review_status", "unspecified"),
                })
    return examples


def dataset_summary(examples: list[dict]) -> dict:
    summary = {"examples": len(examples), "topics": len({x["topic_id"] for x in examples})}
    summary["splits"] = {
        split: sum(x["split"] == split for x in examples)
        for split in ("train", "validation", "test")
    }
    summary["languages"] = {
        lang: sum(x["language"] == lang for x in examples) for lang in ("en", "rw")
    }
    summary["topics_by_split"] = {
        split: sorted({x["topic_id"] for x in examples if x["split"] == split})
        for split in ("train", "validation", "test")
    }
    return summary
