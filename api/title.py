"""POST /api/title — summarize the opening exchange into a short chat title (Vercel serverless)."""
import json
import sys
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
            user_message = (body.get("user_message") or "").strip()
            bot_reply = (body.get("bot_reply") or "").strip()
            lang = body.get("lang") if body.get("lang") in ("en", "rw") else "en"
            if not user_message:
                self._json(400, {"error": "user_message required"})
                return
            title = rag._default.gemini_generator.generate_title(user_message, bot_reply, lang)
            self._json(200, {"title": title})
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
