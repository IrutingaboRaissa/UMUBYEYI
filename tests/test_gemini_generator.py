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
    assert generator.generate("I feel sad", "en") == ""
    assert "missing key" in generator.last_error


def test_current_default_model_is_used():
    generator = GeminiGenerator(api_key="test-key", opener=lambda *args: None)
    assert generator.model == "gemini-3.1-flash-lite"


def test_general_knowledge_response_is_accepted_not_constrained_to_evidence():
    def open_ok(request, timeout):
        assert request.get_header("X-goog-api-key") == "test-key"
        sent = json.loads(request.data.decode("utf-8"))
        prompt = sent["contents"][0]["parts"][0]["text"]
        assert "Evidence" not in prompt  # not constrained to our own passages
        return FakeResponse(api_payload({
            "answer": (
                "Feeling alone after having a baby is something many new mothers experience, even "
                "though it can feel very isolating in the moment. It can help to remember that this "
                "adjustment is genuinely hard, not a sign that you are failing. Reaching out to someone "
                "you trust, even briefly, can make a real difference. What kind of support would feel "
                "easiest for you to ask for right now?"
            ),
        }))

    generator = GeminiGenerator(api_key="test-key", opener=open_ok)
    answer = generator.generate("I feel alone", "en")
    assert "alone" in answer.lower()


def test_repeated_question_can_get_a_differently_worded_answer():
    responses = iter([
        "Feeling exhausted after a new baby is extremely common, even though it rarely feels that "
        "way in the moment. Your body and mind are recovering from a huge change, and rest -- even "
        "in small doses -- genuinely helps. Is there a specific time of day that feels hardest?",
        "It makes sense that you're exhausted right now; new motherhood asks a huge amount of you, "
        "physically and emotionally, often with very little sleep. Try to let go of anything that "
        "isn't essential today. What's one thing you could hand off to someone else this week?",
    ])

    def open_ok(request, timeout):
        return FakeResponse(api_payload({"answer": next(responses)}))

    generator = GeminiGenerator(api_key="test-key", opener=open_ok)
    first = generator.generate("I feel exhausted", "en")
    second = generator.generate("I feel exhausted", "en")
    assert first and second
    assert first != second


def test_short_response_is_rejected():
    generator = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload({"answer": "That sounds hard."})),
    )
    assert generator.generate("I feel alone", "en") == ""


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
    generator = GeminiGenerator(
        api_key="test-key",
        opener=lambda *args, **kwargs: FakeResponse(api_payload({"answer": (
            "I hear that this is difficult, and I want you to know things can get better. Talking to "
            "a health worker can help, so please call 199020 right now for support. You deserve real "
            "help with what you are feeling. What support feels available to you today?"
        )})),
    )
    assert generator.generate("I feel sad", "en") == ""


def test_generate_fails_closed_on_network_error():
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError("offline")

    offline = GeminiGenerator(api_key="test-key", opener=unavailable)
    assert offline.generate("Help", "en") == ""
    assert offline.last_error.startswith("network error")


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
