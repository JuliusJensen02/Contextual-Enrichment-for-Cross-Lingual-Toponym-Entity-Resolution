"""The candidate generation pipeline chosen by the experiments in results/EXPERIMENTS.md.

It uses only the title, the phonetic title (title_ipa) and the coordinates of a record:

  1. Geo filter   pairs more than `max_km` (100) apart are dropped. Pairs where a record has no
                  coordinates are always kept.
  2. Score        title_weight * title similarity + (1 - title_weight) * phonetic similarity
                    title similarity     cosine of the LaBSE embeddings of the two titles
                    phonetic similarity  TF-IDF cosine on the letter 2- and 3-grams of title_ipa
  3. Top k        every record keeps its k best-scoring records on the other side that passed
                  the geo filter. A pair is a candidate if either side keeps it (union).

  test_set = TestSetLoader().load(TestSetName.MEHDIE)
  CandidatePipeline(test_set.datasets).all_pairs()      # {(source, target): {(id_a, id_b), ...}}

  python pipeline.py                        # all test sets, full data: PC / PQ / RR / |C|
  python pipeline.py --testset zh-ru --k 3 10

Needs the repo root on sys.path (for data_loader), scikit-learn and sentence-transformers.
"""
import argparse
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.append(str(Path(__file__).resolve().parents[1]))  # the repo root, for data_loader

from data_loader import Dataset, DatasetName, TestSetLoader, TestSetName  # noqa: E402
from methods import LMKNNSearch  # noqa: E402

CHUNK = 1000  # source records scored at a time (keeps memory at CHUNK x target records)


class CandidatePipeline:
    def __init__(self, datasets: list[Dataset], k=5, title_weight=0.5, max_km=100,
                 model="sentence-transformers/LaBSE"):
        """k:            records kept per record (default 5).
        title_weight: share of the title similarity in the score; the rest is the phonetic
                      similarity (default 0.5: the two count equally).
        max_km:       geo filter in km (default 100, common to all test sets)."""
        self.datasets = {dataset.name: dataset for dataset in datasets}
        self.k, self.title_weight, self.max_km = k, title_weight, max_km
        self._encoder = LMKNNSearch(model=model)

    def all_pairs(self) -> dict:
        """{(source, target): candidate pairs} for every pair of the datasets."""
        return {(s, t): self.generate(s, t) for s, t in combinations(self.datasets, 2)}

    def generate(self, source: DatasetName = None, target: DatasetName = None) -> set:
        """Candidate pairs (source_id, target_id) between two of the datasets (both default to
        the only two there are)."""
        if source is None and target is None:
            source, target = self.datasets
        A, B = self.datasets[source], self.datasets[target]
        ids_a, ids_b = A.ids, B.ids
        k_rows, k_cols = min(self.k, len(ids_b)), min(self.k, len(ids_a))

        title_a, title_b = (self._encoder._embed([t.strip() for t in d.frame["title"]]) for d in (A, B))
        ipa_a, ipa_b = ([(d.phonetic[i] or [""])[0].lower() for i in d.ids] for d in (A, B))
        tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3)).fit(ipa_a + ipa_b)
        phon_a, phon_b = tfidf.transform(ipa_a), tfidf.transform(ipa_b).T.tocsr()
        points_a, points_b = _points(A), _points(B)

        pairs = set()
        best_score = np.full((0, len(ids_b)), -np.inf, dtype=np.float32)  # per target record: its
        best_row = np.zeros((0, len(ids_b)), dtype=np.int64)              # k best source records so far
        w = np.float32(self.title_weight)
        for c in range(0, len(ids_a), CHUNK):
            score = w * (title_a[c:c + CHUNK] @ title_b.T) + (1 - w) * (phon_a[c:c + CHUNK] @ phon_b).toarray()
            score[_distances(points_a[c:c + CHUNK], points_b) > self.max_km] = -np.inf  # nan: kept
            # each source record's k best target records
            top = np.argpartition(-score, k_rows - 1, axis=1)[:, :k_rows]
            for i, js in enumerate(top):
                pairs.update((ids_a[c + i], ids_b[j]) for j in js if score[i, j] > 0)
            # each target record's k best source records: merge this chunk into the best so far
            rows = np.arange(c, c + len(score))[:, None].repeat(len(ids_b), 1)
            best_score, best_row = np.vstack([best_score, score]), np.vstack([best_row, rows])
            keep = np.argpartition(-best_score, k_cols - 1, axis=0)[:k_cols]
            best_score = np.take_along_axis(best_score, keep, 0)
            best_row = np.take_along_axis(best_row, keep, 0)
        for j in range(len(ids_b)):
            pairs.update((ids_a[i], ids_b[j]) for s, i in zip(best_score[:, j], best_row[:, j]) if s > 0)
        return pairs


# ============================================================================ geo filter
def _points(dataset: Dataset) -> np.ndarray:
    """[records, max points per record, 2] in radians, nan where a record has fewer points."""
    coords = [dataset.coordinates[i] for i in dataset.ids]
    out = np.full((len(coords), max(1, max(map(len, coords))), 2), np.nan)
    for r, points in enumerate(coords):
        if points:
            out[r, :len(points)] = points
    return np.radians(out)


def _distances(points_a, points_b) -> np.ndarray:
    """Great-circle (haversine) km between every record of a and of b: the closest two points
    if a record has several, nan if either record has no coordinates."""
    best = np.full((points_a.shape[0], points_b.shape[0]), np.nan, dtype=np.float32)
    for i in range(points_a.shape[1]):
        for j in range(points_b.shape[1]):
            p, q = points_a[:, None, i], points_b[None, :, j]
            if np.isnan(p[..., 0]).all() or np.isnan(q[..., 0]).all():
                continue
            h = (np.sin((q[..., 0] - p[..., 0]) / 2) ** 2
                 + np.cos(p[..., 0]) * np.cos(q[..., 0]) * np.sin((q[..., 1] - p[..., 1]) / 2) ** 2)
            best = np.fmin(best, 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(h, 0, 1))))
    return best


# ============================================================================ running it
TESTSETS = {"pleiades-tm": TestSetName.PLEIADES_TRISMEGISTOS, "mehdie": TestSetName.MEHDIE,
            "zh-ru": TestSetName.WIKIDATA_ZH_RU}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", choices=[*TESTSETS, "all"], default="all")
    ap.add_argument("--k", nargs="+", type=int, default=[5], help="records kept per record")
    ap.add_argument("--title-weight", nargs="+", type=float, default=[0.5],
                    help="share of the title similarity in the score (the rest is phonetic)")
    ap.add_argument("--max-km", type=float, default=100, help="geo filter in km")
    args = ap.parse_args()

    print(f"{'test set':12s} {'k':>3s} {'weight':>6s} {'truth':>5s} {'PC':>6s} {'PQ':>8s} {'RR':>8s} {'|C|':>10s} {'sec':>6s}")
    for name in (TESTSETS if args.testset == "all" else [args.testset]):
        test_set = TestSetLoader().load(TESTSETS[name])
        sizes = {d.name: len(d) for d in test_set.datasets}
        for weight in args.title_weight:
            for k in args.k:
                t0 = time.time()
                results = CandidatePipeline(test_set.datasets, k, weight, args.max_km).all_pairs()
                truth = sum(len(test_set.links_between(s, t)) for s, t in results)
                found = sum(len(c & test_set.links_between(s, t)) for (s, t), c in results.items())
                n = sum(map(len, results.values()))
                possible = sum(sizes[s] * sizes[t] for s, t in results)
                print(f"{name:12s} {k:3d} {weight:6.2f} {truth:5d} {found / truth:6.3f} {found / n:8.5f} "
                      f"{1 - n / possible:8.5f} {n:10,d} {time.time() - t0:6.0f}", flush=True)


if __name__ == "__main__":
    main()
