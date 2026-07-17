"""Lazy local inference for Umubyeyi's own fine-tuned emotional-support generator."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

try:  # package import in training scripts; top-level import in Vercel/local API
    from .generation_data import format_generator_input
except ImportError:  # pragma: no cover - exercised by the deployed top-level import
    from generation_data import format_generator_input

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTER = ROOT / "models" / "umubyeyi-bloomz-lora"


def _history_text(history, max_turns: int = 6) -> str:
    """Match the "Role: content" shape the generator was trained on (see
    build_esconv_examples in generation_data.py)."""
    if not history:
        return ""
    lines = []
    for item in history[-max_turns:]:
        role = "Supporter" if item.get("role") == "bot" else "User"
        content = (item.get("text") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return " ".join(lines)


class FineTunedGenerator:
    """Load the PEFT adapter only when a local generated answer is requested.

    Decoder-only causal LM (BLOOMZ-560m) fine-tuned on real ESConv supporter
    turns. Generates freely from its own weights -- the way a general-purpose
    fine-tuned LLM would -- rather than being constrained to reproduce a
    retrieved passage. Retrieval evidence is used only by the deterministic
    safety/scope layer upstream in rag.py, never fed into this model.
    """

    def __init__(self, adapter_path: Path | str | None = None):
        configured = adapter_path or os.environ.get("UMU_FINETUNED_MODEL") or DEFAULT_ADAPTER
        self.adapter_path = Path(configured)
        self._attempted = False
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._manifest = None

    def _read_manifest(self) -> dict:
        if self._manifest is None:
            try:
                self._manifest = json.loads(
                    (self.adapter_path / "training_manifest.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                self._manifest = {}
        return self._manifest

    @property
    def _remote_url(self) -> str:
        """URL of the Hugging Face Space hosting this same model, for the
        deployed (Vercel) build which cannot bundle PyTorch/Transformers
        within its 500MB serverless function limit. See hf_space/."""
        return os.environ.get("UMU_REMOTE_GENERATOR_URL", "").strip().rstrip("/")

    @property
    def available(self) -> bool:
        if os.environ.get("UMU_DISABLE_FINETUNED") == "1":
            return False
        if os.environ.get("VERCEL") == "1":
            return bool(self._remote_url)
        if not (self.adapter_path / "adapter_config.json").exists():
            return False
        if not (self.adapter_path / "training_manifest.json").exists():
            return False
        # Do not silently run a superseded adapter trained on templated prompts.
        return self._read_manifest().get("training_dataset_version") == "esconv-v1"

    def _load(self) -> bool:
        if self._attempted:
            return self._model is not None
        self._attempted = True
        if not self.available:
            return False
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            manifest = self._read_manifest()
            base = manifest["base_model"]
            tokenizer = AutoTokenizer.from_pretrained(self.adapter_path)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(base)
            model = PeftModel.from_pretrained(model, self.adapter_path)
            model.eval()
            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model
            return True
        except Exception:
            # PEFT/Transformers can raise version-, device-, or backend-specific
            # exceptions. Generation is optional, so always fail to the caller's
            # own fallback rather than crashing the request.
            self._model = None
            self._tokenizer = None
            return False

    def _generate_remote(self, query: str, lang: str, history=None) -> str:
        """Call the Hugging Face Space hosting this same model over HTTP.

        Gradio's API is a two-step async contract: POST submits the job and
        returns an event_id, then GET streams Server-Sent Events until a
        "complete" event carries the result. Any failure (space asleep,
        network error, timeout, malformed stream) returns "" so the caller
        falls through to its next fallback -- never a crash.
        """
        space_url = self._remote_url
        if not space_url:
            return ""
        timeout = float(os.environ.get("UMU_REMOTE_GENERATOR_TIMEOUT_SECONDS", "20"))
        try:
            payload = json.dumps({
                "data": [query, lang, json.dumps(history or [])]
            }).encode("utf-8")
            post_request = urllib.request.Request(
                f"{space_url}/call/generate", data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(post_request, timeout=timeout) as response:
                event_id = json.loads(response.read().decode("utf-8")).get("event_id")
            if not event_id:
                return ""

            get_request = urllib.request.Request(f"{space_url}/call/generate/{event_id}")
            with urllib.request.urlopen(get_request, timeout=timeout) as response:
                event_type = None
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_type = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        if event_type == "error":
                            return ""
                        if event_type == "complete":
                            data = json.loads(line[len("data:"):].strip())
                            return str(data[0]).strip() if data else ""
            return ""
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            return ""

    def generate(self, query: str, lang: str, history=None) -> str:
        # Capabilities are recorded from held-out evaluation. This checkpoint was
        # only fine-tuned and evaluated on English (see accepted_generation_languages
        # in training_manifest.json) -- avoid paying generation latency otherwise.
        manifest = self._read_manifest()
        accepted_languages = manifest.get("accepted_generation_languages", ["en"])
        if lang not in accepted_languages:
            return ""
        if os.environ.get("VERCEL") == "1":
            return self._generate_remote(query, lang, history)
        if not self._load():
            return ""
        prompt = format_generator_input(query, "", lang, _history_text(history)) + "\n"
        encoded = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=384)
        try:
            with self._torch.inference_mode():
                output = self._model.generate(
                    **encoded, max_new_tokens=120, do_sample=True, temperature=0.8, top_p=0.9,
                    no_repeat_ngram_size=3, pad_token_id=self._tokenizer.pad_token_id,
                )
            # A causal LM echoes the prompt back before continuing -- decode only the
            # new tokens (matches training-time generate_responses in the notebook).
            new_tokens = output[0][encoded["input_ids"].shape[1]:]
            answer = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        except Exception:
            return ""
        # The model was trained on single supporter turns; on rare degenerate
        # continuations it hallucinates a further "User:"/"Supporter:" line.
        answer = re.split(r"\n(?:User|Supporter):", answer)[0].strip()
        if len(answer.split()) < 4:
            return ""
        return answer
