import json
import urllib.error
from pathlib import Path

from finetuned_generator import FineTunedGenerator
from generation_data import (
    build_esconv_examples, dataset_summary, format_generator_input,
)


class _FakeHttpResponse:
    """Minimal context-manager stand-in for urllib.request.urlopen's return value."""

    def __init__(self, body: bytes = b"", lines: list[bytes] | None = None):
        self._body = body
        self._lines = lines or []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body

    def __iter__(self):
        return iter(self._lines)


def _remote_generator(tmp_path: Path, monkeypatch, space_url: str = "https://example.hf.space"):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("UMU_REMOTE_GENERATOR_URL", space_url)
    return FineTunedGenerator(tmp_path / "unused")


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


def test_runtime_prompt_contains_retrieved_evidence_without_a_fixed_answer():
    prompt = format_generator_input("I feel sad", "Persistent sadness deserves support.", "en")
    assert "Persistent sadness deserves support." in prompt
    assert "I feel sad" in prompt
    assert prompt.endswith("Response:")


def test_missing_fine_tuned_adapter_fails_closed(tmp_path: Path):
    generator = FineTunedGenerator(tmp_path / "missing")
    assert generator.available is False
    assert generator.generate("I feel sad", "en") == ""


def test_manifest_disables_language_that_failed_strict_evaluation(tmp_path: Path, monkeypatch):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "training_manifest.json").write_text(json.dumps({
        "base_model": "bigscience/bloomz-560m",
        "training_dataset_version": "esconv-v1",
        "accepted_generation_languages": ["en"],
    }), encoding="utf-8")
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    generator = FineTunedGenerator(adapter)
    monkeypatch.setattr(generator, "_load", lambda: (_ for _ in ()).throw(AssertionError("must not load")))
    assert generator.generate("Mfite agahinda", "rw") == ""


def test_vercel_deployment_calls_the_remote_space_instead_of_loading_locally(tmp_path, monkeypatch):
    import urllib.request

    generator = _remote_generator(tmp_path, monkeypatch)
    monkeypatch.setattr(generator, "_load", lambda: (_ for _ in ()).throw(AssertionError("must not load locally")))

    def fake_urlopen(request, timeout=None):
        assert request.full_url.endswith("/generate")
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["message"] == "I feel exhausted"
        return _FakeHttpResponse(body=json.dumps({
            "answer": "What made you feel that way today?"
        }).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert generator.generate("I feel exhausted", "en") == "What made you feel that way today?"


def test_remote_space_empty_answer_fails_closed(tmp_path, monkeypatch):
    import urllib.request

    generator = _remote_generator(tmp_path, monkeypatch)

    def fake_urlopen(request, timeout=None):
        return _FakeHttpResponse(body=json.dumps({"answer": ""}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert generator.generate("I feel exhausted", "en") == ""


def test_remote_space_network_failure_fails_closed_not_crash(tmp_path, monkeypatch):
    import urllib.request

    generator = _remote_generator(tmp_path, monkeypatch)

    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("space asleep or unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert generator.generate("I feel exhausted", "en") == ""


def test_remote_generator_not_called_when_url_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("UMU_REMOTE_GENERATOR_URL", raising=False)
    generator = FineTunedGenerator(tmp_path / "unused")

    import urllib.request
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call network")),
    )
    assert generator.generate("I feel exhausted", "en") == ""
