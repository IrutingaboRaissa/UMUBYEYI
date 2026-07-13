"""Fine-tune a real bilingual generator for Umubyeyi using LoRA.

This updates trainable adapter weights on top of google/mt5-small.  It is not
prompt configuration.  The generator is trained only on the separate grounding
collection; the tabular PPD screening dataset is never treated as conversation.

Recommended full run (GPU/Colab):
    python train_grounded_generator.py

Small pipeline check:
    python train_grounded_generator.py --smoke
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "models" / "umubyeyi-mt5-lora"
REPORT_DIR = ROOT / "reports" / "generator"


def create_generator_figures(manifest: dict, history: list[dict], report_dir: Path = REPORT_DIR) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report_dir.mkdir(parents=True, exist_ok=True)
    training = [(row["step"], row["loss"]) for row in history if "loss" in row]
    validation = [(row["epoch"], row["eval_loss"]) for row in history if "eval_loss" in row]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    if training:
        axes[0].plot(*zip(*training), marker="o", markersize=3, label="training loss")
    if validation:
        twin = axes[0].twiny()
        twin.plot(*zip(*validation), color="#D36B4B", marker="s", markersize=3, label="validation loss")
        twin.set_xlabel("Epoch")
    axes[0].set_title("mT5 LoRA learning curves")
    axes[0].set_xlabel("Optimizer step")
    axes[0].set_ylabel("Loss")
    axes[0].grid(alpha=.2)

    base = manifest["baseline_test"]
    tuned = manifest["fine_tuned_test"]
    names = ["ROUGE-L", "Evidence overlap"]
    x = range(len(names))
    axes[1].bar([i - .18 for i in x], [base["rouge_l_f1"], base["mean_grounding_overlap"]],
                width=.36, label="base mT5", color="#B9A7BC")
    axes[1].bar([i + .18 for i in x], [tuned["rouge_l_f1"], tuned["mean_grounding_overlap"]],
                width=.36, label="fine-tuned", color="#488A68")
    axes[1].set_xticks(list(x), names)
    axes[1].set_ylim(0, 1)
    axes[1].set_title("Untouched-topic generation results")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(report_dir / "generator_training_and_test.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def lcs_length(a: list[str], b: list[str]) -> int:
    previous = [0] * (len(b) + 1)
    for left in a:
        current = [0]
        for index, right in enumerate(b, 1):
            current.append(previous[index - 1] + 1 if left == right else max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def text_metrics(
    predictions: list[str], references: list[str], evidence: list[str], languages: list[str]
) -> dict:
    from src.finetuned_generator import grounding_overlap, validate_grounded_generation

    rouge_l, exact = [], []
    for prediction, reference in zip(predictions, references):
        p, r = prediction.lower().split(), reference.lower().split()
        common = lcs_length(p, r)
        precision = common / len(p) if p else 0.0
        recall = common / len(r) if r else 0.0
        rouge_l.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
        exact.append(prediction.strip() == reference.strip())
    accepted = [
        bool(validate_grounded_generation(p, e, lang))
        for p, e, lang in zip(predictions, evidence, languages)
    ]
    return {
        "rouge_l_f1": round(sum(rouge_l) / len(rouge_l), 4),
        "exact_match": round(sum(exact) / len(exact), 4),
        "mean_grounding_overlap": round(sum(
            grounding_overlap(p, e) for p, e in zip(predictions, evidence)
        ) / len(predictions), 4),
        "strict_grounding_acceptance": round(sum(accepted) / len(predictions), 4),
        "strict_acceptance_by_language": {
            lang: round(
                sum(ok for ok, item_lang in zip(accepted, languages) if item_lang == lang)
                / sum(item_lang == lang for item_lang in languages), 4
            )
            for lang in sorted(set(languages))
        },
        "examples": len(predictions),
    }


def generate_predictions(model, tokenizer, examples: list[dict], limit: int) -> list[str]:
    import torch

    chosen = examples[:limit] if limit else examples
    predictions = []
    model.eval()
    for example in chosen:
        batch = tokenizer(example["input"], return_tensors="pt", truncation=True, max_length=512)
        batch = {key: value.to(model.device) for key, value in batch.items()}
        with torch.inference_mode():
            output = model.generate(**batch, max_new_tokens=180, num_beams=2, no_repeat_ngram_size=3)
        predictions.append(tokenizer.decode(output[0], skip_special_tokens=True).strip())
    return predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="google/mt5-small")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=float, default=8.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--variants", type=int, default=6)
    parser.add_argument("--eval-limit", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    random.seed(42)
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
        EarlyStoppingCallback, Seq2SeqTrainer, Seq2SeqTrainingArguments,
    )
    from src.generation_data import build_generation_examples, dataset_summary

    if args.smoke:
        args.epochs = 1.0
        args.variants = 1
        args.eval_limit = 2
        args.output_dir = ROOT / "models" / "_generator_smoke"
    report_dir = ROOT / "reports" / "_generator_smoke" if args.smoke else REPORT_DIR

    examples = build_generation_examples(variants_per_language=args.variants)
    summary = dataset_summary(examples)
    split_rows = {
        split: [{"input": x["input"], "target": x["target"]} for x in examples if x["split"] == split]
        for split in ("train", "validation", "test")
    }
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    def tokenize(batch):
        encoded = tokenizer(batch["input"], max_length=512, truncation=True)
        encoded["labels"] = tokenizer(text_target=batch["target"], max_length=220, truncation=True)["input_ids"]
        return encoded

    datasets = {
        split: Dataset.from_list(rows).map(tokenize, batched=True, remove_columns=["input", "target"])
        for split, rows in split_rows.items()
    }
    base_model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)
    lora = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM, r=8, lora_alpha=16,
        lora_dropout=0.05, target_modules=["q", "v"], bias="none",
    )
    model = get_peft_model(base_model, lora)
    trainable, total = model.get_nb_trainable_parameters()
    test_examples = [x for x in examples if x["split"] == "test"]
    eval_n = min(args.eval_limit or len(test_examples), len(test_examples))

    started = time.time()
    baseline_predictions = generate_predictions(model, tokenizer, test_examples, eval_n)
    baseline_metrics = text_metrics(
        baseline_predictions, [x["target"] for x in test_examples[:eval_n]],
        [x["evidence"] for x in test_examples[:eval_n]],
        [x["language"] for x in test_examples[:eval_n]],
    )

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output_dir.parent / "_generator_checkpoints"),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        eval_strategy="epoch", save_strategy="epoch", logging_strategy="steps", logging_steps=5,
        save_total_limit=2, load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, predict_with_generate=False, report_to="none", seed=42,
        fp16=False, dataloader_num_workers=0,
    )
    trainer = Seq2SeqTrainer(
        model=model, args=training_args, train_dataset=datasets["train"],
        eval_dataset=datasets["validation"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    result = trainer.train()
    tuned_predictions = generate_predictions(model, tokenizer, test_examples, eval_n)
    tuned_metrics = text_metrics(
        tuned_predictions, [x["target"] for x in test_examples[:eval_n]],
        [x["evidence"] for x in test_examples[:eval_n]],
        [x["language"] for x in test_examples[:eval_n]],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fine_tuned": True,
        "method": "LoRA supervised fine-tuning (PEFT)",
        "base_model": args.base_model,
        "task": "bilingual evidence-conditioned postpartum support generation",
        "seed": 42,
        "dataset": summary,
        "data_statement": (
            "Project-authored prompt augmentation over 14 source-attributed knowledge passages; "
            "the 800-row tabular PPD dataset is not used for generator training."
        ),
        "kinyarwanda_review": "required before real-world use",
        "accepted_generation_languages": [
            lang for lang, rate in tuned_metrics["strict_acceptance_by_language"].items()
            if rate >= 0.5
        ],
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_percentage": round(100 * trainable / total, 4),
        "epochs_requested": args.epochs,
        "train_runtime_seconds": round(time.time() - started, 2),
        "training_loss": round(float(result.training_loss), 6),
        "baseline_test": baseline_metrics,
        "fine_tuned_test": tuned_metrics,
        "test_topics_held_out_from_training": summary["topics_by_split"]["test"],
    }
    (args.output_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (report_dir / "metrics.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (report_dir / "loss_history.json").write_text(json.dumps(trainer.state.log_history, indent=2), encoding="utf-8")
    create_generator_figures(manifest, trainer.state.log_history, report_dir)
    samples = [
        {"language": ex["language"], "topic": ex["topic"], "prediction": prediction,
         "reference": ex["target"], "evidence": ex["evidence"]}
        for ex, prediction in zip(test_examples[:eval_n], tuned_predictions)
    ]
    (report_dir / "test_generations.json").write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
