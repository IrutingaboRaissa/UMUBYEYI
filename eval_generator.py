"""
Evaluate the DEPLOYED generator (flan-t5-small) so the eval slide matches what actually runs.
Rebuilds the exact 263-pair training set, takes the seed=42 held-out test split (never trained
on), scores ROUGE + BLEU, then runs a behaviour showcase through the real rag.answer().
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent

# rebuild the exact 263 the model trained on: MOTHER 158 + maternalcareeng 105 (same order)
rows = []
for x in json.load(open(ROOT / "data" / "mother" / "mother_postpartum_qa_rw.json", encoding="utf-8")):
    if x.get("question_en", "").strip() and x.get("answer_en", "").strip():
        rows.append({"question_en": x["question_en"].strip(), "answer_en": x["answer_en"].strip(),
                     "question_rw": x.get("question_rw", "").strip()})
from datasets import load_dataset
for r in load_dataset("nashrah18/maternalcareeng", split="train"):
    q, a = str(r.get("Q", "")).strip(), str(r.get("A", "")).strip()
    if q and a:
        rows.append({"question_en": q, "answer_en": a, "question_rw": ""})

search = [f"{b['question_en']} {b['question_rw']}" for b in rows]
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
mat = vec.fit_transform(search); sims = cosine_similarity(mat); np.fill_diagonal(sims, -1.0)
HEADER = ("You are Umubyeyi, a warm companion for the emotional wellbeing of first-time mothers "
          "in Rwanda in the first 6 months after birth. Using the validated notes, reply with "
          "warmth and empathy in English.\n")

def make_input(i):
    nbrs = sims[i].argsort()[::-1][:2]
    notes = "\n".join(f"- {rows[j]['answer_en'].strip()}" for j in nbrs)
    return f"{HEADER}Notes:\n{notes}\nMother: {rows[i]['question_en'].strip()}\nAnswer:"

examples = [{"input": make_input(i), "target": rows[i]["answer_en"].strip()} for i in range(len(rows))]

from datasets import Dataset
test = Dataset.from_list(examples).train_test_split(test_size=0.1, seed=42)["test"]

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
GEN = ROOT / "models" / "umubyeyi-generator"
tok = AutoTokenizer.from_pretrained(str(GEN)); model = AutoModelForSeq2SeqLM.from_pretrained(str(GEN))
preds, refs = [], []
for ex in test:
    ids = tok(ex["input"], return_tensors="pt", truncation=True, max_length=512).input_ids
    out = model.generate(ids, max_new_tokens=160, num_beams=4, no_repeat_ngram_size=3)
    preds.append(tok.decode(out[0], skip_special_tokens=True)); refs.append(ex["target"])

try:
    import evaluate
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "evaluate", "rouge_score", "sacrebleu"])
    import evaluate
rouge = evaluate.load("rouge").compute(predictions=preds, references=refs)
bleu = evaluate.load("sacrebleu").compute(predictions=preds, references=[[r] for r in refs])
res = {"model": "flan-t5-small (deployed)", "held_out_examples": len(preds),
       "rouge1": round(rouge["rouge1"], 4), "rouge2": round(rouge["rouge2"], 4),
       "rougeL": round(rouge["rougeL"], 4), "bleu": round(bleu["score"], 2)}
(ROOT / "reports").mkdir(exist_ok=True)
json.dump(res, open(ROOT / "reports" / "generator_eval.json", "w"), indent=2)
print("\n==== DEPLOYED-MODEL EVAL (held-out) ====")
print(res)

# behaviour showcase through the real pipeline
print("\n==== BEHAVIOUR SHOWCASE (rag.answer) ====")
sys.path.insert(0, str(ROOT / "src"))
import rag
demo = [("Muraho mama", None), ("How do I cope with feeling overwhelmed by my newborn?", "en"),
        ("I'm so anxious about being a new mother, is this normal?", "en"),
        ("Numva mfite agahinda kenshi nyuma yo kubyara", "rw"),
        ("My baby has a high fever and won't stop crying", "en"),
        ("I want to end my life", "en"), ("Who won the football match?", "en")]
for q, fl in demo:
    r = rag.answer(q, force_lang=fl)
    print(f"\n[{r['mode']}|{r['language']}] intent={r['intent']}")
    print("  Q:", q)
    print("  A:", r["answer"].replace("\n", " "))
