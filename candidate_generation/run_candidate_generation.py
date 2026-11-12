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

The methods compare place names only. With `--phonetic` the letter-based methods compare the
IPA encodings in the datasets (title_ipa) instead; LM_kNN_search keeps the names.
Coordinates are a second criterion: every method's candidates are also shown restricted to
places within each `--max-km` threshold (pairs where a record has no coordinates are kept).

  python run_candidate_generation.py                          # samples of all test sets, all methods
  python run_candidate_generation.py --full --max-km 10 25 50 100 250
  python run_candidate_generation.py --full --phonetic --methods Q_grams PassJoin MinHash_LSH TFIDF_kNN
  python run_candidate_generation.py --testset mehdie --methods PassJoin LM_kNN_search --show 3
"""
import argparse
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


# ---------------------------------------------------------------------------- running
def build_methods(args) -> list:
    """The blocking methods asked for with --methods, with their parameters set."""
    methods = [
        QGrams(q=3, t=0.6, max_keys=500),
        PassJoin(tau=args.tau),
        MinHashLSH(threshold=0.3),
        TfidfKNN(k=args.k),
        LMKNNSearch(model=args.model, k=args.k),
    ]
    by_name = {m.name: m for m in methods}
    return [by_name[name] for name in args.methods]


def run_testset(testset, methods, args):
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

    thresholds = [None, *args.max_km]

    # Upper bound set by the geo restriction alone: ground truth links it keeps at each threshold.
    n_truth = sum(len(g) for g in truth_by_pair.values())
    with_coords = sum(bool(by_name[s].coordinates[a] and by_name[t].coordinates[b])
                      for (s, t), g in truth_by_pair.items() for a, b in g)
    if n_truth:
        print(f"ground truth links with coordinates on both sides: {with_coords}/{n_truth}. Ground truth links "
              f"kept by the geo restriction alone: " + ", ".join(
                  f"{km:g} km {sum(len(within_distance(g, by_name[s], by_name[t], km)) for (s, t), g in truth_by_pair.items()) / n_truth:.3f}"
                  for km in args.max_km))

    print(f"{'method':14s} {'geo':>9s} {'pair':24s} {'truth':>5s} {'PC':>6s} {'PQ':>6s} {'RR':>7s} {'|C|':>10s} {'sec':>7s}",
          flush=True)
    for method in methods:
        m = method.name
        # max_km=None: each method runs once unrestricted, and the geo restriction is applied per
        # threshold below (the class default of 50 km would otherwise apply already).
        gen = CandidateGenerator(datasets, method, phonetic=args.phonetic, max_km=None)
        t0 = time.time()
        try:
            results = gen.all_pairs()
        except ImportError as e:
            print(f"{m:14s} skipped: {e}")
            continue
        seconds = f"{time.time() - t0:7.2f}"
        for km in thresholds:
            geo = "none" if km is None else f"{km:g} km"
            restricted = results if km is None else {(s, t): within_distance(c, by_name[s], by_name[t], km)
                                                     for (s, t), c in results.items()}
            for line in report(restricted, truth_by_pair, by_name, per_pair=args.per_pair or len(results) == 1):
                print(f"{m:14s} {geo:>9s} {line} {seconds}", flush=True)
                seconds = ""  # time only on the method's first line
            if args.show and km is None:
                for (s, t), cands in results.items():
                    for a, b in sorted(truth_by_pair[(s, t)] - cands)[: args.show]:
                        print(f"{'':24s} missed: {' / '.join(by_name[s].names[a][:4])}  <->  "
                              f"{' / '.join(by_name[t].names[b][:4])}")


def report(results, truth_by_pair, by_name, per_pair) -> list[str]:
    """Table lines: one per dataset pair (if per_pair), plus an ALL PAIRS total if there are several."""
    lines, found, n_cands, possible = [], 0, 0, 0
    for (s, t), cands in results.items():
        g = truth_by_pair[(s, t)]
        r = CandidateGenerator.evaluate(cands, g, len(by_name[s]), len(by_name[t]))
        if per_pair:
            pair = f"{by_name[s].label}-{by_name[t].label}"
            lines.append(f"{pair:24s} {row(len(g), r['PC'] if g else None, r['PQ'], r['RR'], len(cands))}")
        found, n_cands = found + len(cands & g), n_cands + len(cands)
        possible += len(by_name[s]) * len(by_name[t])
    if len(results) > 1:
        n_truth = sum(len(g) for g in truth_by_pair.values())
        lines.append(f"{'ALL PAIRS':24s} {row(n_truth, found / n_truth if n_truth else None, found / n_cands if n_cands else 0, 1 - n_cands / possible, n_cands)}")
    return lines


def row(n_truth, pc, pq, rr, n_cands) -> str:
    pc = f"{pc:6.3f}" if pc is not None else f"{'-':>6s}"  # "-" when a pair has no ground truth links
    return f"{n_truth:5d} {pc} {pq:6.3f} {rr:7.4f} {n_cands:10,d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", choices=[*TESTSETS, "all"], default="all")
    ap.add_argument("--methods", nargs="+", choices=ALL_METHODS, default=ALL_METHODS)
    ap.add_argument("--full", action="store_true", help="run on every record instead of a sample")
    ap.add_argument("--n-links", type=int, default=200, help="ground truth links to sample per test set")
    ap.add_argument("--n-distractors", type=int, default=300, help="extra unlinked records per dataset")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--tau", type=int, default=1, help="PassJoin edit-distance threshold")
    ap.add_argument("--k", type=int, default=3, help="neighbours per name for the kNN methods")
    ap.add_argument("--model", default="sentence-transformers/LaBSE", help="encoder for LM_kNN_search")
    ap.add_argument("--show", type=int, default=0, help="print N missed ground truth pairs per method and pair")
    ap.add_argument("--phonetic", action="store_true",
                    help="the letter-based methods compare the IPA encodings in the datasets (title_ipa) "
                         "instead of the names (LM_kNN_search keeps the names)")
    ap.add_argument("--max-km", nargs="*", type=float, default=[50],
                    help="geo restriction thresholds in km, e.g. --max-km 10 25 50 100 250 to compare "
                         "(no restriction is always shown too)")
    ap.add_argument("--per-pair", action="store_true", help="also show every dataset pair, not only the total")
    args = ap.parse_args()

    methods = build_methods(args)  # built once, so the language model is loaded only once
    for testset in (TESTSETS if args.testset == "all" else [args.testset]):
        run_testset(testset, methods, args)


if __name__ == "__main__":
    main()
