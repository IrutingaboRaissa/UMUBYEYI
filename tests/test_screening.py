import pytest

from screening import FEATURES, ScreeningService, predict_checkin


class FakeElevatedModel:
    def predict(self, frame):
        assert list(frame.columns) == FEATURES
        return ["elevated"]


def complete_answers():
    answers = {name: "No" for name in FEATURES}
    answers.update({
        "Age": 27,
        "Relationship with husband": "Good",
        "Relationship with the newborn": "Good",
        "Feeling about motherhood": "Positive",
        "Recieved Support": "High",
        "Need for Support": "Low",
        "Trust and share feelings": "Yes",
        "Relax/sleep when newborn is tended ": "Yes",
        "Relax/sleep when the newborn is asleep": "Yes",
        "Feeling for regular activities": "Nothing (no difficulty)",
        "Depression before pregnancy (PHQ2)": "Negative",
        "Depression during pregnancy (PHQ2)": "Negative",
    })
    return answers


def test_checkin_returns_non_diagnostic_contract():
    result = predict_checkin(complete_answers())
    assert result["risk"] in {"elevated", "not_elevated"}
    assert isinstance(result["elevated"], bool)
    assert "not a diagnosis" in result["disclaimer"].lower()


def test_checkin_requires_all_answers():
    with pytest.raises(ValueError, match="Missing"):
        predict_checkin({"Age": 25})


def test_screening_service_supports_model_injection():
    service = ScreeningService(model=FakeElevatedModel())
    result = service.predict(complete_answers())
    assert result["risk"] == "elevated"
    assert result["elevated"] is True


@pytest.mark.parametrize("age", [18, 60])
def test_checkin_accepts_boundary_ages(age):
    answers = complete_answers()
    answers["Age"] = age
    assert predict_checkin(answers)["risk"] in {"elevated", "not_elevated"}


@pytest.mark.parametrize("age", [17, 61])
def test_checkin_rejects_out_of_range_ages(age):
    answers = complete_answers()
    answers["Age"] = age
    with pytest.raises(ValueError, match="between 18 and 60"):
        predict_checkin(answers)


def test_checkin_rejects_non_numeric_age():
    answers = complete_answers()
    answers["Age"] = "unknown"
    with pytest.raises(ValueError, match="whole number"):
        predict_checkin(answers)
