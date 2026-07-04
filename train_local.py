"""
Train Umubyeyi's own models locally (no Colab, artifacts land straight in models/).

Usage:
    python train_local.py classifier    # fast (seconds) -> models/intent_clf.joblib
    python train_local.py generator     # slow on CPU (1-3h) -> models/umubyeyi-generator/
    python train_local.py all            # both

Env overrides (generator):
    UMU_EPOCHS=6         number of epochs
    UMU_MAX=0            cap training examples (0 = all); use a small number for a smoke test
    UMU_BASE=google/mt5-small
"""
import json
import os
import re
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)

AMOD_CSV = ROOT / "data" / "raw" / "amod_full.csv"
# prefer the 263-pair POSTPARTUM bank; fall back to the legacy 859 bank
BANK_JSON = ROOT / "data" / "grounding_bank_postpartum.json"
if not BANK_JSON.exists():
    BANK_JSON = ROOT / "data" / "grounding_bank.json"

# ----------------------------------------------------------------- classifier (router)
INTENT_KEYWORDS = {
    "self_care_coping":     ["self-care", "self care", "coping", "cope", "manage", "routine", "advice", "what can i do", "take care"],
    "sleep":                ["sleep", "insomnia", "tired", "exhaust", "awake", "rest", "fatigue"],
    "overwhelmed_identity": ["overwhelm", "myself", "identity", "lost", "failing", "failure", "too much", "can't handle"],
    "sadness_low_mood":     ["sad", "depress", "empty", "hopeless", "tearful", "cry", "worthless", "down", "numb", "miserable"],
    "anxiety_worry":        ["anxi", "worry", "worried", "panic", "afraid", "fear", "nervous", "scared", "stress"],
    "relationship_support": ["partner", "husband", "wife", "family", "relationship", "alone", "lonely", "support", "marriage", "friend"],
}
EXCLUDE = ["childhood trauma", "addict", "alcohol", "drug", "eating disorder", "anorexia", "bulimia",
           "ptsd", "flashback", "personality disorder", "schizophren", "bipolar"]


def train_classifier():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    df = pd.read_csv(AMOD_CSV)
    df.columns = [c.strip() for c in df.columns]
    df["Context"] = df["Context"].astype(str).str.strip()
    df = df[df["Context"].str.len() > 0].drop_duplicates("Context").reset_index(drop=True)

    ctx = df["Context"].str.lower()
    names = list(INTENT_KEYWORDS)
    hits = pd.DataFrame({i: ctx.str.contains("|".join(re.escape(k) for k in kws), regex=True)
                         for i, kws in INTENT_KEYWORDS.items()}).astype(int)
    excluded = ctx.str.contains("|".join(re.escape(k) for k in EXCLUDE), regex=True)
    n_intents = hits.sum(axis=1)
    df["intent"] = [names[j] for j in hits.values.argmax(axis=1)]
    df.loc[(n_intents == 0) | excluded, "intent"] = np.nan
    data = df.dropna(subset=["intent"]).reset_index(drop=True)
    print(f"[classifier] labeled {len(data)} questions across {data['intent'].nunique()} intents")
    print(data["intent"].value_counts().to_string())

    # deployed router: fit the word+char TF-IDF + LogReg on ALL labeled data, save as one text->intent pipeline
    vec = FeatureUnion([
        ("word", TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, max_features=8000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
    ])
    pipe = Pipeline([("tfidf", vec),
                     ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42))])
    pipe.fit(data["Context"], data["intent"])
    out = MODELS / "intent_clf.joblib"
    joblib.dump(pipe, out)
    print(f"[classifier] saved -> {out}")
    for t in ["I can't stop crying and feel worthless", "I'm so anxious I can't breathe", "I never sleep anymore"]:
        print(f"   {t!r} -> {pipe.predict([t])[0]}")


# ------------------------------------------------------------------ generator (mT5)
N_NOTES = 2
HEADER = ("You are Umubyeyi, a warm companion for the emotional wellbeing of first-time mothers "
          "in Rwanda in the first 6 months after birth. Using the validated notes, reply with "
          "warmth and empathy in English.\n")


def _build_examples():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    bank = json.loads(BANK_JSON.read_text(encoding="utf-8"))
    rows = [b for b in bank if b.get("answer_en", "").strip() and b.get("question_en", "").strip()]
    search = [f'{b["question_en"]} {b.get("question_rw","")}' for b in rows]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
    mat = vec.fit_transform(search)
    sims = cosine_similarity(mat)
    np.fill_diagonal(sims, -1.0)

    examples = []
    for i, b in enumerate(rows):
        nbrs = sims[i].argsort()[::-1][:N_NOTES]
        notes = "\n".join(f"- {rows[j]['answer_en'].strip()}" for j in nbrs)
        examples.append({"input": f"{HEADER}Notes:\n{notes}\nMother: {b['question_en'].strip()}\nAnswer:",
                         "target": b["answer_en"].strip()})
    return examples


def train_generator():
    from datasets import Dataset
    from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
                              Seq2SeqTrainer, Seq2SeqTrainingArguments)

    base = os.environ.get("UMU_BASE", "google/flan-t5-base")
    epochs = int(os.environ.get("UMU_EPOCHS", "6"))
    cap = int(os.environ.get("UMU_MAX", "0"))

    examples = _build_examples()
    if cap:
        examples = examples[:cap]
    print(f"[generator] {len(examples)} grounded examples | base={base} | epochs={epochs} | device=CPU")

    ds = Dataset.from_list(examples).train_test_split(test_size=0.1, seed=42)
    tok = AutoTokenizer.from_pretrained(base)

    def _tok(b):
        m = tok(b["input"], max_length=512, truncation=True)
        m["labels"] = tok(text_target=b["target"], max_length=200, truncation=True)["input_ids"]
        return m

    ds = ds.map(_tok, batched=True, remove_columns=["input", "target"])
    model = AutoModelForSeq2SeqLM.from_pretrained(base)

    args = Seq2SeqTrainingArguments(
        output_dir=str(MODELS / "_gen_ckpt"), num_train_epochs=epochs, learning_rate=3e-4,
        per_device_train_batch_size=4, per_device_eval_batch_size=4,
        eval_strategy="epoch", save_strategy="no", logging_steps=25,
        predict_with_generate=True, fp16=False, report_to="none", seed=42)

    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=ds["train"], eval_dataset=ds["test"],
                             data_collator=DataCollatorForSeq2Seq(tok, model=model), processing_class=tok)
    trainer.train()

    out = MODELS / "umubyeyi-generator"
    out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out))
    tok.save_pretrained(str(out))
    # persist the loss history so we can plot it for the slides without Colab
    hist = [h for h in trainer.state.log_history if "loss" in h or "eval_loss" in h]
    (ROOT / "reports").mkdir(exist_ok=True)
    json.dump(hist, open(ROOT / "reports" / "generator_loss_history.json", "w"), indent=2)
    print(f"[generator] saved -> {out}  (+ reports/generator_loss_history.json)")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("classifier", "all"):
        train_classifier()
    if what in ("generator", "all"):
        train_generator()
