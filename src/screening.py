"""Object-oriented guided postpartum screening-risk service."""
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

try:  # package import in training scripts; top-level import in Vercel/local API
    from .explain import CheckinExplainer
except ImportError:  # pragma: no cover - exercised by the deployed top-level import
    from explain import CheckinExplainer

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
        self.explainer = CheckinExplainer(model_getter=lambda: self.model, features=self.features)

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

    def predict(self, answers: Mapping[str, Any], explain: bool = True) -> dict[str, Any]:
        """Return screening-risk support without retaining submitted answers."""
        row = self.validate(answers)
        frame = pd.DataFrame([row], columns=self.features)
        label = str(self.model.predict(frame)[0])
        explanation = self.explainer.explain(frame) if explain else None
        return self._response(label, explanation)

    @staticmethod
    def _response(label: str, explanation: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        elevated = label == "elevated"
        return {
            "risk": label,
            "elevated": elevated,
            "message_en": (
                "Thank you for answering honestly — that takes courage. Based on what you shared, it looks "
                "like you could be carrying more than feels comfortable right now, and that's completely "
                "understandable given everything a new mother handles. This isn't a diagnosis, just a signal "
                "worth listening to. Tools like this one can point in the right direction, but only a real "
                "conversation with a health worker can tell you what's actually going on and get you the "
                "right support — please try to reach out soon."
                if elevated else
                "Thank you for checking in. Based on what you shared today, nothing here stood out as a "
                "strong concern — that's good to hear. Feelings can still shift day to day, so keep "
                "checking in with yourself when it helps. This isn't a medical exam, so if you're ever "
                "worried or these feelings stick around, please still talk to a health worker to be sure."
            ),
            "message_rw": (
                "Urakoze kubwira ukuri — ibyo birasaba ubutwari. Ibisubizo byawe byerekana ko wenda "
                "witwaje ibiruta ibyo wagombye, kandi ibyo ni ibisanzwe kubera byinshi umubyeyi mushya "
                "anyuramo. Iki si isuzuma ry'indwara, ni ikimenyetso gikwiye kwitabwaho gusa. Ibikoresho "
                "nk'iki birashobora kukuyobora, ariko ni ukuganira n'umukozi w'ubuzima wabihuguriwe honyine "
                "byakwereka neza ikibazo n'ubufasha bukwiye — nyamuneka gerageza kubigenza vuba."
                if elevated else
                "Urakoze gukora iki gisuzuma. Ibisubizo byawe uyu munsi ntibyerekanye ikibazo gikomeye — "
                "ibyo ni byiza. Ariko uko wiyumva birashobora guhinduka uko iminsi igenda, bityo komeza "
                "wisuzumishe iyo bikwiye. Iki si isuzuma ry'ubuvuzi, bityo niba ufite impungenge cyangwa "
                "ibyiyumvo bikomeza, nyamuneka vugana n'umukozi w'ubuzima kugira ngo umenye neza."
            ),
            "disclaimer": "Research screening support only; not a diagnosis or medical advice.",
            "explainability_available": explanation is not None,
            "explanation": explanation,
        }


screening_service = ScreeningService()


def predict_checkin(answers: dict, explain: bool = True) -> dict:
    """Backward-compatible functional entry point used by API handlers."""
    return screening_service.predict(answers, explain=explain)
