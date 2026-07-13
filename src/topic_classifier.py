"""Runtime wrapper for the project-trained bilingual wellbeing topic classifier."""
from __future__ import annotations

from pathlib import Path

import joblib


class TopicClassifier:
    """Load the supervised classifier and return ranked topic probabilities."""

    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self.pipeline = joblib.load(self.model_path) if self.model_path.exists() else None

    @property
    def available(self) -> bool:
        return self.pipeline is not None

    def predict(self, text: str, k: int = 3) -> list[dict]:
        if not self.available or not text.strip() or k < 1:
            return []
        probabilities = self.pipeline.predict_proba([text])[0]
        classifier = self.pipeline.named_steps["classifier"]
        ranked = probabilities.argsort()[::-1][:k]
        return [
            {"topic_id": str(classifier.classes_[index]), "score": float(probabilities[index])}
            for index in ranked
        ]
