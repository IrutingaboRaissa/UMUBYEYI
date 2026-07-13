"""Train and evaluate Umubyeyi's bilingual supervised topic classifier.

Training uses the 168 labelled, project-authored generator prompts plus alternative
representations already present in the 14-topic knowledge bank. The final controlled
test contains 28 independently phrased cases and is never used for fitting.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from evaluate_system_layers import RETRIEVAL_CASES
from src.generation_data import build_generation_examples

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "topic_classifier.joblib"
REPORT_DIR = ROOT / "reports" / "topic_classifier"
BANK_PATH = ROOT / "data" / "knowledge" / "postpartum_wellbeing.json"


def feature_pipeline(kind: str) -> FeatureUnion | TfidfVectorizer:
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")
    char = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, strip_accents="unicode"
    )
    if kind == "word":
        return word
    if kind == "char":
        return char
    return FeatureUnion([("word", word), ("char", char)])


def make_pipeline(kind: str) -> Pipeline:
    return Pipeline([
        ("features", feature_pipeline(kind)),
        ("classifier", LogisticRegression(
            max_iter=3000, C=4.0, class_weight="balanced", random_state=42
        )),
    ])


def top_k_accuracy(model: Pipeline, texts: list[str], labels: list[str], k: int) -> float:
    probabilities = model.predict_proba(texts)
    classes = model.named_steps["classifier"].classes_
    ranked = np.argsort(probabilities, axis=1)[:, -k:]
    return float(np.mean([label in classes[indexes] for label, indexes in zip(labels, ranked)]))


def score(model: Pipeline, texts: list[str], labels: list[str]) -> dict:
    predicted = model.predict(texts)
    return {
        "cases": len(labels),
        "accuracy": round(float(accuracy_score(labels, predicted)), 4),
        "macro_f1": round(float(f1_score(labels, predicted, average="macro")), 4),
        "top_3_accuracy": round(top_k_accuracy(model, texts, labels, 3), 4),
    }


def knowledge_examples() -> tuple[list[str], list[str]]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    texts, labels = [], []
    for row in bank:
        variants = [
            row["topic"], row["queries_en"], row["queries_rw"],
            row["text_en"], row["text_rw"],
        ]
        texts.extend(text for text in variants if text.strip())
        labels.extend([row["id"]] * sum(bool(text.strip()) for text in variants))
    return texts, labels


def create_confusion_figure(labels: list[str], predicted: list[str], classes: list[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matrix = confusion_matrix(labels, predicted, labels=classes)
    fig, ax = plt.subplots(figsize=(12, 10))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(classes)), classes, rotation=55, ha="right", fontsize=8)
    ax.set_yticks(range(len(classes)), classes, fontsize=8)
    ax.set_xlabel("Predicted topic")
    ax.set_ylabel("Expected topic")
    ax.set_title("Bilingual topic classifier — controlled 28-case test")
    for row in range(len(classes)):
        for column in range(len(classes)):
            if matrix[row, column]:
                ax.text(column, row, str(matrix[row, column]), ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, shrink=.7)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "confusion_matrix.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    generated = build_generation_examples()
    query_texts = [row["query"] for row in generated]
    query_labels = [row["topic_id"] for row in generated]
    train_x, validation_x, train_y, validation_y = train_test_split(
        query_texts, query_labels, test_size=.2, random_state=42, stratify=query_labels
    )
    extra_x, extra_y = knowledge_examples()
    train_x.extend(extra_x)
    train_y.extend(extra_y)

    candidates = {}
    for kind in ("word", "char", "char_word"):
        model = make_pipeline(kind)
        model.fit(train_x, train_y)
        candidates[kind] = {"model": model, "validation": score(model, validation_x, validation_y)}
    representation_priority = {"word": 0, "char": 1, "char_word": 2}
    selected_name = max(
        candidates, key=lambda name: (
            candidates[name]["validation"]["macro_f1"],
            candidates[name]["validation"]["top_3_accuracy"],
            representation_priority[name],
        )
    )

    final_model = make_pipeline(selected_name)
    full_x, full_y = query_texts + extra_x, query_labels + extra_y
    final_model.fit(full_x, full_y)
    test_x = [query for _, _, query in RETRIEVAL_CASES]
    test_y = [topic for _, topic, _ in RETRIEVAL_CASES]
    test_languages = [language for language, _, _ in RETRIEVAL_CASES]
    predicted = final_model.predict(test_x)

    by_language = {}
    for language in ("en", "rw"):
        indexes = [index for index, item in enumerate(test_languages) if item == language]
        by_language[language] = score(
            final_model, [test_x[index] for index in indexes], [test_y[index] for index in indexes]
        )
    manifest = {
        "training_source": "168 project-authored augmented prompts + 70 knowledge-bank representations",
        "external_validity": "controlled project-authored test; not real-user or clinical validation",
        "training_examples": len(full_x),
        "topics": len(set(full_y)),
        "selected_pipeline": selected_name,
        "candidate_validation": {
            name: value["validation"] for name, value in candidates.items()
        },
        "controlled_test": {**score(final_model, test_x, test_y), "by_language": by_language},
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)
    (REPORT_DIR / "metrics.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (REPORT_DIR / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["language", "query", "expected", "predicted"])
        writer.writeheader()
        for language, query, expected, actual in zip(test_languages, test_x, test_y, predicted):
            writer.writerow({
                "language": language, "query": query, "expected": expected, "predicted": actual
            })
    create_confusion_figure(test_y, list(predicted), sorted(set(test_y)))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
