
"""
Tune the XGBoost matcher: try several settings, and for each one find the decision threshold
that maximises F-beta (F5 by default) on the VALIDATION pairs. Keeps the best model.
"""

import argparse
import json
import random

import numpy as np
from sklearn.metrics import roc_auc_score

if __package__:
    from .train_gradientboost import make_dataset, train
else:
    from train_gradientboost import make_dataset, train


SEARCH_SPACE = {
    "max_depth": [2, 3, 4, 5, 6],
    "learning_rate": [0.02, 0.05, 0.1],
    "n_estimators": [100, 300, 600],
    "min_child_weight": [1, 3, 5],
    "subsample": [0.7, 1.0],
    "colsample_bytree": [0.7, 1.0],
    "reg_lambda": [1, 5, 10],
}


def f_beta(y, pred, beta):
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())

    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0

    b2 = beta ** 2
    f = (1 + b2) * p * r / (b2 * p + r) if b2 * p + r else 0.0

    return p, r, f


def tune_threshold(y, probs, beta):
    """Find the threshold with the best F-beta score."""
    best_t, best_f = 0.5, -1.0

    for t in np.unique(probs):
        predictions = (probs >= t).astype(int)
        f = f_beta(y, predictions, beta)[2]

        if f > best_f:
            best_t, best_f = float(t), f # Ties retain the lower threshold, favouring recall.

    return best_t


def sample_settings(n, seed):
    """Generate n unique random hyperparameter configurations."""
    rng = random.Random(seed)

    seen = set()
    out = []

    total_combinations = np.prod([len(v) for v in SEARCH_SPACE.values()])

    if n > total_combinations:
        raise ValueError(
            f"Requested {n} trials, but only {total_combinations} "
            "unique configurations exist."
        )

    while len(out) < n:
        params = {k: rng.choice(v) for k, v in SEARCH_SPACE.items()}
        key = tuple(sorted(params.items()))

        if key not in seen:
            seen.add(key)
            out.append(params)

    return out


def tune(X_tr, y_tr, X_va, y_va, trials=30, beta=5.0, seed=42, verbose=True):
    """
    Try the default settings plus random configurations.

    Returns the best model, threshold, parameters and validation metrics.
    """

    if beta <= 0:
        raise ValueError("Beta must be greater than zero.")

    for name, y in (("training", y_tr), ("validation", y_va)):
        if len(y) == 0 or y.min() == y.max():
            raise ValueError(
                f"The {name} pairs need both matches and non-matches."
            )

    settings = [{}] + sample_settings(trials, seed)

    rows = []
    best = None

    for i, params in enumerate(settings):

        # Set the XGBoost random seed for reproducibility.
        clf = train(X_tr, y_tr, random_state=seed, **params)

        probs = clf.predict_proba(X_va)[:, 1]

        # Select the threshold using validation data.
        threshold = tune_threshold(y_va, probs, beta)

        predictions = (probs >= threshold).astype(int)
        p, r, f = f_beta(y_va, predictions, beta)

        # Calculate ROC-AUC using scikit-learn.
        auc = roc_auc_score(y_va, probs)

        row = {
            "params": params,
            "threshold": threshold,
            "precision": p,
            "recall": r,
            "f": f,
            "auc": auc,
        }

        rows.append(row)

        if verbose:
            print(
                f"  [{i:3d}/{len(settings) - 1}] "
                f"F{beta:g} {f:.3f}  "
                f"AUC {auc:.3f}  "
                f"{'default' if not params else params}"
            )

        # Prefer higher F-beta, then higher ROC-AUC in case of a tie.
        if best is None or (f, auc) > (best["f"], best["auc"]):
            best = {**row, "clf": clf}

    best["default_f"] = rows[0]["f"]
    best["rows"] = rows

    if verbose:
        print(
            f"\nBest: F{beta:g} {best['f']:.3f} "
            f"on validation "
            f"(default settings: {best['default_f']:.3f})"
        )

        print(
            f"      threshold {best['threshold']:.4f}, "
            f"precision {best['precision']:.3f}, "
            f"recall {best['recall']:.3f}, "
            f"settings {best['params'] or 'default'}"
        )

        print(
            "Note: The settings and threshold were both selected "
            "using validation data, so this score is optimistic."
        )

    return best


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--entities", required=True)
    ap.add_argument("--train-pairs", required=True)
    ap.add_argument("--val-pairs", required=True)
    ap.add_argument("--out", default="xgb_model.json")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--beta", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=42)

    args = ap.parse_args()

    # Set NumPy and Python random seeds.
    random.seed(args.seed)
    np.random.seed(args.seed)

    load = lambda path: json.load(open(path, encoding="utf-8"))

    entities = {e["id"]: e for e in load(args.entities)}

    # Encoding is the slow step, so it happens once.
    print("Encoding training and validation pairs ...")

    X_tr, y_tr = make_dataset(load(args.train_pairs), entities)
    X_va, y_va = make_dataset(load(args.val_pairs), entities)

    print(
        f"  train: {len(y_tr)} pairs "
        f"({int(y_tr.sum())} matches), "
        f"val: {len(y_va)} pairs "
        f"({int(y_va.sum())} matches)"
    )

    result = tune(
        X_tr,
        y_tr,
        X_va,
        y_va,
        trials=args.trials,
        beta=args.beta,
        seed=args.seed,
    )

    # Save the best model.
    result["clf"].save_model(args.out)

    # Save its selected threshold and hyperparameters.
    with open(
        args.out + ".threshold.json",
        "w",
        encoding="utf-8"
    ) as fh:
        json.dump(
            {
                "threshold": result["threshold"],
                "beta": args.beta,
                "params": result["params"],
                "seed": args.seed,
            },
            fh,
            indent=2,
        )

    print(f"Saved {args.out} and {args.out}.threshold.json")


if __name__ == "__main__":
    main()
