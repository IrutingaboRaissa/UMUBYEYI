"""Umubyeyi fine-tuned generator inference API (Hugging Face Space, Gradio + ZeroGPU).

Loads the real BLOOMZ-560m + LoRA adapter fine-tuned on ESConv (the same
weights committed at models/umubyeyi-bloomz-lora/ in the main repo, merged
into a single checkpoint offline -- see hf_space/README.md for why) and
exposes it as a named Gradio API endpoint. The deployed Vercel app cannot
bundle PyTorch/Transformers within its 500MB serverless function limit, so
it calls this Space instead of falling straight back to retrieval -- this is
the only difference from local inference; the model and prompt format are
identical to src/finetuned_generator.py.

Called over HTTP as: POST {space_url}/call/generate {"data": [query, lang, history_json]}
then GET {space_url}/call/generate/{event_id} (Gradio's async SSE result contract).
"""
import json
import re
from pathlib import Path

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    import spaces
except ImportError:  # running outside a real ZeroGPU Space (local test)
    class _NoOpSpaces:
        @staticmethod
        def GPU(fn):
            return fn
    spaces = _NoOpSpaces()

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "merged_model"
ACCEPTED_LANGUAGES = ["en"]

# Loaded (and moved to cuda) at module level, not inside the @spaces.GPU
# function: a CUDA emulation mode is active here even without a real GPU
# attached, and the ZeroGPU docs specifically recommend placement at
# startup over lazy/in-function loading. This is a plain merged checkpoint
# (LoRA folded in offline) rather than a PeftModel -- PEFT's own adapter
# loading path does not tolerate ZeroGPU's tensor-op patching well.
_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
if _tokenizer.pad_token is None:
    _tokenizer.pad_token = _tokenizer.eos_token
_model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, dtype=torch.float16)
_model.to("cuda")
_model.eval()


def _normalise(text) -> str:
    return " ".join(str(text or "").split()).strip()


def _format_generator_input(query: str, evidence: str, lang: str, history: str) -> str:
    """Mirrors src/generation_data.py's format_generator_input exactly --
    the model was trained on this exact prompt shape."""
    language = "Kinyarwanda" if lang == "rw" else "English"
    evidence_text = _normalise(evidence) or "No external evidence supplied."
    history_text = _normalise(history)
    parts = [
        "Write an empathetic emotional-support response.",
        "Do not diagnose or invent medical facts.",
        f"Language: {language}",
        f"Evidence: {evidence_text}",
    ]
    if history_text:
        parts.append(f"Conversation: {history_text}")
    parts.extend([f"User: {_normalise(query)}", "Response:"])
    return "\n".join(parts)


def _history_text(history_items, max_turns: int = 6) -> str:
    if not history_items:
        return ""
    lines = []
    for item in history_items[-max_turns:]:
        role = "Supporter" if item.get("role") == "bot" else "User"
        content = (item.get("text") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return " ".join(lines)


@spaces.GPU
def generate(query: str, lang: str = "en", history_json: str = "[]") -> str:
    if lang not in ACCEPTED_LANGUAGES:
        return ""
    try:
        history_items = json.loads(history_json) if history_json else []
    except (json.JSONDecodeError, TypeError):
        history_items = []

    prompt = _format_generator_input(query, "", lang, _history_text(history_items)) + "\n"
    encoded = _tokenizer(prompt, return_tensors="pt", truncation=True, max_length=384).to("cuda")
    try:
        with torch.inference_mode():
            output = _model.generate(
                **encoded, max_new_tokens=120, do_sample=True, temperature=0.8, top_p=0.9,
                no_repeat_ngram_size=3, pad_token_id=_tokenizer.pad_token_id,
            )
        new_tokens = output[0][encoded["input_ids"].shape[1]:]
        answer = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    except Exception:
        return ""

    # The model was trained on single supporter turns; on rare degenerate
    # continuations it hallucinates a further "User:"/"Supporter:" line.
    answer = re.split(r"\n(?:User|Supporter):", answer)[0].strip()
    if len(answer.split()) < 4:
        return ""
    return answer


with gr.Blocks(title="Umubyeyi -- fine-tuned generator") as demo:
    gr.Markdown(
        "# Umubyeyi -- fine-tuned generator inference API\n"
        "Not a chat UI for end users. Real-time inference for Umubyeyi's own "
        "fine-tuned BLOOMZ-560m generator (LoRA on real ESConv data, merged "
        "offline) -- called by the deployed app's backend, since Vercel's "
        "serverless functions cannot bundle PyTorch/Transformers within "
        "their 500MB limit. Main project: https://github.com/IrutingaboRaissa/UMUBYEYI"
    )
    query_in = gr.Textbox(label="Message")
    lang_in = gr.Textbox(label="Language (en only -- no Kinyarwanda training data yet)", value="en")
    history_in = gr.Textbox(label="Conversation history (JSON list, optional)", value="[]")
    answer_out = gr.Textbox(label="Answer")
    submit_btn = gr.Button("Generate")
    submit_btn.click(
        fn=generate, inputs=[query_in, lang_in, history_in], outputs=answer_out, api_name="generate"
    )

demo.queue()

if __name__ == "__main__":
    demo.launch()
