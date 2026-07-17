"""Build a small, real background sample for SHAP explanations of the guided check-in model.

Reuses the exact same seed-42, stratified 70/15/15 split as train_checkin_classifier.py so
only genuine TRAINING-split rows end up in the background reference (never validation/test).
The background is used by src/explain.py to explain individual predictions; it is not itself
a trained artifact and contains no participant identifiers, just the same 15 feature columns
already used at runtime.

Also writes a categories sidecar (one sorted list of valid values per categorical feature,
taken from the FULL 800-row dataset, not just the sampled background) so src/explain.py can
integer-encode categorical answers for SHAP's masker without ever missing a valid dropdown
value that simply didn't land in the small background sample.
"""
import json

import pandas as pd
from sklearn.model_selection import train_test_split

from train_checkin_classifier import FEATURES, ROOT
from train_ppd_classifier import DATA, SEED

BACKGROUND_SIZE = 40
NUMERIC_FEATURES = {"Age"}
OUTPUT = ROOT / "models" / "ppd_checkin_shap_background.csv"
CATEGORIES_OUTPUT = ROOT / "models" / "ppd_checkin_shap_categories.json"


def main():
    df = pd.read_csv(DATA)
    X = df[FEATURES].copy()
    y = df["EPDS Result"].astype(str).eq("High").map({True: "elevated", False: "not_elevated"})
    X_train, _, y_train, _ = train_test_split(X, y, test_size=.30, stratify=y, random_state=SEED)

    background = X_train.sample(n=min(BACKGROUND_SIZE, len(X_train)), random_state=SEED)
    background.to_csv(OUTPUT, index=False)

    categories = {
        col: sorted(str(v) for v in X[col].dropna().unique())
        for col in FEATURES if col not in NUMERIC_FEATURES
    }
    CATEGORIES_OUTPUT.write_text(json.dumps(categories, indent=2), encoding="utf-8")
    print(f"Wrote {len(background)} background rows to {OUTPUT}")
    print(f"Wrote category domains for {len(categories)} features to {CATEGORIES_OUTPUT}")


if __name__ == "__main__":
    main()
