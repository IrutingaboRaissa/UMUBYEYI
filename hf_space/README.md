---
title: Umubyeyi Generator API
emoji: 🌿
colorFrom: purple
colorTo: gray
sdk: gradio
sdk_version: 6.5.1
app_file: app.py
pinned: false
short_description: Inference API for Umubyeyi's fine-tuned BLOOMZ generator
---

# Umubyeyi — fine-tuned generator inference API

This Space hosts Umubyeyi's own fine-tuned emotional-support generator
(BLOOMZ-560m, LoRA on real ESConv data) so the deployed Vercel app can call
real generation instead of falling back to retrieval — Vercel's serverless
Python functions cannot bundle PyTorch/Transformers within their 500MB size
limit, but this Space (with a free ZeroGPU allocation) has no such
constraint.

This is not a chat UI for end users, though the page above lets you try it
directly. The programmatic contract is a named Gradio API endpoint:

```
POST {space_url}/call/generate  {"data": ["<message>", "en", "[]"]}
-> {"event_id": "..."}
GET  {space_url}/call/generate/{event_id}   (Gradio's async SSE result stream)
```

The model, LoRA adapter, and prompt format here are identical to
`src/finetuned_generator.py` in the main repository
(https://github.com/IrutingaboRaissa/UMUBYEYI) — this Space exists purely to
run the same weights on infrastructure without Vercel's size limit, not to
run a different model.

## Regenerating `merged_model/`

Not committed to git (1.1GB). `app.py` loads a plain merged checkpoint rather
than the LoRA adapter directly, because PEFT's own adapter-loading path
crashes under ZeroGPU's tensor-op patching (`RuntimeError: No CUDA GPUs are
available` inside `PeftModel.from_pretrained`, even at module level, before
any real GPU is attached). Merging offline sidesteps that entirely. Regenerate
from the repo root:

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

ADAPTER_PATH = "models/umubyeyi-bloomz-lora"
manifest = json.load(open(f"{ADAPTER_PATH}/training_manifest.json"))
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
base_model = AutoModelForCausalLM.from_pretrained(manifest["base_model"], dtype=torch.float16)
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH).merge_and_unload()

model.save_pretrained("hf_space/merged_model", safe_serialization=True)
tokenizer.save_pretrained("hf_space/merged_model")
```

**Known unresolved issue**: uploading this 1.1GB file to this Space fails
with `403 Forbidden: Repository storage limit reached (Max: 1 GB)` — the
account's Space storage cap is under the model's own size, so this Space is
not currently serving real generations. Needs either a paid tier with a
higher storage limit, or a smaller/quantized checkpoint.
