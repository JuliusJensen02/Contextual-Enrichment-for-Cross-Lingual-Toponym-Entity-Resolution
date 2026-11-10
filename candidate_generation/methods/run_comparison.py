"""Run every blocker on the same data and print PC / PQ / RR.
  python run_comparison.py --demo
  python run_comparison.py --a A.json --b B.json --gold gold.json --name-attrs name alt
A.json / B.json: list of records, each with an "id". gold.json: list of [id_a, id_b]."""
import argparse
import json
import time

from blockers.common import collapse, evaluate, explode_names, serialize


def load_records(path):
    with open(path, encoding="utf8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a"); ap.add_argument("--b"); ap.add_argument("--gold")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--name-attrs", nargs="+", default=["name", "alt"],
                    help="attributes holding the place name(s); used by the character-level methods")
    ap.add_argument("--k", type=int, default=5, help="neighbours per record for dense methods")
    args = ap.parse_args()

    if args.demo:
        from demo_data import A as RA, B as RB, GOLD
    else:
        RA, RB = load_records(args.a), load_records(args.b)
        GOLD = [tuple(p) for p in load_records(args.gold)]
    gold = set(map(tuple, GOLD))

    full = lambda recs: {r["id"]: serialize(r) for r in recs}                      # all attrs, normalised
    variants = lambda recs: explode_names(recs, args.name_attrs)                    # one entry per name variant
    raw = lambda recs: {r["id"]: serialize(r, with_names=True, norm=False) for r in recs}  # for LM encoders

    methods = []   # (label, view, callable)
    from blockers.token_meta import token_meta_blocking
    from blockers.ext_qgrams import extended_qgrams_blocking
    from blockers.passjoin import passjoin
    methods += [
        ("4 token+purge+filter+meta(WNP)", full, lambda a, b: token_meta_blocking(a, b, filter_ratio=0.8)),
        ("6a plain q-grams (q=3)", variants, lambda a, b: collapse(extended_qgrams_blocking(a, b, q=3, t=None))),
        ("6b extended q-grams (t=0.6)", variants, lambda a, b: collapse(extended_qgrams_blocking(a, b, q=3, t=0.6, max_keys=500))),
        ("7 passjoin tau=2 (candidates)", variants, lambda a, b: collapse(passjoin(a, b, tau=2))),
    ]
    try:
        from blockers.minhash_lsh import minhash_lsh
        methods.append(("5 minhash-lsh (3-grams)", variants, lambda a, b: collapse(minhash_lsh(a, b, threshold=0.3))))
    except ImportError:
        print("skip method 5 (pip install datasketch)")
    try:
        from blockers.dense import dense_knn
        import faiss, sentence_transformers  # noqa: F401
        methods.append(("1 LaBSE + kNN", raw, lambda a, b: dense_knn(a, b, k=args.k)))
    except ImportError:
        print("skip method 1 (pip install sentence-transformers faiss-cpu)")

    print(f"{'method':34s} {'PC':>6s} {'PQ':>6s} {'RR':>6s} {'|C|':>7s} {'sec':>6s}")
    for label, view, fn in methods:
        a, b = view(RA), view(RB)
        t0 = time.time()
        cands = fn(a, b)
        dt = time.time() - t0
        m = evaluate(cands, gold, len(RA), len(RB))
        print(f"{label:34s} {m['PC']:6.3f} {m['PQ']:6.3f} {m['RR']:6.3f} {m['candidates']:7d} {dt:6.2f}")


if __name__ == "__main__":
    main()
