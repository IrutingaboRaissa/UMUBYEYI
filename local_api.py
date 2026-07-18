"""Local HTTP adapter for the Python endpoints used by ``npm run dev``."""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_local_env(path: Path, override: bool = False) -> None:
    """Load simple KEY=VALUE development secrets without another dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        # Empty placeholders must not mask a real value in another local env file.
        if key and value and (override or key not in os.environ):
            os.environ[key] = value


_load_local_env(ROOT / ".env")
_load_local_env(ROOT / ".env.local", override=True)
sys.path.insert(0, str(ROOT / "src"))

import db  # noqa: E402
import rag  # noqa: E402
from screening import screening_service  # noqa: E402


class LocalApiHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._json(204, {})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            if self.path == "/api/chat":
                self._chat(body)
            elif self.path == "/api/screen":
                self._json(200, screening_service.predict(body.get("answers") or {}, explain=body.get("explain", True)))
            elif self.path == "/api/event":
                self._event(body)
            elif self.path == "/api/feedback":
                self._feedback(body)
            elif self.path == "/api/title":
                self._title(body)
            else:
                self._json(404, {"error": "Endpoint not found"})
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _chat(self, body):
        message = (body.get("message") or "").strip()
        if not message:
            self._json(400, {"error": "message required"})
            return
        force = body.get("force_lang")
        force = force if force in ("en", "rw") else None
        started = time.time()
        result = rag.answer(message, force_lang=force, history=body.get("history"))
        result["latency_ms"] = int((time.time() - started) * 1000)
        self._json(200, result)

    def _event(self, body):
        sid = (body.get("session_id") or "").strip()
        if sid and db:
            sources = body.get("sources") or []
            similarity = sources[0].get("sim", 0.0) if sources else 0.0
            db.log_event(sid, body.get("language"), body.get("mode"),
                         body.get("grounded"), similarity,
                         int(body.get("latency_ms", 0)))
        self._json(200, {"ok": True})

    def _feedback(self, body):
        sid = (body.get("session_id") or "").strip()
        rating = int(body.get("rating", 0))
        if not sid or rating not in (1, -1):
            self._json(400, {"error": "session_id and rating (+1|-1) required"})
            return
        if db:
            db.log_feedback(sid, rating, body.get("language"), body.get("mode"))
        self._json(200, {"ok": True})

    def _title(self, body):
        user_message = (body.get("user_message") or "").strip()
        bot_reply = (body.get("bot_reply") or "").strip()
        lang = body.get("lang") if body.get("lang") in ("en", "rw") else "en"
        if not user_message:
            self._json(400, {"error": "user_message required"})
            return
        title = rag._default.groq_generator.generate_title(user_message, bot_reply, lang)
        self._json(200, {"title": title})

    def _json(self, status, payload):
        data = b"" if status == 204 else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class LocalApiServer:
    """Own the lifecycle and configuration of the local development API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000,
                 handler_class=LocalApiHandler):
        self._server = ThreadingHTTPServer((host, port), handler_class)
        self.host, self.port = self._server.server_address[:2]

    @property
    def address(self) -> str:
        return f"http://{self.host}:{self.port}"

    def run(self) -> None:
        print(f"Umubyeyi local API ready at {self.address}", flush=True)
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def serve_forever(self) -> None:
        """Serve requests; useful for controlled integration tests."""
        self._server.serve_forever()

    def shutdown(self) -> None:
        """Stop a server currently running in another thread."""
        self._server.shutdown()

    def close(self) -> None:
        self._server.server_close()


if __name__ == "__main__":
    LocalApiServer().run()
