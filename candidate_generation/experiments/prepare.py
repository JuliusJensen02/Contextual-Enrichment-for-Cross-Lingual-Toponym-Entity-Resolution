"""Computes once what every combination run needs: the LaBSE embedding of every title and the
geo filter of every pair of datasets.

  python experiments/prepare.py --testset mehdie
"""
import argparse

import numpy as np

from common import CACHE, CHUNK, MAX_KM, embedding_path, far_path, load
from methods import LMKNNSearch
from pipeline import _distances, _points


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", required=True)
    ap.add_argument("--max-km", type=float, default=MAX_KM)
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    test_set = load(args.testset)

    for source, target in test_set.pairs:
        A, B = test_set.dataset(source), test_set.dataset(target)
        points_a, points_b = _points(A), _points(B)
        out = np.lib.format.open_memmap(far_path(args.testset, source, target, args.max_km), mode="w+",
                                        dtype=bool, shape=(len(A), len(B)))
        for c in range(0, len(A), CHUNK):
            out[c:c + CHUNK] = _distances(points_a[c:c + CHUNK], points_b) > args.max_km  # nan: False
        out.flush()
        print(f"geo filter {A.label}-{B.label}: {int(np.count_nonzero(out)):,} of {out.size:,} pairs ruled out",
              flush=True)

    encoder = LMKNNSearch()
    for dataset in test_set.datasets:
        titles = [title.strip() for title in dataset.frame["title"]]  # as pipeline.py embeds them
        np.save(embedding_path(args.testset, dataset), encoder._embed(titles))
        print(f"embedded {dataset.label}: {len(titles):,} titles", flush=True)


if __name__ == "__main__":
    main()
