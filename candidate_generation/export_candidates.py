"""Writes the candidates of the pipeline (pipeline.py, default settings) to
datasets/03_candidate_generation/, one JSON file per pair of datasets:

  {"source": "Pleiades", "target": "Trismegistos",
   "candidates": {"<source id>": ["<target id>", ...], ...}}

Every source record is a key, in the order of its dataset; its candidates are sorted with the
best score first, and a record without candidates has an empty list. Read them back with
TestSetLoader().load_candidates(...) from data_loader.

  python export_candidates.py                       # all test sets
  python export_candidates.py --testset pleiades-tm
  python export_candidates.py --exclude Thurayya    # MEHDIE as Kima-Yaqut only
"""
import argparse
import json
import time
from pathlib import Path

from pipeline import TESTSETS, CandidatePipeline, TestSetLoader

from data_loader.candidates import candidates_path

DATASETS = Path(__file__).resolve().parents[1] / "datasets"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", choices=[*TESTSETS, "all"], default="all")
    ap.add_argument("--exclude", nargs="+", default=[], metavar="DATASET",
                    help="datasets to leave out, by label (e.g. Thurayya): no candidates are written for their pairs")
    args = ap.parse_args()

    for name in (TESTSETS if args.testset == "all" else [args.testset]):
        test_set = TestSetLoader().load(TESTSETS[name])
        test_set = test_set.without(*(d.name for d in test_set.datasets if d.label in args.exclude))
        pipeline = CandidatePipeline(test_set.datasets)
        for source, target in test_set.pairs:
            started = time.time()
            scores = pipeline.scored(source, target)
            candidates = {record_id: [] for record_id in test_set.dataset(source).ids}
            for (id_a, id_b), _ in sorted(scores.items(), key=lambda item: (-item[1], item[0])):
                candidates[id_a].append(id_b)
            path = candidates_path(DATASETS, source, target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"source": source.label, "target": target.label, "candidates": candidates},
                                       ensure_ascii=False, indent=1), encoding="utf8")
            truth = test_set.links_between(source, target)
            print(f"{path.relative_to(DATASETS)}: {len(scores):,} pairs, {len(truth & set(scores))} of "
                  f"{len(truth)} ground truth links, {time.time() - started:.0f} s", flush=True)


if __name__ == "__main__":
    main()
