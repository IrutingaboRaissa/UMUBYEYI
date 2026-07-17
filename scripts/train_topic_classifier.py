"""Train Umubyeyi's bilingual six-intent classifier on the AMOD-derived data.

The labels are project-authored keyword weak labels and the Kinyarwanda column is
an NLLB-200 machine translation. Metrics therefore measure reproduction of those
labels, not clinical validity or native-language correctness.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "intent" / "amod_kinyarwanda.csv"
MODEL_PATH = ROOT / "models" / "topic_classifier.joblib"
REPORT_DIR = ROOT / "reports" / "topic_classifier"
SEED = 42


def feature_pipeline() -> FeatureUnion:
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
    char = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2
    )
    return FeatureUnion([("word", word), ("char", char)])


def make_pipeline(estimator) -> Pipeline:
    return Pipeline([
        ("features", feature_pipeline()),
        ("classifier", estimator),
    ])


def score(model: Pipeline, texts: list[str], labels: list[str]) -> dict:
    predicted = model.predict(texts)
    probabilities = model.predict_proba(texts)
    classes = model.named_steps["classifier"].classes_
    top_three = np.argsort(probabilities, axis=1)[:, -3:]
    return {
        "cases": len(labels),
        "accuracy": round(float(accuracy_score(labels, predicted)), 4),
        "macro_f1": round(float(f1_score(labels, predicted, average="macro")), 4),
        "top_3_accuracy": round(float(np.mean([
            label in classes[indexes] for label, indexes in zip(labels, top_three)
        ])), 4),
    }


def bilingual_rows(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    texts = frame["Context"].tolist() + frame["context_rw"].tolist()
    labels = frame["intent"].tolist() * 2
    return texts, labels


def save_confusions(model: Pipeline, test: pd.DataFrame, classes: list[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for axis, (language, column) in zip(axes, (("English", "Context"), ("Kinyarwanda", "context_rw"))):
        predicted = model.predict(test[column])
        matrix = confusion_matrix(test["intent"], predicted, labels=classes)
        image = axis.imshow(matrix, cmap="Blues")
        axis.set_xticks(range(len(classes)), classes, rotation=50, ha="right", fontsize=8)
        axis.set_yticks(range(len(classes)), classes, fontsize=8)
        axis.set(title=f"{language} intent confusion matrix", xlabel="Predicted", ylabel="Expected")
        for row in range(len(classes)):
            for column_index in range(len(classes)):
                axis.text(column_index, row, str(matrix[row, column_index]),
                          ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=axis, shrink=.7)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "confusion_matrices.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    frame = pd.read_csv(DATA_PATH).dropna(subset=["Context", "intent", "context_rw"])
    for column in ("Context", "intent", "context_rw"):
        frame[column] = frame[column].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    raw_rows = len(frame)
    frame["rw_normalised"] = frame["context_rw"].str.lower()
    frame = frame.drop_duplicates("rw_normalised").drop(columns="rw_normalised").reset_index(drop=True)

    train, temporary = train_test_split(
        frame, test_size=.30, stratify=frame["intent"], random_state=SEED
    )
    validation, test = train_test_split(
        temporary, test_size=.50, stratify=temporary["intent"], random_state=SEED
    )
    train_x, train_y = bilingual_rows(train)
    validation_x, validation_y = bilingual_rows(validation)

    definitions = {
        "Dummy baseline": DummyClassifier(strategy="most_frequent"),
        "Complement NB": ComplementNB(alpha=.5),
        "Logistic Regression": LogisticRegression(
            max_iter=3000, C=4, class_weight="balanced", random_state=SEED
        ),
        "Calibrated Linear SVM": CalibratedClassifierCV(
            LinearSVC(C=1, class_weight="balanced", random_state=SEED), cv=3
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=250, class_weight="balanced", random_state=SEED, n_jobs=-1
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=250, class_weight="balanced", random_state=SEED, n_jobs=-1
        ),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=7, weights="distance"),
    }
    candidates = {}
    for name, estimator in definitions.items():
        model = make_pipeline(estimator)
        model.fit(train_x, train_y)
        candidates[name] = {"model": model, "validation": score(model, validation_x, validation_y)}
    selected = max(candidates, key=lambda name: candidates[name]["validation"]["macro_f1"])

    fit_frame = pd.concat([train, validation], ignore_index=True)
    fit_x, fit_y = bilingual_rows(fit_frame)
    final_model = make_pipeline(definitions[selected]).fit(fit_x, fit_y)
    test_en = score(final_model, test["Context"].tolist(), test["intent"].tolist())
    test_rw = score(final_model, test["context_rw"].tolist(), test["intent"].tolist())
    test_x, test_y = bilingual_rows(test)
    test_combined = score(final_model, test_x, test_y)

    manifest = {
        "task": "six-class bilingual emotional-intent classification",
        "source": "Amod/mental_health_counseling_conversations-derived project file",
        "source_revision": "d7e86f0813c5690181b41f97403c3674aa55dcef",
        "label_status": "project-authored keyword weak labels; not human annotations",
        "kinyarwanda_status": "NLLB-200 machine translations; native review required",
        "raw_rows": raw_rows,
        "rows_after_exact_kinyarwanda_deduplication": len(frame),
        "split_rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "classes": sorted(frame["intent"].unique()),
        "selected_pipeline": selected,
        "candidate_validation": {
            name: details["validation"] for name, details in candidates.items()
        },
        "untouched_test": {"combined": test_combined, "english": test_en, "kinyarwanda": test_rw},
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH, compress=3)
    (REPORT_DIR / "metrics.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (REPORT_DIR / "test_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["language", "text", "expected", "predicted"])
        writer.writeheader()
        for language, column in (("en", "Context"), ("rw", "context_rw")):
            predicted = final_model.predict(test[column])
            for text, expected, actual in zip(test[column], test["intent"], predicted):
                writer.writerow({
                    "language": language, "text": text,
                    "expected": expected, "predicted": actual,
                })
    save_confusions(final_model, test, sorted(frame["intent"].unique()))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
