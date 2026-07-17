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


def grounded_payload(answer, support_ids=None, concerns=None, claims=None, unsupported=False):
    concerns = concerns or ["feeling alone"]
    return {
        "answer": answer,
        "identified_concerns": concerns,
        "covered_concerns": concerns,
        "grounded_claims": claims or ["Talking to someone you trust can help."],
        "support_ids": support_ids or ["E1"],
        "unsupported_claims": unsupported,
    }


def test_missing_key_skips_network():
    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    generator = GeminiGenerator(api_key="", opener=forbidden)
    assert generator.generate("I feel sad", "Talking to someone can help.", "en") == ""
    assert "missing key" in generator.last_error


def test_current_default_model_is_used():
    generator = GeminiGenerator(api_key="test-key", opener=lambda *args: None)
    assert generator.model == "gemini-3.1-flash-lite"


def test_grounded_structured_response_is_accepted():
    evidence = "Talking to someone you trust can help. A health worker can offer support."

    def open_ok(request, timeout):
        assert request.get_header("X-goog-api-key") == "test-key"
        sent = json.loads(request.data.decode("utf-8"))
        prompt = sent["contents"][0]["parts"][0]["text"]
        assert "E1:" in prompt and "E2:" in prompt
        return FakeResponse(api_payload(grounded_payload(
            "Feeling alone can be difficult. Talking to someone you trust can help. "
            "A health worker can offer support. What kind of support would feel easiest to ask for today?",
            support_ids=["E1", "E2"],
            claims=["Talking to someone you trust can help.", "A health worker can offer support."],
        )))

    generator = GeminiGenerator(api_key="test-key", opener=open_ok)
    answer = generator.generate("I feel alone", evidence, "en")
    assert "someone you trust" in answer


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


def test_response_with_invented_number_is_rejected():
    evidence = "Talking to a health worker can help."
    generator = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload(grounded_payload(
            "I hear that this is difficult. Talking to a health worker can help, so call 999 now. "
            "You deserve support with what you are experiencing. What support feels available today?",
            claims=["Talking to a health worker can help, so call 999 now."],
        ))),
    )
    assert generator.generate("I feel sad", evidence, "en") == ""


def test_invalid_support_id_and_api_failure_fail_closed():
    evidence = "Talking to someone can help."
    bad_id = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload(grounded_payload(
            "This sounds difficult and lonely. Talking to someone can help. You deserve to be heard "
            "without judgement. Who might feel safest to speak with about this today?",
            support_ids=["E9"], claims=["Talking to someone can help."],
        ))),
    )
    assert bad_id.generate("Help", evidence, "en") == ""

    def unavailable(*args, **kwargs):
        raise urllib.error.URLError("offline")

    offline = GeminiGenerator(api_key="test-key", opener=unavailable)
    assert offline.generate("Help", evidence, "en") == ""
    assert offline.last_error.startswith("network error")


def test_failed_coverage_is_retried_once_and_corrected():
    evidence = "Talking to someone you trust can help."
    attempts = []

    def opener(request, timeout):
        attempts.append(json.loads(request.data.decode("utf-8")))
        if len(attempts) == 1:
            invalid = grounded_payload(
                "I hear you. Talking to someone you trust can help. What feels hardest today?",
                concerns=["sadness", "feeling alone"],
                claims=["Talking to someone you trust can help."],
            )
            invalid["covered_concerns"] = ["sadness"]
            return FakeResponse(api_payload(invalid))
        return FakeResponse(api_payload(grounded_payload(
            "Feeling sad and alone sounds heavy. Talking to someone you trust can help. You deserve "
            "space to explain both feelings without judgement. Which part feels strongest right now?",
            concerns=["sadness", "feeling alone"],
            claims=["Talking to someone you trust can help."],
        )))

    generator = GeminiGenerator(api_key="test-key", opener=opener)
    answer = generator.generate("I feel sad and alone", evidence, "en")
    assert "sad and alone" in answer
    assert len(attempts) == 2


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
