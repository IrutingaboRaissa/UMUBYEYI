"""
Umubyeyi - FastAPI backend. Keeps the LLM key server-side and exposes one endpoint.

Run:  uvicorn src.api:app --reload --port 8000
Test: curl -X POST localhost:8000/chat -H "Content-Type: application/json" \
            -d '{"message":"Umwana wanjye ararira cyane nijoro, nakora iki?"}'
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import rag

app = FastAPI(title="Umubyeyi", description="Postpartum (0-6mo) maternal assistant for Rwandan first-time mothers")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatIn(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok", "grounding_entries": len(rag.BANK)}


@app.post("/chat")
def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if not msg:
        return {"answer": "", "language": "en", "danger": False, "sources": []}
    return rag.answer(msg)
