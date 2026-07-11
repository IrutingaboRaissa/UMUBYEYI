"""HTTP integration tests for the local development adapter."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from local_api import LocalApiServer
from test_screening import complete_answers


@pytest.fixture
def api_server():
    server = LocalApiServer(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.address
    finally:
        server.shutdown()
        server.close()
        thread.join(timeout=2)


def post(base_url, path, payload):
    request = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_chat_endpoint_returns_response_contract(api_server):
    status, result = post(api_server, "/api/chat", {"message": "hello", "force_lang": "en"})
    assert status == 200
    assert result["mode"] == "greeting"
    assert result["language"] == "en"
    assert "latency_ms" in result


def test_screen_endpoint_runs_saved_checkin_model(api_server):
    status, result = post(api_server, "/api/screen", {"answers": complete_answers()})
    assert status == 200
    assert result["risk"] in {"elevated", "not_elevated"}
    assert "not a diagnosis" in result["disclaimer"].lower()


def test_unknown_endpoint_returns_404(api_server):
    with pytest.raises(urllib.error.HTTPError) as error:
        post(api_server, "/api/unknown", {})
    assert error.value.code == 404


def test_chat_endpoint_rejects_empty_message(api_server):
    with pytest.raises(urllib.error.HTTPError) as error:
        post(api_server, "/api/chat", {"message": ""})
    assert error.value.code == 400
