from pathlib import Path

from topic_classifier import TopicClassifier


ROOT = Path(__file__).resolve().parents[1]


def test_trained_topic_classifier_is_available_and_ranked():
    classifier = TopicClassifier(ROOT / "models" / "topic_classifier.joblib")
    predictions = classifier.predict("I feel hopeless and have lost interest in everything", k=3)
    assert classifier.available
    assert len(predictions) == 3
    assert predictions[0]["score"] >= predictions[1]["score"] >= predictions[2]["score"]
    assert predictions[0]["topic_id"] == "persistent_sadness"


def test_missing_topic_model_fails_without_rule_based_guessing(tmp_path):
    classifier = TopicClassifier(tmp_path / "missing.joblib")
    assert classifier.available is False
    assert classifier.predict("I feel sad") == []
