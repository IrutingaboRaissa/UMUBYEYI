"""Lazy local inference for Umubyeyi's fine-tuned multilingual generator."""
from __future__ import annotations

import json
import importlib.util
import os
import re
from pathlib import Path

try:  # package import in training scripts; top-level import in Vercel/local API
    from .generation_data import format_generator_input
except ImportError:  # pragma: no cover - exercised by the deployed top-level import
    from generation_data import format_generator_input

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTER = ROOT / "models" / "umubyeyi-mt5-lora"


def grounding_overlap(answer: str, evidence: str) -> float:
    """Fraction of meaningful generated words supported by the supplied evidence."""
    words = re.findall(r"[^\W\d_]{3,}", answer.lower(), flags=re.UNICODE)
    evidence_words = set(re.findall(r"[^\W\d_]{3,}", evidence.lower(), flags=re.UNICODE))
    if not words:
        return 0.0
    return sum(word in evidence_words for word in words) / len(words)


def _normalise(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE))


def validate_grounded_generation(answer: str, evidence: str, lang: str) -> str:
    """Return a safe generated answer or empty text when generation is unreliable.

    The small model can continue beyond a good evidence reproduction or produce
    malformed low-resource-language text.  Only complete evidence sentences that
    the model actually generated are retained.  This is intentionally stricter
    than a bag-of-words overlap score.
    """
    cleaned = re.sub(r"<extra_id_\d+>\s*:??\s*", "", answer).strip()
    answer_normalised = _normalise(cleaned)
    evidence_sentences = [
        sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", evidence.strip())
        if sentence.strip()
    ]
    matched = [
        sentence for sentence in evidence_sentences
        if _normalise(sentence) and _normalise(sentence) in answer_normalised
    ]
    evidence_words = sum(len(_normalise(sentence).split()) for sentence in evidence_sentences)
    matched_words = sum(len(_normalise(sentence).split()) for sentence in matched)
    coverage = matched_words / evidence_words if evidence_words else 0.0
    if coverage < 0.65:
        return ""
    acknowledgement = "Ndumva ko ibi bikugoye." if lang == "rw" else "I hear that this is difficult."
    return f"{acknowledgement} {' '.join(matched)}"


class FineTunedGenerator:
    """Load the PEFT adapter only when a local generated answer is requested."""

    def __init__(self, adapter_path: Path | str | None = None):
        configured = adapter_path or os.environ.get("UMU_FINETUNED_MODEL") or DEFAULT_ADAPTER
        self.adapter_path = Path(configured)
        self._attempted = False
        self._model = None
        self._tokenizer = None
        self._manifest = None

    @property
    def available(self) -> bool:
        if os.environ.get("VERCEL") == "1" or os.environ.get("UMU_DISABLE_FINETUNED") == "1":
            return False
        manifest_path = self.adapter_path / "training_manifest.json"
        if not (self.adapter_path / "adapter_config.json").exists() or not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        # Do not silently run the superseded adapter trained on templated prompts.
        return manifest.get("training_dataset_version") == "esconv-amod-v1"

    def _load(self) -> bool:
        if self._attempted:
            return self._model is not None
        self._attempted = True
        if not self.available:
            return False
        try:
            import torch
            # A globally installed CPU-only bitsandbytes can make PEFT fail while
            # loading an ordinary (non-quantized) LoRA adapter. A clean project
            # environment does not install bitsandbytes. Skip this optional path
            # quickly here and allow the caller's grounded fallback.
            if not torch.cuda.is_available() and importlib.util.find_spec("bitsandbytes") is not None:
                return False
            from peft import PeftModel
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._manifest = json.loads(
                (self.adapter_path / "training_manifest.json").read_text(encoding="utf-8")
            )
            base = self._manifest["base_model"]
            tokenizer = AutoTokenizer.from_pretrained(self.adapter_path)
            model = AutoModelForSeq2SeqLM.from_pretrained(base)
            model = PeftModel.from_pretrained(model, self.adapter_path)
            model.eval()
            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model
            return True
        except Exception:
            # PEFT/Transformers can raise version-, device-, or backend-specific
            # exceptions. Generation is optional, so always fail to retrieval.
            self._model = None
            self._tokenizer = None
            return False

    def generate(self, query: str, evidence: str, lang: str) -> str:
        # Capabilities are recorded from held-out strict validation. Avoid paying
        # generation latency for a language whose raw outputs did not pass the gate.
        try:
            manifest = json.loads(
                (self.adapter_path / "training_manifest.json").read_text(encoding="utf-8")
            )
            accepted_languages = manifest.get("accepted_generation_languages", ["en", "rw"])
            if lang not in accepted_languages:
                return ""
        except (OSError, json.JSONDecodeError):
            return ""
        if not self._load():
            return ""
        prompt = format_generator_input(query, evidence, lang)
        encoded = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        try:
            with self._torch.inference_mode():
                output = self._model.generate(
                    **encoded, max_new_tokens=120, num_beams=2,
                    no_repeat_ngram_size=3, early_stopping=True,
                )
            answer = self._tokenizer.decode(output[0], skip_special_tokens=True).strip()
        except Exception:
            return ""
        # A fine-tuned model is still generative. Reject outputs that are not visibly
        # anchored in the retrieved passage and let the caller use direct retrieval.
        if len(answer.split()) < 6 or grounding_overlap(answer, evidence) < 0.25:
            return ""
        return validate_grounded_generation(answer, evidence, lang)
