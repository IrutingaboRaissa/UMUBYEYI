"""Train postpartum screening-risk classifiers on the 800-participant PPD dataset.

The target is elevated EPDS screening risk (High versus Low/Medium). EPDS and PHQ item responses,
scores, and derived results are excluded from predictors to prevent target leakage.
The output is a research screening-risk model, not a diagnostic model.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from visualizations import create_experiment_figures, create_test_confusion_figure  # noqa: E402
DATA = ROOT / "data" / "postpartum_depression" / "PPD_dataset_v3.csv"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports" / "ppd_classifier"
SEED = 42


def load_xy():
    df = pd.read_csv(DATA)
    target = "EPDS Result"
    # Everything from the first PHQ-9 symptom item onward contains concurrent scale
    # responses or a score derived from them. Excluding the whole block prevents a
    # model from merely reconstructing the target questionnaire arithmetic.
    first_scale_item = "Little interest or pleasure in doing things"
    scale_start = df.columns.get_loc(first_scale_item)
    excluded = set(df.columns[scale_start:]) | {"sr", target}
    features = [c for c in df.columns if c not in excluded]
    y = df[target].astype(str).eq("High").map({True: "elevated", False: "not_elevated"})
    return df[features].copy(), y, features


def split_data(X, y):
    # 70/15/15, stratified. The test set remains untouched during model selection.
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=SEED)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=SEED)
    return X_train, X_val, X_test, y_train, y_val, y_test


def make_pipeline(model, feature_columns):
    numeric = [c for c in ["Age", "Number of the latest pregnancy"] if c in feature_columns]
    categorical = [c for c in feature_columns if c not in numeric]
    numeric_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2)),
    ])

    prep = ColumnTransformer([
        ("numeric", numeric_pipe, numeric),
        ("categorical", categorical_pipe, categorical),
    ])
    return Pipeline([("preprocess", prep), ("model", model)])


def metrics(model, X, y):
    pred = model.predict(X)
    labels = ["elevated", "not_elevated"]
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, pos_label="elevated", zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, pos_label="elevated", zero_division=0)), 4),
        "f1_score": round(float(f1_score(y, pred, pos_label="elevated", zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y, pred, labels=labels).tolist(),
        "labels": labels,
    }


def main():
    X, y, features = load_xy()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
    candidates = {
        "dummy_baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(
            max_iter=3000, class_weight="balanced", random_state=SEED),
        "decision_tree": DecisionTreeClassifier(
            max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=SEED),
        "random_forest": RandomForestClassifier(
            n_estimators=500, min_samples_leaf=3, class_weight="balanced_subsample",
            n_jobs=-1, random_state=SEED),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500, min_samples_leaf=3, class_weight="balanced",
            n_jobs=-1, random_state=SEED),
        "support_vector_machine": SVC(
            C=1.0, kernel="rbf", class_weight="balanced", random_state=SEED),
        "k_nearest_neighbors": KNeighborsClassifier(n_neighbors=11, weights="distance"),
    }
    fitted, validation = {}, {}
    for name, estimator in candidates.items():
        pipe = make_pipeline(estimator, features)
        started = time.perf_counter()
        pipe.fit(X_train, y_train)
        fitted[name] = pipe
        validation[name] = metrics(pipe, X_val, y_val)
        validation[name]["fit_seconds"] = round(time.perf_counter() - started, 4)

    winner = max(validation, key=lambda name: validation[name]["f1_score"])
    # Refit the selected configuration on train+validation, then evaluate once on test.
    X_fit = pd.concat([X_train, X_val])
    y_fit = pd.concat([y_train, y_val])
    final_model = make_pipeline(candidates[winner], features)
    final_model.fit(X_fit, y_fit)
    test = metrics(final_model, X_test, y_test)

    MODELS.mkdir(exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODELS / "ppd_screening_risk.joblib")
    report = {
        "dataset": "Mendeley Data 10.17632/4nznnrk8cg.3",
        "task": "Elevated EPDS screening risk (High vs Low/Medium); not diagnosis",
        "rows": len(X),
        "features": features,
        "excluded_for_leakage": "All concurrent EPDS/PHQ items, scores and derived results",
        "split": {"train": len(X_train), "validation": len(X_val), "test": len(X_test), "seed": SEED},
        "class_counts": y.value_counts().to_dict(),
        "validation": validation,
        "selected_model": winner,
        "test": test,
    }
    (REPORTS / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    create_experiment_figures(
        X, y, {key: report["split"][key] for key in ("train", "validation", "test")},
        validation, REPORTS, "Full screening model")
    create_test_confusion_figure(test, REPORTS, winner)
    print(json.dumps({"selected_model": winner, "validation": validation[winner], "test": test}, indent=2))


if __name__ == "__main__":
    main()
