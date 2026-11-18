"""Run the blocking methods on our test sets and print PC / PQ / RR.

A test set is any number of datasets plus ground truth links between them. Every method is run
on every pair of datasets in the test set and scored per pair and in total.

Test sets, loaded through data_loader (the minimized datasets + their ground truth links):
  pleiades-tm  Pleiades (Greek), Trismegistos (Latin)   TestSetName.PLEIADES_TRISMEGISTOS
  mehdie       Kima, Yaqut, al-Thurayya                 TestSetName.MEHDIE
  zh-ru        Wikidata Chinese, Russian                TestSetName.WIKIDATA_ZH_RU

By default each run samples `--n-links` ground truth links, takes their records, and adds
`--n-distractors` random records without a link per dataset so the methods have something to
reject. Every link whose two records both ended up in the sample counts. `--full` skips the
sampling and runs on every record.

What the letter-based methods (Q_grams, PassJoin, MinHash_LSH, TFIDF_kNN) compare is set with
`--phonetic`: `on` (default) = the IPA encodings in the datasets (title_ipa), `off` = the names,
`both` = one run of each. LM_kNN_search always compares the titles as written. Only the title of
a record is used, never its name variants.
Coordinates are the first step: every method runs behind a geo filter of `--max-km` (default
100; several values = one run of each; `--max-km` without a value = no geo filter). Pairs where
a record has no coordinates always pass the filter.

Every method parameter takes one or several values; each value is run and reported separately.
`--out FILE.csv` also saves the table, one row per run.

  python run_candidate_generation.py                          # samples of all test sets, all methods
  python run_candidate_generation.py --full --max-km 10 25 50 100 250
  python run_candidate_generation.py --full --phonetic both --tau 0 1 2 --k 1 3 5 10 --out results.csv
  python run_candidate_generation.py --testset mehdie --methods PassJoin LM_kNN_search --show 3
"""
import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # the repo root, for data_loader

from candidate_generator import CandidateGenerator, within_distance  # noqa: E402
from data_loader import TestSet, TestSetLoader, TestSetName  # noqa: E402
from methods import LMKNNSearch, MinHashLSH, PassJoin, QGrams, TfidfKNN  # noqa: E402

LOADER = TestSetLoader()

ALL_METHODS = ["Q_grams", "PassJoin", "MinHash_LSH", "TFIDF_kNN", "LM_kNN_search"]

TESTSETS = {"pleiades-tm": TestSetName.PLEIADES_TRISMEGISTOS, "mehdie": TestSetName.MEHDIE,
            "zh-ru": TestSetName.WIKIDATA_ZH_RU}

CSV_COLUMNS = ["testset", "pair", "method", "params", "input", "max_km", "truth", "PC", "PQ", "RR",
               "candidates", "seconds"]


# ---------------------------------------------------------------------------- running
def build_methods(args) -> list[tuple]:
    """(method, its parameters as text) for every method asked for with --methods and every
    value given for its parameter."""
    built = {
        "Q_grams": [(QGrams(q=q, t=t, max_keys=keys), f"q={q},t={t:g}" + (f",keys={keys}" if keys != 500 else ""))
                    for q in args.qgram_q for t in args.qgram_t for keys in args.qgram_max_keys],
        "PassJoin": [(PassJoin(tau=tau), f"tau={tau}") for tau in args.tau],
        "MinHash_LSH": [(MinHashLSH(n=n, num_perm=perm, threshold=thr),
                         f"n={n},thr={thr:g}" + (f",perm={perm}" if perm != 128 else ""))
                        for n in args.minhash_n for thr in args.minhash_threshold for perm in args.minhash_num_perm],
        "TFIDF_kNN": [(TfidfKNN(k=k, ngram_range=tuple(map(int, grams.split("-")))),
                       f"k={k}" + (f",n={grams}" if grams != "2-3" else ""))
                      for grams in args.tfidf_ngrams for k in args.k],
        "LM_kNN_search": [(LMKNNSearch(model=args.model, k=k), f"k={k}") for k in args.k],
    }
    return [run for name in args.methods for run in built[name]]


def inputs_for(method, phonetic: str) -> list[str]:
    """What the method compares in each of its runs: "ipa" and/or "names"."""
    if method.raw_names:
        return ["names"]
    return {"on": ["ipa"], "off": ["names"], "both": ["ipa", "names"]}[phonetic]


def run_testset(testset, methods, args, writer):
    test_set: TestSet = LOADER.load(TESTSETS[testset])
    if not args.full:
        test_set = test_set.sample(args.n_links, args.n_distractors, args.seed)
    datasets = test_set.datasets
    by_name = {dataset.name: dataset for dataset in datasets}
    truth_by_pair = {pair: test_set.links_between(*pair) for pair in test_set.pairs}
    sizes = ", ".join(f"{dataset.label} {len(dataset)}" for dataset in datasets)
    print()
    print(f"=== {testset}: {sizes} records; {len(test_set.links)} ground truth links; "
          f"{len(test_set.pairs)} dataset pair(s)")

    thresholds = args.max_km or [None]

    # Upper bound set by the geo restriction alone: ground truth links it keeps at each threshold.
    n_truth = sum(len(g) for g in truth_by_pair.values())
    with_coords = sum(bool(by_name[s][a].coordinates and by_name[t][b].coordinates)
                      for (s, t), g in truth_by_pair.items() for a, b in g)
    if n_truth:
        print(f"ground truth links with coordinates on both sides: {with_coords}/{n_truth}. Ground truth links "
              f"kept by the geo restriction alone: " + ", ".join(
                  f"{km:g} km {sum(len(within_distance(g, by_name[s], by_name[t], km)) for (s, t), g in truth_by_pair.items()) / n_truth:.3f}"
                  for km in args.max_km))

    print(f"{'method':14s} {'params':20s} {'input':5s} {'geo':>9s} {'pair':24s} {'truth':>5s} {'PC':>6s} {'PQ':>6s} "
          f"{'RR':>7s} {'|C|':>10s} {'sec':>7s}", flush=True)
    for method, params in methods:
        for compared in inputs_for(method, args.phonetic):
            label = f"{method.name:14s} {params:20s} {compared:5s}"
            for km in thresholds:
                geo = "none" if km is None else f"{km:g} km"
                gen = CandidateGenerator(datasets, method, phonetic=compared == "ipa", max_km=km)
                t0 = time.time()
                try:
                    results = gen.all_pairs()
                except (ImportError, MemoryError) as e:
                    print(f"{label} skipped: {type(e).__name__} {e}", flush=True)
                    break
                seconds = round(time.time() - t0, 2)
                for r in report(results, truth_by_pair, by_name, per_pair=args.per_pair or len(results) == 1):
                    pc = f"{r['PC']:6.3f}" if r["PC"] is not None else f"{'-':>6s}"  # "-": no ground truth links
                    print(f"{label} {geo:>9s} {r['pair']:24s} {r['truth']:5d} {pc} {r['PQ']:6.3f} {r['RR']:7.4f} "
                          f"{r['candidates']:10,d} {seconds:7.2f}", flush=True)
                    if writer:
                        writer.writerow({**r, "testset": testset, "method": method.name, "params": params,
                                         "input": compared, "max_km": "" if km is None else f"{km:g}",
                                         "PC": "" if r["PC"] is None else round(r["PC"], 4), "PQ": round(r["PQ"], 4),
                                         "RR": round(r["RR"], 6), "seconds": seconds})
                if args.show:
                    for (s, t), cands in results.items():
                        for a, b in sorted(truth_by_pair[(s, t)] - cands)[: args.show]:
                            print(f"{'':24s} missed: {by_name[s][a].names[0]}  <->  {by_name[t][b].names[0]}")


def report(results, truth_by_pair, by_name, per_pair) -> list[dict]:
    """Table rows: one per dataset pair (if per_pair), plus an ALL PAIRS total if there are several."""
    rows, found, n_cands, possible = [], 0, 0, 0
    for (s, t), cands in results.items():
        g = truth_by_pair[(s, t)]
        r = CandidateGenerator.evaluate(cands, g, len(by_name[s]), len(by_name[t]))
        if per_pair:
            rows.append({"pair": f"{by_name[s].label}-{by_name[t].label}", "truth": len(g),
                         "PC": r["PC"] if g else None, "PQ": r["PQ"], "RR": r["RR"], "candidates": len(cands)})
        found, n_cands = found + len(cands & g), n_cands + len(cands)
        possible += len(by_name[s]) * len(by_name[t])
    if len(results) > 1:
        n_truth = sum(len(g) for g in truth_by_pair.values())
        rows.append({"pair": "ALL PAIRS", "truth": n_truth, "PC": found / n_truth if n_truth else None,
                     "PQ": found / n_cands if n_cands else 0, "RR": 1 - n_cands / possible, "candidates": n_cands})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", choices=[*TESTSETS, "all"], default="all")
    ap.add_argument("--methods", nargs="+", choices=ALL_METHODS, default=ALL_METHODS)
    ap.add_argument("--full", action="store_true", help="run on every record instead of a sample")
    ap.add_argument("--n-links", type=int, default=200, help="ground truth links to sample per test set")
    ap.add_argument("--n-distractors", type=int, default=300, help="extra unlinked records per dataset")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--phonetic", choices=["on", "off", "both"], default="on",
                    help="what the letter-based methods compare: on = the IPA encodings in the datasets "
                         "(title_ipa), off = the names, both = one run of each (LM_kNN_search always uses the names)")
    ap.add_argument("--tau", nargs="+", type=int, default=[1],
                    help="PassJoin: edit-distance threshold(s); 0 = identical names only")
    ap.add_argument("--k", nargs="+", type=int, default=[3], help="kNN methods: neighbours per name")
    ap.add_argument("--minhash-threshold", nargs="+", type=float, default=[0.3],
                    help="MinHash_LSH: Jaccard similarity threshold(s)")
    ap.add_argument("--tfidf-ngrams", nargs="+", default=["2-3"], metavar="MIN-MAX",
                    help="TFIDF_kNN: range(s) of letter piece lengths, e.g. 1-2 2-3 3-3")
    ap.add_argument("--minhash-num-perm", nargs="+", type=int, default=[128],
                    help="MinHash_LSH: signature size(s); larger = more exact overlap estimate")
    ap.add_argument("--qgram-max-keys", nargs="+", type=int, default=[500], help="Q_grams: cap(s) on the keys per name")
    ap.add_argument("--minhash-n", nargs="+", type=int, default=[3], help="MinHash_LSH: length(s) of the letter pieces")
    ap.add_argument("--qgram-q", nargs="+", type=int, default=[3], help="Q_grams: length(s) of the letter pieces")
    ap.add_argument("--qgram-t", nargs="+", type=float, default=[0.6],
                    help="Q_grams: share(s) of a name's q-grams a key must contain")
    ap.add_argument("--model", default="sentence-transformers/LaBSE", help="encoder for LM_kNN_search")
    ap.add_argument("--max-km", nargs="*", type=float, default=[100],
                    help="geo filter in km, applied first; several values = one run of each, "
                         "no value = no geo filter")
    ap.add_argument("--per-pair", action="store_true", help="also show every dataset pair, not only the total")
    ap.add_argument("--show", type=int, default=0, help="print N missed ground truth pairs per method and pair")
    ap.add_argument("--out", metavar="FILE.csv", help="also save the table here, one row per run")
    args = ap.parse_args()

    methods = build_methods(args)  # built once, so the language model is loaded only once
    out = open(args.out, "w", encoding="utf8", newline="") if args.out else None
    writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS) if out else None
    if writer:
        writer.writeheader()
    try:
        for testset in (TESTSETS if args.testset == "all" else [args.testset]):
            run_testset(testset, methods, args, writer)
            if out:
                out.flush()
    finally:
        if out:
            out.close()


if __name__ == "__main__":
    main()
