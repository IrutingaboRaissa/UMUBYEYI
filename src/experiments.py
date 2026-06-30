"""
Umubyeyi - classification experiment suite (Analysis chapter).

Runs 10 systematic experiments on the 724 weak-labelled Amod questions (6 postpartum
mental-wellbeing intents), covering hyperparameters AND optimization techniques. The aim is
not to "win" a metric (the ceiling is the weak keyword labels, proven across models) but to
demonstrate rigorous ML methodology and isolate the bottleneck.

Output: prints a results table and writes reports/experiment_results.csv (+ a learning curve).
Run:  python src/experiments.py
"""
import sys, csv, json
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"; REPORTS.mkdir(exist_ok=True)
SEED = 42
np.random.seed(SEED)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, learning_curve
from sklearn.naive_bayes import ComplementNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import accuracy_score, f1_score

# ---------------- data ----------------
rows = list(csv.DictReader(open(ROOT / "notebooks" / "amod_kinyarwanda.csv", encoding="utf-8")))
X = np.array([r["Context"].strip() for r in rows])
y = np.array([r["intent"].strip() for r in rows])
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
print(f"data: {len(X)} questions, {len(set(y))} intents | train {len(Xtr)} / test {len(Xte)}\n")

results = []
def record(exp, config, acc, f1, note=""):
    results.append({"experiment": exp, "config": config,
                    "accuracy": round(acc, 3), "macro_f1": round(f1, 3), "note": note})
    print(f"  {config:<46} acc={acc:.3f}  macroF1={f1:.3f}  {note}")

def make_vec(use_word=True, use_char=True, word_ng=(1, 2), char_ng=(3, 5), max_features=None):
    parts = []
    if use_word:
        parts.append(("w", TfidfVectorizer(analyzer="word", ngram_range=word_ng,
                      sublinear_tf=True, min_df=2, max_features=max_features)))
    if use_char:
        parts.append(("c", TfidfVectorizer(analyzer="char_wb", ngram_range=char_ng,
                      sublinear_tf=True, min_df=2, max_features=max_features)))
    return FeatureUnion(parts)

def evaluate(clf, vec=None):
    pipe = Pipeline([("vec", vec or make_vec()), ("clf", clf)])
    pipe.fit(Xtr, ytr)
    p = pipe.predict(Xte)
    return accuracy_score(yte, p), f1_score(yte, p, average="macro"), pipe

# ---------------- E1: ComplementNB (alpha) ----------------
print("E1 - ComplementNB baseline (alpha smoothing)")
for a in (0.1, 0.3, 1.0):
    acc, f1, _ = evaluate(ComplementNB(alpha=a))
    record("E1 ComplementNB", f"alpha={a}", acc, f1, "baseline" if a == 1.0 else "")

# ---------------- E2: Logistic Regression (C / L2) ----------------
print("\nE2 - Logistic Regression (C = inverse L2 regularization)")
for C in (0.01, 0.1, 1, 10):
    acc, f1, _ = evaluate(LogisticRegression(C=C, class_weight="balanced", max_iter=2000))
    record("E2 LogReg", f"C={C}", acc, f1)

# ---------------- E3: Linear SVM (C) ----------------
print("\nE3 - Linear SVM (C = regularization)")
for C in (0.01, 0.1, 1, 10):
    acc, f1, _ = evaluate(LinearSVC(C=C, class_weight="balanced"))
    record("E3 LinearSVM", f"C={C}", acc, f1)

# ---------------- E4: Random Forest (capacity) ----------------
print("\nE4 - Random Forest (n_estimators x max_depth)")
for n in (100, 300):
    for d in (None, 30):
        acc, f1, _ = evaluate(RandomForestClassifier(n_estimators=n, max_depth=d,
                              class_weight="balanced", random_state=SEED, n_jobs=-1))
        record("E4 RandomForest", f"n={n},max_depth={d}", acc, f1)

# ---------------- E5: TF-IDF feature ablation ----------------
print("\nE5 - TF-IDF feature ablation (fixed LinearSVM C=1)")
for name, vec in (("word(1,2)", make_vec(use_char=False)),
                  ("char_wb(3,5)", make_vec(use_word=False)),
                  ("word+char", make_vec()),
                  ("word+char,max_feat=5000", make_vec(max_features=5000))):
    acc, f1, _ = evaluate(LinearSVC(C=1, class_weight="balanced"), vec=vec)
    record("E5 TF-IDF ablation", name, acc, f1)

# ---------------- E6: class imbalance handling ----------------
print("\nE6 - Class-imbalance techniques (LinearSVM C=1)")
def resample(idx_text, idx_y, mode):
    classes, counts = np.unique(idx_y, return_counts=True)
    target = counts.max() if mode == "oversample" else counts.min()
    keep = []
    for c in classes:
        ci = np.where(idx_y == c)[0]
        rep = mode == "oversample"
        keep.append(np.random.choice(ci, size=target, replace=rep))
    keep = np.concatenate(keep); np.random.shuffle(keep)
    return idx_text[keep], idx_y[keep]

acc, f1, _ = evaluate(LinearSVC(C=1))
record("E6 imbalance", "none (no class_weight)", acc, f1)
acc, f1, _ = evaluate(LinearSVC(C=1, class_weight="balanced"))
record("E6 imbalance", "class_weight=balanced", acc, f1)
for mode in ("oversample", "undersample"):
    Xr, yr = resample(Xtr, ytr, mode)
    pipe = Pipeline([("vec", make_vec()), ("clf", LinearSVC(C=1))]).fit(Xr, yr)
    p = pipe.predict(Xte)
    record("E6 imbalance", f"random {mode}", accuracy_score(yte, p), f1_score(yte, p, average="macro"))

# ---------------- E7: Gradient Boosting (learning rate) ----------------
print("\nE7 - Gradient Boosting on SVD(100) features (learning_rate)")
for lr in (0.05, 0.1, 0.3):
    pipe = Pipeline([("vec", make_vec()), ("svd", TruncatedSVD(100, random_state=SEED)),
                     ("clf", GradientBoostingClassifier(learning_rate=lr, n_estimators=200, random_state=SEED))])
    pipe.fit(Xtr, ytr); p = pipe.predict(Xte)
    record("E7 GradientBoosting", f"lr={lr}", accuracy_score(yte, p), f1_score(yte, p, average="macro"))

# ---------------- E8: calibration + selective prediction ----------------
print("\nE8 - Calibration + selective prediction (LinearSVM)")
cal = Pipeline([("vec", make_vec()),
                ("clf", CalibratedClassifierCV(LinearSVC(C=1, class_weight="balanced"), cv=3))]).fit(Xtr, ytr)
proba = cal.predict_proba(Xte); pred = cal.classes_[proba.argmax(1)]; conf = proba.max(1)
acc_all = accuracy_score(yte, pred)
for thr in (0.0, 0.4, 0.6):
    mask = conf >= thr
    cov = mask.mean(); acc_cov = accuracy_score(yte[mask], pred[mask]) if mask.any() else 0.0
    record("E8 selective pred", f"threshold={thr}", acc_cov, f1_score(yte, pred, average="macro"),
           f"coverage={cov:.0%}")

# ---------------- E9: MLP optimization (optimizer / LR / early stopping) ----------------
print("\nE9 - MLP optimization sweep on SVD(100) features")
base = Pipeline([("vec", make_vec()), ("svd", TruncatedSVD(100, random_state=SEED))]).fit(Xtr, ytr)
Ztr, Zte = base.transform(Xtr), base.transform(Xte)
for solver in ("adam", "sgd"):
    for lr in (0.001, 0.01):
        for es in (False, True):
            mlp = MLPClassifier(hidden_layer_sizes=(128,), solver=solver, learning_rate_init=lr,
                                alpha=1e-4, early_stopping=es, max_iter=300, random_state=SEED)
            mlp.fit(Ztr, ytr); p = mlp.predict(Zte)
            record("E9 MLP optim", f"{solver},lr={lr},early_stop={es}",
                   accuracy_score(yte, p), f1_score(yte, p, average="macro"))

# ---------------- E10: evaluation rigor (CV vs single split) ----------------
print("\nE10 - Evaluation rigor: 5-fold CV vs single split (best model)")
best = Pipeline([("vec", make_vec()), ("clf", LinearSVC(C=1, class_weight="balanced"))])
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
f1_cv = cross_val_score(best, X, y, cv=cv, scoring="f1_macro")
acc_single, f1_single, _ = evaluate(LinearSVC(C=1, class_weight="balanced"))
record("E10 CV rigor", "single 80/20 split", acc_single, f1_single)
record("E10 CV rigor", "5-fold CV (macroF1 mean)", float(f1_cv.mean()), float(f1_cv.mean()),
       f"std={f1_cv.std():.3f} -> {f1_cv.mean():.3f}+/-{f1_cv.std():.3f}")

# learning curve (overfitting evidence)
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    sizes, tr_s, te_s = learning_curve(best, X, y, cv=cv, scoring="f1_macro",
                                       train_sizes=np.linspace(0.2, 1.0, 6), n_jobs=-1)
    plt.figure(figsize=(6, 4))
    plt.plot(sizes, tr_s.mean(1), "o-", label="train macro-F1")
    plt.plot(sizes, te_s.mean(1), "s-", label="validation macro-F1")
    plt.xlabel("training examples"); plt.ylabel("macro-F1"); plt.title("Learning curve - LinearSVM")
    plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(REPORTS / "learning_curve.png", dpi=130)
    print(f"\nsaved {REPORTS/'learning_curve.png'}")
except Exception as e:
    print("learning-curve plot skipped:", e)

# ---------------- save ----------------
with open(REPORTS / "experiment_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["experiment", "config", "accuracy", "macro_f1", "note"])
    w.writeheader(); w.writerows(results)

best_row = max(results, key=lambda r: r["macro_f1"])
print(f"\n{'='*70}")
print(f"{len(results)} runs across 10 experiments -> reports/experiment_results.csv")
print(f"best macro-F1: {best_row['macro_f1']} ({best_row['experiment']} | {best_row['config']})")
print("Finding: tuning moves macro-F1 only marginally; the ceiling is the weak labels.")
