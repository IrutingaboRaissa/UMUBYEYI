import sys

import pandas as pd
import pytest

from explain import CheckinExplainer, DEFAULT_BACKGROUND, DEFAULT_CATEGORIES
from screening import FEATURES, screening_service


def complete_frame(**overrides):
    row = {name: "No" for name in FEATURES}
    row.update({
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
    row.update(overrides)
    return pd.DataFrame([row], columns=FEATURES)


def test_background_and_categories_artifacts_exist():
    assert DEFAULT_BACKGROUND.exists()
    assert DEFAULT_CATEGORIES.exists()


def test_explain_returns_ranked_signed_contributions():
    result = screening_service.explainer.explain(complete_frame())
    assert result is not None
    assert 1 <= len(result) <= 5
    for row in result:
        assert set(row.keys()) == {"feature", "feature_label", "contribution", "direction"}
        assert row["feature"] in FEATURES
        assert row["direction"] in {"increases", "decreases"}
        assert isinstance(row["contribution"], float)
    # Sorted by absolute magnitude, largest first.
    magnitudes = [abs(row["contribution"]) for row in result]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_risky_answers_show_a_risk_increasing_contribution():
    risky = complete_frame(**{
        "Relationship with husband": "Bad",
        "Angry after latest child birth": "Yes",
        "Abuse": "Yes",
    })
    result = screening_service.explainer.explain(risky)
    assert result is not None
    assert any(row["direction"] == "increases" for row in result)


def test_explain_degrades_to_none_when_shap_import_fails(monkeypatch):
    explainer = CheckinExplainer(model_getter=lambda: screening_service.model)
    monkeypatch.setitem(sys.modules, "shap", None)  # import shap -> ModuleNotFoundError-like
    assert explainer.explain(complete_frame()) is None


def test_explainer_unavailable_without_background_files():
    explainer = CheckinExplainer(
        model_getter=lambda: screening_service.model,
        background_path=screening_service.explainer.background_path.parent / "does-not-exist.csv",
        categories_path=screening_service.explainer.categories_path,
    )
    assert explainer.available is False
    assert explainer.explain(complete_frame()) is None


def test_vercel_gates_shap_off_by_default(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("UMU_ENABLE_SHAP", raising=False)
    explainer = CheckinExplainer(model_getter=lambda: screening_service.model)
    assert explainer.available is False


def test_vercel_opt_in_flag_re_enables_shap(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("UMU_ENABLE_SHAP", "1")
    explainer = CheckinExplainer(model_getter=lambda: screening_service.model)
    assert explainer.available is True
