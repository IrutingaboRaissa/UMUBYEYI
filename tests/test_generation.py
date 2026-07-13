import json
from pathlib import Path

from finetuned_generator import (
    FineTunedGenerator, grounding_overlap, validate_grounded_generation,
)
from generation_data import build_generation_examples, dataset_summary


def test_generation_examples_are_bilingual_and_topic_grouped():
    examples = build_generation_examples(variants_per_language=2)
    summary = dataset_summary(examples)
    assert summary["languages"]["en"] == summary["languages"]["rw"]
    assert summary["topics"] == 14
    topic_splits = {}
    for example in examples:
        topic_splits.setdefault(example["topic_id"], set()).add(example["split"])
    assert all(len(splits) == 1 for splits in topic_splits.values())


def test_generator_targets_are_traceable_to_evidence():
    for example in build_generation_examples(variants_per_language=1):
        assert example["evidence"] in example["target"]
        assert example["source"]
        assert example["url"].startswith("https://")


def test_grounding_overlap_rejects_unrelated_generation():
    evidence = "Persistent sadness after childbirth deserves support from a health worker."
    assert grounding_overlap("Persistent sadness deserves support from a health worker.", evidence) > 0.5
    assert grounding_overlap("Football scores and airport hotels are interesting.", evidence) == 0.0


def test_strict_validator_removes_generated_continuation():
    evidence = "Persistent sadness deserves support. A trained health worker can help."
    raw = (
        "<extra_id_0>: Persistent sadness deserves support. "
        "A trained health worker can help. Football football invented continuation."
    )
    assert validate_grounded_generation(raw, evidence, "en") == (
        "I hear that this is difficult. Persistent sadness deserves support. "
        "A trained health worker can help."
    )


def test_strict_validator_rejects_partial_low_quality_output():
    evidence = "Persistent sadness deserves support. A trained health worker can help."
    assert validate_grounded_generation("sadness support worker maybe", evidence, "en") == ""


def test_missing_fine_tuned_adapter_fails_closed(tmp_path: Path):
    generator = FineTunedGenerator(tmp_path / "missing")
    assert generator.available is False
    assert generator.generate("I feel sad", "Seek support.", "en") == ""


def test_manifest_disables_language_that_failed_strict_evaluation(tmp_path: Path, monkeypatch):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "training_manifest.json").write_text(json.dumps({
        "base_model": "google/mt5-small",
        "accepted_generation_languages": ["en"],
    }), encoding="utf-8")
    generator = FineTunedGenerator(adapter)
    monkeypatch.setattr(generator, "_load", lambda: (_ for _ in ()).throw(AssertionError("must not load")))
    assert generator.generate("Mfite agahinda", "Vugana n'umukozi w'ubuzima.", "rw") == ""
