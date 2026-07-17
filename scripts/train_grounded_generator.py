"""Fine-tune Umubyeyi's response generator on genuine support conversations.

ESConv provides multi-turn supporter responses. The postpartum knowledge bank
is kept separate for retrieval at inference time. The PPD screening table is
never used as language model supervision.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DEFAULT_OUTPUT = ROOT / "models" / "umubyeyi-mt5-lora"
REPORT_DIR = ROOT / "reports" / "generator"
ESCONV_CACHE = ROOT / "data" / "external" / "ESConv.json"


def lcs_length(a: list[str], b: list[str]) -> int:
    previous = [0] * (len(b) + 1)
    for left in a:
        current = [0]
        for index, right in enumerate(b, 1):
            current.append(
                previous[index - 1] + 1 if left == right
                else max(previous[index], current[-1])
            )
        previous = current
    return previous[-1]


def text_metrics(predictions: list[str], references: list[str]) -> dict:
    rouge_l, exact, bigrams = [], [], set()
    total_bigrams = 0
    for prediction, reference in zip(predictions, references):
        predicted_words = prediction.lower().split()
        reference_words = reference.lower().split()
        common = lcs_length(predicted_words, reference_words)
        precision = common / len(predicted_words) if predicted_words else 0.0
        recall = common / len(reference_words) if reference_words else 0.0
        rouge_l.append(
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        exact.append(prediction.strip() == reference.strip())
        prediction_bigrams = list(zip(predicted_words, predicted_words[1:]))
        bigrams.update(prediction_bigrams)
        total_bigrams += len(prediction_bigrams)
    return {
        "rouge_l_f1": round(sum(rouge_l) / max(1, len(rouge_l)), 4),
        "exact_match": round(sum(exact) / max(1, len(exact)), 4),
        "distinct_2": round(len(bigrams) / max(1, total_bigrams), 4),
        "mean_response_words": round(
            sum(len(item.split()) for item in predictions) / max(1, len(predictions)), 2
        ),
        "examples": len(predictions),
    }


def generate_predictions(model, tokenizer, examples: list[dict], limit: int) -> list[str]:
    import torch

    chosen = examples[:limit] if limit else examples
    predictions = []
    model.eval()
    for example in chosen:
        batch = tokenizer(
            example["input"], return_tensors="pt", truncation=True, max_length=384
        )
        batch = {key: value.to(model.device) for key, value in batch.items()}
        with torch.inference_mode():
            output = model.generate(
                **batch, max_new_tokens=160, num_beams=2, no_repeat_ngram_size=3
            )
        predictions.append(tokenizer.decode(output[0], skip_special_tokens=True).strip())
    return predictions


def create_figures(manifest: dict, history: list[dict], report_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    training = [(row["step"], row["loss"]) for row in history if "loss" in row]
    validation = [(row["epoch"], row["eval_loss"]) for row in history if "eval_loss" in row]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    if training:
        axes[0].plot(*zip(*training), marker="o", markersize=3, label="Training")
    if validation:
        twin = axes[0].twiny()
        twin.plot(*zip(*validation), color="#D36B4B", marker="s", label="Validation")
        twin.set_xlabel("Epoch")
    axes[0].set(title="LoRA loss curves", xlabel="Optimizer step", ylabel="Loss")
    axes[0].grid(alpha=.2)

    base, tuned = manifest["baseline_test"], manifest["fine_tuned_test"]
    names = ["ROUGE-L", "Distinct-2"]
    positions = range(len(names))
    axes[1].bar([x - .18 for x in positions],
                [base["rouge_l_f1"], base["distinct_2"]], .36,
                label="Base mT5", color="#B9A7BC")
    axes[1].bar([x + .18 for x in positions],
                [tuned["rouge_l_f1"], tuned["distinct_2"]], .36,
                label="Fine-tuned", color="#488A68")
    axes[1].set_xticks(list(positions), names)
    axes[1].set(title="Held-out conversation results", ylim=(0, 1))
    axes[1].legend(); axes[1].grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(report_dir / "generator_training_and_test.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="google/mt5-small")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--max-supporter-turns", type=int, default=6)
    parser.add_argument("--eval-limit", type=int, default=100)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    random.seed(42)
    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
        EarlyStoppingCallback, Seq2SeqTrainer, Seq2SeqTrainingArguments,
    )
    from generation_data import (
        ESCONV_COMMIT, ESCONV_SHA256, build_esconv_examples, dataset_summary,
        download_esconv, load_esconv,
    )

    if args.smoke:
        args.epochs = 1.0
        args.max_supporter_turns = 1
        args.eval_limit = 2
        args.output_dir = ROOT / "models" / "_generator_smoke"
    report_dir = ROOT / "reports" / "_generator_smoke" if args.smoke else REPORT_DIR

    esconv_path = download_esconv(ESCONV_CACHE)
    esconv_rows = load_esconv(esconv_path)
    if args.smoke:
        esconv_rows = esconv_rows[:40]
    esconv_examples = build_esconv_examples(
        esconv_rows, max_supporter_turns=args.max_supporter_turns
    )
    examples = esconv_examples
    summary = dataset_summary(examples)

    split_rows = {
        split: [{"input": row["input"], "target": row["target"]}
                for row in examples if row["split"] == split]
        for split in ("train", "validation", "test")
    }
    if any(not rows for rows in split_rows.values()):
        raise ValueError(f"Every split must contain examples: {summary['splits']}")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    def tokenize(batch):
        encoded = tokenizer(batch["input"], max_length=384, truncation=True)
        encoded["labels"] = tokenizer(
            text_target=batch["target"], max_length=180, truncation=True
        )["input_ids"]
        return encoded

    tokenized = {
        split: Dataset.from_list(rows).map(
            tokenize, batched=True, remove_columns=["input", "target"]
        ) for split, rows in split_rows.items()
    }
    base_model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)
    lora = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM, r=8, lora_alpha=16,
        lora_dropout=.05, target_modules=["q", "v"], bias="none",
    )
    model = get_peft_model(base_model, lora)
    if torch.cuda.is_available():
        model.to("cuda")
    trainable, total = model.get_nb_trainable_parameters()

    test_examples = [row for row in examples if row["split"] == "test"]
    eval_count = min(args.eval_limit or len(test_examples), len(test_examples))
    baseline_predictions = generate_predictions(model, tokenizer, test_examples, eval_count)
    references = [row["target"] for row in test_examples[:eval_count]]
    baseline_metrics = text_metrics(baseline_predictions, references)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output_dir.parent / "_generator_checkpoints"),
        num_train_epochs=args.epochs, learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        eval_strategy="epoch", save_strategy="epoch", logging_steps=25,
        save_total_limit=2, load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False,
        report_to="none", seed=42, fp16=torch.cuda.is_available(),
        dataloader_num_workers=0,
    )
    trainer = Seq2SeqTrainer(
        model=model, args=training_args,
        train_dataset=tokenized["train"], eval_dataset=tokenized["validation"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    started = time.time()
    result = trainer.train()
    tuned_predictions = generate_predictions(model, tokenizer, test_examples, eval_count)
    tuned_metrics = text_metrics(tuned_predictions, references)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fine_tuned": True,
        "training_dataset_version": "esconv-v1",
        "method": "LoRA supervised fine-tuning (PEFT)",
        "base_model": args.base_model,
        "task": "English emotional-support response generation",
        "seed": 42,
        "dataset": summary,
        "data_sources": {
            "ESConv": {
                "commit": ESCONV_COMMIT, "sha256": ESCONV_SHA256,
                "license": "academic research use only",
            },
        },
        "data_statement": (
            "Targets are original ESConv supporter turns; no templated or model-generated "
            "answers are used. The postpartum bank is retrieval evidence, not generator "
            "supervision. The AMOD-derived file under data/intent/ trains the separate "
            "bilingual intent classifier only and supplies no generator targets."
        ),
        "accepted_generation_languages": ["en"],
        "kinyarwanda_limitation": (
            "No human-authored Kinyarwanda response corpus was available; Kinyarwanda "
            "generation must remain behind retrieval/Groq fallback and native review."
        ),
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_percentage": round(100 * trainable / total, 4),
        "epochs_requested": args.epochs,
        "train_runtime_seconds": round(time.time() - started, 2),
        "training_loss": round(float(result.training_loss), 6),
        "baseline_test": baseline_metrics,
        "fine_tuned_test": tuned_metrics,
    }
    (args.output_dir / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (report_dir / "metrics.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (report_dir / "loss_history.json").write_text(
        json.dumps(trainer.state.log_history, indent=2), encoding="utf-8"
    )
    create_figures(manifest, trainer.state.log_history, report_dir)
    review_rows = [{
        "dataset": row["dataset"], "problem_type": row["problem_type"],
        "query": row["query"], "reference": row["target"],
        "base_prediction": base, "fine_tuned_prediction": tuned,
        "reviewer": "", "empathy_1_to_5": "", "safety_1_to_5": "",
        "fluency_1_to_5": "", "notes": "",
    } for row, base, tuned in zip(
        test_examples[:eval_count], baseline_predictions, tuned_predictions
    )]
    (report_dir / "test_generations.json").write_text(
        json.dumps(review_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
