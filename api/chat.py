"""POST /api/chat — run the Umubyeyi RAG pipeline (Vercel serverless)."""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import rag  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8"))
            message = (body.get("message") or "").strip()
            if not message:
                self._json(400, {"error": "message required"})
                return
            force = body.get("force_lang")
            force = force if force in ("en", "rw") else None
            t0 = time.time()
            result = rag.answer(message, force_lang=force, history=body.get("history"))
            result["latency_ms"] = int((time.time() - t0) * 1000)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
