"""
Evaluate the DEPLOYED generator on the SAME pruned-bank held-out split it never trained on,
so the eval slide matches what actually runs. Reuses train_local's grounded-example builder
(identical data + prompt format), scores ROUGE + BLEU, then runs a behaviour showcase.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import train_local  # same pruned 158-pair postpartum bank + grounded-example builder as training

from datasets import Dataset

examples = train_local._build_examples()
test = Dataset.from_list(examples).train_test_split(test_size=0.1, seed=42)["test"]
print(f"held-out examples: {len(test)} (of {len(examples)} grounded pairs)")

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
res = {"model": "flan-t5-small (deployed, early-stopped, pruned postpartum bank)",
       "held_out_examples": len(preds),
       "rouge1": round(rouge["rouge1"], 4), "rouge2": round(rouge["rouge2"], 4),
       "rougeL": round(rouge["rougeL"], 4), "bleu": round(bleu["score"], 2)}
(ROOT / "reports").mkdir(exist_ok=True)
json.dump(res, open(ROOT / "reports" / "generator_eval.json", "w"), indent=2)
print("\n==== DEPLOYED-MODEL EVAL (held-out) ====")
print(res)

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
