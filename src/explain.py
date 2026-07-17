"""Real SHAP explainability for the guided check-in classifier.

Wraps the deployed sklearn Pipeline (ColumnTransformer + whichever estimator won
training) as a black-box `predict_proba` callable, so this works regardless of
which of the seven candidate algorithms the training script picked — no
algorithm-specific explainer (e.g. TreeExplainer) coupling required.

SHAP's default tabular masker calls numeric operations (np.isclose) across the
whole feature row, which breaks on this pipeline's raw categorical strings
(e.g. "Bad"/"Good"). So categorical features are integer-encoded for SHAP's
masker using a fixed category domain (built from the full training dataset by
build_shap_background.py, not just the small sampled background) and decoded
back to real category strings inside the wrapped predict function before
calling the actual pipeline.

Gated off on Vercel by default (mirrors finetuned_generator.py's VERCEL gate and
rag.py's UMU_ENABLE_OLLAMA opt-in pattern): shap is a heavy optional dependency,
and any failure (missing package, background file absent, shape mismatch) must
degrade to "no explanation" rather than a 500.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKGROUND = ROOT / "models" / "ppd_checkin_shap_background.csv"
DEFAULT_CATEGORIES = ROOT / "models" / "ppd_checkin_shap_categories.json"
NUMERIC_FEATURES = {"Age"}

# Human-readable labels for the check-in's raw column names, shown in the UI.
FEATURE_LABELS = {
    "Age": "Age",
    "Relationship with husband": "Relationship with partner",
    "Relationship with the newborn": "Connection with your baby",
    "Feeling about motherhood": "How you feel about motherhood",
    "Recieved Support": "Support you currently receive",
    "Need for Support": "How much more support you need",
    "Abuse": "Experience of abuse",
    "Trust and share feelings": "Can share feelings with someone you trust",
    "Worry about newborn": "Constantly worried about your baby",
    "Relax/sleep when newborn is tended ": "Can rest when someone trusted watches the baby",
    "Relax/sleep when the newborn is asleep": "Can rest when the baby sleeps",
    "Angry after latest child birth": "Feeling angry or hard to calm",
    "Feeling for regular activities": "Comfort with ordinary daily activities",
    "Depression before pregnancy (PHQ2)": "Low mood before pregnancy (screening)",
    "Depression during pregnancy (PHQ2)": "Low mood during pregnancy (screening)",
}


class CheckinExplainer:
    """Lazily builds a model-agnostic SHAP explainer for the check-in pipeline."""

    def __init__(self, model_getter, background_path: Path = DEFAULT_BACKGROUND,
                 categories_path: Path = DEFAULT_CATEGORIES, features: list[str] | None = None):
        self._model_getter = model_getter
        self.background_path = Path(background_path)
        self.categories_path = Path(categories_path)
        self.features = list(features or FEATURE_LABELS.keys())
        self._attempted = False
        self._explainer = None
        self._categories: dict[str, list[str]] = {}

    @property
    def available(self) -> bool:
        if os.environ.get("VERCEL") == "1" and os.environ.get("UMU_ENABLE_SHAP") != "1":
            return False
        if os.environ.get("UMU_DISABLE_SHAP") == "1":
            return False
        return self.background_path.exists() and self.categories_path.exists()

    def _encode(self, df: pd.DataFrame) -> np.ndarray:
        """Turn a raw-value feature frame into the integer codes SHAP's masker needs."""
        columns = []
        for feature in self.features:
            if feature in NUMERIC_FEATURES:
                columns.append(df[feature].astype(float).to_numpy())
            else:
                domain = self._categories[feature]
                columns.append(df[feature].astype(str).map(
                    lambda v, d=domain: float(d.index(v)) if v in d else -1.0
                ).to_numpy())
        return np.column_stack(columns)

    def _decode(self, arr: np.ndarray) -> pd.DataFrame:
        """Turn SHAP's integer-coded rows back into the raw values the pipeline expects."""
        data = {}
        for i, feature in enumerate(self.features):
            column = arr[:, i]
            if feature in NUMERIC_FEATURES:
                data[feature] = column.astype(int)
            else:
                domain = self._categories[feature]
                data[feature] = [domain[int(round(code))] if 0 <= int(round(code)) < len(domain)
                                  else domain[0] for code in column]
        return pd.DataFrame(data, columns=self.features)

    def _load(self) -> bool:
        if self._attempted:
            return self._explainer is not None
        self._attempted = True
        if not self.available:
            return False
        try:
            import shap  # noqa: F401 (heavy optional import, kept lazy)

            self._categories = json.loads(self.categories_path.read_text(encoding="utf-8"))
            background = pd.read_csv(self.background_path)[self.features]
            model = self._model_getter()

            def wrapped_predict_proba(encoded: np.ndarray) -> np.ndarray:
                return model.predict_proba(self._decode(encoded))

            self._explainer = shap.Explainer(wrapped_predict_proba, self._encode(background))
        except Exception:
            self._explainer = None
        return self._explainer is not None

    def explain(self, row: pd.DataFrame, top_k: int = 5) -> list[dict[str, Any]] | None:
        if not self._load():
            return None
        try:
            model = self._model_getter()
            values = self._explainer(self._encode(row[self.features]))
            elevated_index = list(model.classes_).index("elevated")
            row_values = values.values[0]
            # Binary classifiers can return either one column (P(elevated) directly)
            # or one column per class; index into "elevated" only in the latter case.
            per_feature = row_values[:, elevated_index] if row_values.ndim > 1 else row_values
            contributions = sorted(
                zip(self.features, per_feature), key=lambda pair: abs(pair[1]), reverse=True
            )[:top_k]
            return [
                {
                    "feature": feature,
                    "feature_label": FEATURE_LABELS.get(feature, feature),
                    "contribution": round(float(contribution), 4),
                    "direction": "increases" if contribution > 0 else "decreases",
                }
                for feature, contribution in contributions
            ]
        except Exception:
            return None
