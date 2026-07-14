import json
from pathlib import Path

from finetuned_generator import (
    FineTunedGenerator, grounding_overlap, validate_grounded_generation,
)
from generation_data import (
    build_amod_response_examples, build_esconv_examples, dataset_summary,
    format_generator_input,
)


def test_esconv_examples_keep_conversations_grouped_and_targets_original():
    conversations = [{
        "situation": "I feel overwhelmed.",
        "problem_type": "ongoing depression",
        "dialog": [
            {"speaker": "seeker", "annotation": {}, "content": "I feel exhausted."},
            {"speaker": "supporter", "annotation": {"strategy": "Reflection of feelings"},
             "content": "It sounds like this has taken a lot out of you."},
            {"speaker": "seeker", "annotation": {}, "content": "Yes, it has."},
            {"speaker": "supporter", "annotation": {"strategy": "Question"},
             "content": "What support would feel most useful today?"},
        ],
    }]
    examples = build_esconv_examples(conversations)
    summary = dataset_summary(examples)
    assert summary["datasets"] == {"ESConv": 2}
    assert {row["target"] for row in examples} == {
        "It sounds like this has taken a lot out of you.",
        "What support would feel most useful today?",
    }
    conversation_splits = {}
    for example in examples:
        conversation_splits.setdefault(example["group_id"], set()).add(example["split"])
    assert all(len(splits) == 1 for splits in conversation_splits.values())


def test_amod_responses_are_real_source_targets_and_question_grouped():
    source = [
        {"Context": "I feel sad", "Response": "Thank you for sharing that."},
        {"Context": "I feel sad", "Response": "It may help to speak with someone you trust."},
    ]
    intents = [{"Context": "I feel sad", "intent": "sadness_low_mood"}]
    examples = build_amod_response_examples(source, intents)
    assert len(examples) == 2
    assert len({row["group_id"] for row in examples}) == 1
    assert {row["target"] for row in examples} == {row["Response"] for row in source}


def test_runtime_prompt_contains_retrieved_evidence_without_a_fixed_answer():
    prompt = format_generator_input("I feel sad", "Persistent sadness deserves support.", "en")
    assert "Persistent sadness deserves support." in prompt
    assert "I feel sad" in prompt
    assert prompt.endswith("Response:")


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
