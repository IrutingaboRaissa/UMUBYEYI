"""Train the reduced-input model used by Umubyeyi's optional guided check-in."""
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train_ppd_classifier import DATA, SEED, make_pipeline, metrics  # noqa: E402
from visualizations import create_experiment_figures, create_test_confusion_figure  # noqa: E402
FEATURES = [
    "Age",
    "Relationship with husband",
    "Relationship with the newborn",
    "Feeling about motherhood",
    "Recieved Support",
    "Need for Support",
    "Abuse",
    "Trust and share feelings",
    "Worry about newborn",
    "Relax/sleep when newborn is tended ",
    "Relax/sleep when the newborn is asleep",
    "Angry after latest child birth",
    "Feeling for regular activities",
    "Depression before pregnancy (PHQ2)",
    "Depression during pregnancy (PHQ2)",
]


def candidates():
    return {
        "dummy_baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED),
        "decision_tree": DecisionTreeClassifier(max_depth=7, min_samples_leaf=5,
                                                  class_weight="balanced", random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=500, min_samples_leaf=3,
                                                  class_weight="balanced_subsample", n_jobs=-1,
                                                  random_state=SEED),
        "extra_trees": ExtraTreesClassifier(n_estimators=500, min_samples_leaf=3,
                                              class_weight="balanced", n_jobs=-1, random_state=SEED),
        "support_vector_machine": SVC(C=1.0, kernel="rbf", class_weight="balanced", random_state=SEED),
        "k_nearest_neighbors": KNeighborsClassifier(n_neighbors=11, weights="distance"),
    }


def main():
    df = pd.read_csv(DATA)
    X = df[FEATURES].copy()
    y = df["EPDS Result"].astype(str).eq("High").map({True: "elevated", False: "not_elevated"})
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=.30, stratify=y, random_state=SEED)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=.50, stratify=y_temp, random_state=SEED)

    validation = {}
    model_defs = candidates()
    for name, estimator in model_defs.items():
        model = make_pipeline(estimator, FEATURES)
        started = time.perf_counter()
        model.fit(X_train, y_train)
        validation[name] = metrics(model, X_val, y_val)
        validation[name]["fit_seconds"] = round(time.perf_counter() - started, 4)
    winner = max(validation, key=lambda name: validation[name]["f1_score"])

    final = make_pipeline(model_defs[winner], FEATURES)
    final.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))
    test = metrics(final, X_test, y_test)

    joblib.dump(final, ROOT / "models" / "ppd_checkin_risk.joblib")
    report_dir = ROOT / "reports" / "ppd_checkin"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "task": "Optional guided check-in: elevated EPDS screening risk; not diagnosis",
        "dataset": "Mendeley Data 10.17632/4nznnrk8cg.3",
        "features": FEATURES,
        "split": {"train": len(X_train), "validation": len(X_val), "test": len(X_test), "seed": SEED},
        "validation": validation,
        "selected_model": winner,
        "test": test,
    }
    (report_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    create_experiment_figures(
        X, y, {key: report["split"][key] for key in ("train", "validation", "test")},
        validation, report_dir, "Guided check-in model")
    create_test_confusion_figure(test, report_dir, winner)
    print(json.dumps({"selected_model": winner, "test": test}, indent=2))


if __name__ == "__main__":
    main()
