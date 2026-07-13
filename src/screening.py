"""Object-oriented guided postpartum screening-risk service."""
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "ppd_checkin_risk.joblib"

FEATURES = [
    "Age", "Relationship with husband", "Relationship with the newborn",
    "Feeling about motherhood", "Recieved Support", "Need for Support", "Abuse",
    "Trust and share feelings", "Worry about newborn",
    "Relax/sleep when newborn is tended ", "Relax/sleep when the newborn is asleep",
    "Angry after latest child birth", "Feeling for regular activities",
    "Depression before pregnancy (PHQ2)", "Depression during pregnancy (PHQ2)",
]


class ScreeningService:
    """Validate check-in answers and run the saved non-diagnostic classifier.

    The fitted model is loaded lazily on the first prediction, which keeps imports
    lightweight and makes the service straightforward to test with a substitute model.
    Submitted answers are held only for the duration of ``predict`` and are not stored.
    """

    def __init__(self, model_path: Path = MODEL_PATH, model: Any = None,
                 features: list[str] | None = None):
        self.model_path = Path(model_path)
        self._model = model
        self.features = list(features or FEATURES)

    @property
    def model(self):
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Check-in model not found: {self.model_path}")
            self._model = joblib.load(self.model_path)
        return self._model

    def validate(self, answers: Mapping[str, Any]) -> dict[str, Any]:
        """Return a validated feature row or raise a user-facing ValueError."""
        missing = [name for name in self.features if name not in answers]
        if missing:
            raise ValueError(f"Missing {len(missing)} required check-in answers")

        row = {name: answers.get(name) for name in self.features}
        try:
            row["Age"] = int(row["Age"])
        except (TypeError, ValueError):
            raise ValueError("Age must be a whole number") from None
        if not 18 <= row["Age"] <= 60:
            raise ValueError("Age must be between 18 and 60")
        return row

    def predict(self, answers: Mapping[str, Any]) -> dict[str, Any]:
        """Return screening-risk support without retaining submitted answers."""
        row = self.validate(answers)
        frame = pd.DataFrame([row], columns=self.features)
        label = str(self.model.predict(frame)[0])
        return self._response(label)

    @staticmethod
    def _response(label: str) -> dict[str, Any]:
        elevated = label == "elevated"
        return {
            "risk": label,
            "elevated": elevated,
            "message_en": (
                "Your answers suggest elevated screening risk. Please arrange a conversation with a "
                "trained health worker; this result is not a diagnosis."
                if elevated else
                "Your answers were not classified as elevated screening risk. This is not a diagnosis; "
                "please still speak with a health worker if you are worried or your feelings persist."
            ),
            "message_rw": (
                "Ibisubizo byawe bigaragaza ibyago biri hejuru mu isuzuma. Nyamuneka vugana n’umukozi "
                "w’ubuzima wabihuguriwe; iki gisubizo si isuzuma ry’indwara."
                if elevated else
                "Ibisubizo byawe ntibyashyizwe mu byago biri hejuru. Iki si isuzuma ry’indwara; niba "
                "ugifite impungenge cyangwa ibyiyumvo bikomeza, vugana n’umukozi w’ubuzima."
            ),
            "disclaimer": "Research screening support only; not a diagnosis or medical advice.",
        }


screening_service = ScreeningService()


def predict_checkin(answers: dict) -> dict:
    """Backward-compatible functional entry point used by API handlers."""
    return screening_service.predict(answers)
