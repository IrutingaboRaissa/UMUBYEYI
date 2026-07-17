import json
import urllib.error

from gemini_generator import GeminiGenerator


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def api_payload(answer):
    return {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps(answer)}]},
        }]
    }


def test_missing_key_skips_network():
    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    generator = GeminiGenerator(api_key="", opener=forbidden)
    assert generator.generate_social("hi", "en") == ""
    assert "missing key" in generator.last_error


def test_current_default_model_is_used():
    generator = GeminiGenerator(api_key="test-key", opener=lambda *args: None)
    assert generator.model == "gemini-3.1-flash-lite"


def test_social_greeting_is_model_generated_and_structured():
    def open_ok(request, timeout):
        sent = json.loads(request.data.decode("utf-8"))
        prompt = sent["contents"][0]["parts"][0]["text"]
        assert "Kinyarwanda" in prompt
        return FakeResponse(api_payload({
            "answer": "Mwiriwe neza, mama. Nishimiye kukumva; uyu munsi wiyumva ute?",
        }))

    generator = GeminiGenerator(api_key="test-key", opener=open_ok)
    answer = generator.generate_social("mwiriwe", "rw")
    assert answer.startswith("Mwiriwe")


def test_social_greeting_rejects_numbers_and_short_output():
    generator = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload({"answer": "Call 999 now"})),
    )
    assert generator.generate_social("hi", "en") == ""


def test_social_greeting_fails_closed_on_network_error():
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError("offline")

    generator = GeminiGenerator(api_key="test-key", opener=unavailable)
    assert generator.generate_social("hi", "en") == ""
    assert generator.last_error.startswith("network error")


def test_title_is_model_generated_and_bounded():
    def open_ok(request, timeout):
        sent = json.loads(request.data.decode("utf-8"))
        prompt = sent["contents"][0]["parts"][0]["text"]
        assert "maternal-wellbeing" not in prompt  # instruction lives in system_instruction, not here
        return FakeResponse(api_payload({"title": "Feeling exhausted after childbirth"}))

    generator = GeminiGenerator(api_key="test-key", opener=open_ok)
    title = generator.generate_title("I feel exhausted", "That sounds hard.", "en")
    assert title == "Feeling exhausted after childbirth"


def test_title_rejects_missing_or_overlong_output():
    generator = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload({"title": ""})),
    )
    assert generator.generate_title("hi", "hello", "en") == ""
