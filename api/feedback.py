"""POST /api/feedback — anonymous thumbs up/down."""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import db  # noqa: E402


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
            sid = (body.get("session_id") or "").strip()
            rating = int(body.get("rating", 0))
            if not sid or rating not in (1, -1):
                self._json(400, {"error": "session_id and rating (+1|-1) required"})
                return
            if db:
                db.log_feedback(sid, rating, body.get("language"), body.get("mode"))
            self._json(200, {"ok": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)
