"""Bounded CPU inference API for Umubyeyi's BLOOMZ LoRA model."""

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from peft import PeftModel
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent
BASE_MODEL = "bigscience/bloomz-560m"
generation_lock = Lock()
tokenizer = None
model = None

torch.set_num_threads(2)
torch.set_num_interop_threads(1)


def load_model() -> None:
    global tokenizer, model
    for required in ("adapter_config.json", "adapter_model.safetensors"):
        if not (ROOT / required).is_file():
            raise RuntimeError(f"Missing required adapter file: {required}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.float32, low_cpu_mem_usage=True
    )
    model = PeftModel.from_pretrained(base, str(ROOT), local_files_only=True)
    model.eval()


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model()
    yield


app = FastAPI(title="Umubyeyi Generator API", version="1.0.0", lifespan=lifespan)


class GenerateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    language: str = "en"
    history: list[dict] = Field(default_factory=list, max_length=6)


def normalise(value) -> str:
    return " ".join(str(value or "").split()).strip()


def history_text(items: list[dict]) -> str:
    lines = []
    for item in items[-6:]:
        role = "Supporter" if item.get("role") == "bot" else "User"
        content = normalise(item.get("text"))[:800]
        if content:
            lines.append(f"{role}: {content}")
    return " ".join(lines)


def make_prompt(message: str, history: list[dict]) -> str:
    parts = [
        "Write an empathetic emotional-support response.",
        "Do not diagnose or invent medical facts.",
        "Language: English",
        "Evidence: No external evidence supplied.",
    ]
    prior = history_text(history)
    if prior:
        parts.append(f"Conversation: {prior}")
    parts.extend([f"User: {normalise(message)}", "Response:"])
    return "\n".join(parts) + "\n"


def run_generation(request: GenerateRequest) -> str:
    if request.language != "en":
        return ""
    encoded = tokenizer(
        make_prompt(request.message, request.history),
        return_tensors="pt",
        truncation=True,
        max_length=384,
    )
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=64,
            do_sample=True,
            temperature=0.8,
            top_p=0.9,
            no_repeat_ngram_size=3,
            pad_token_id=tokenizer.pad_token_id,
        )
    new_tokens = output[0][encoded["input_ids"].shape[1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return re.split(r"\n(?:User|Supporter):", answer)[0].strip()


@app.get("/health")
def health():
    return {"ok": model is not None, "model": BASE_MODEL, "device": "cpu"}


@app.post("/generate")
def generate(request: GenerateRequest):
    if not generation_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Generator busy; retry later")
    try:
        return {"answer": run_generation(request)}
    finally:
        generation_lock.release()


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta charset='utf-8'><title>Umubyeyi Generator</title>
    <style>body{font-family:system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}textarea{width:100%;min-height:8rem}button{margin-top:1rem;padding:.7rem 1rem}pre{white-space:pre-wrap}</style></head>
    <body><h1>Umubyeyi fine-tuned generator</h1><p>CPU research fallback; English only; not medical advice.</p>
    <textarea id='m' placeholder='Enter an English message'></textarea><br><button onclick='go()'>Generate</button><pre id='o'></pre>
    <script>async function go(){const o=document.getElementById('o');o.textContent='Generating…';const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:document.getElementById('m').value,language:'en',history:[]})});const d=await r.json();o.textContent=d.answer||d.detail||'No response';}</script></body></html>"""
