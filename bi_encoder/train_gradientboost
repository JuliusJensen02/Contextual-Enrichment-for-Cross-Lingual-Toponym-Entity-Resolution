"""
Train the XGBoost matcher on training data.

Uses encode_entity() and compare() from bi_encoder.py, so training and inference
compute exactly the same features.
"""
import argparse
import json

import numpy as np
from xgboost import XGBClassifier

from bi_encoder import FEATURE_NAMES, compare, encode_entity


def make_dataset(pairs, entities):
    """One feature row and one label per pair."""
    cache, X, y = {}, [], []
    for p in pairs:
        for eid in (p["left_id"], p["right_id"]):
            if eid not in cache:  # encode every entity only once
                cache[eid] = encode_entity(entities[eid])
        X.append(compare(cache[p["left_id"]], cache[p["right_id"]]))
        y.append(int(p["label"]))
    return np.array(X, dtype=np.float32), np.array(y)


def train(X, y):
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    clf = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=neg / max(pos, 1),
        eval_metric="logloss",
    )  # NaN is treated as "missing" by XGBoost, so no imputation is needed
    clf.fit(X, y)
    return clf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entities", required=True)
    ap.add_argument("--train-pairs", required=True)
    ap.add_argument("--out", default="xgb_model.json")
    args = ap.parse_args()

    entities = {e["id"]: e for e in json.load(open(args.entities, encoding="utf-8"))}
    pairs = json.load(open(args.train_pairs, encoding="utf-8"))

    X, y = make_dataset(pairs, entities)
    n_pos = int((y == 1).sum())
    print(f"{len(y)} training pairs, {n_pos} matches, {len(y) - n_pos} non-matches")
    if n_pos == 0 or n_pos == len(y):
        raise SystemExit("Training pairs need both matches (label 1) and non-matches (label 0).")

    clf = train(X, y)
    print("feature importance:", dict(zip(FEATURE_NAMES, clf.feature_importances_.round(3))))

    clf.save_model(args.out)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()