"""Candidate generation (blocking) for cross-lingual toponym entity resolution.

Comparing every record in one gazetteer with every record in another is too expensive, so a
blocking method first picks the pairs that are worth comparing: the "candidates".

The CandidateGenerator holds the datasets (data_loader.Dataset) and does everything that is
the same for every method: taking the names of the records, turning name pairs into record
pairs, and the geo restriction. HOW names are compared is a BlockingMethod (the interface in
base/blocking_method.py); one of the methods in methods/ is injected into it:

  Q_grams        q_grams.py        key-based      names sharing most of their letter pieces
  PassJoin       pass_join.py      edit distance  names within `tau` letter edits (Levenshtein)
  MinHash_LSH    minhash_lsh.py    hashing        names whose letter pieces overlap (Jaccard)
  TFIDF_kNN      tfidf_knn.py      sparse kNN     each name's k most similar names by TF-IDF
  LM_kNN_search  lm_knn_search.py  neural kNN     each name's k most similar names by LaBSE embedding

The first four are letter-based. By default they compare the phonetic (IPA) encodings that are
in the datasets (title_ipa), so that names in different scripts become comparable; with
phonetic=False they compare the names instead. LM_kNN_search always compares the names as
written.

The two kNN methods share their neighbour search through the base class in base/knn_method.py.

  test_set = TestSetLoader().load(TestSetName.MEHDIE)
  CandidateGenerator(test_set.datasets, PassJoin(tau=1)).all_pairs()             # every pair of its datasets

  kima, yaqut = test_set.dataset(DatasetName.KIMA), test_set.dataset(DatasetName.YAQUT)
  CandidateGenerator([kima, yaqut], PassJoin(tau=1)).generate()                  # or just two of them

A method only gets what the candidate generator is allowed to use: the title of a record (not
its name variants) or the phonetic (IPA) encoding of the title. Coordinates are the first step:
with `max_km` set, only places at most that far apart can become candidates (geo filter). The
nearest-neighbour methods pick their k neighbours among the places that pass the filter; for
the other methods the filter is applied to their candidates, which gives the same result.

Needs the repo root on sys.path (for data_loader).
"""
import math
import re
import unicodedata
from itertools import combinations

import numpy as np

from base import BlockingMethod
from data_loader import Dataset, DatasetName


class CandidateGenerator:
    def __init__(self, datasets: list[Dataset], method: BlockingMethod, phonetic=True, max_km=100):
        """datasets:  two or more datasets.
        method:    the blocking method that compares the names.
        phonetic:  True (default) = the letter-based methods compare the phonetic (IPA)
                   encodings that are in the datasets; False = they compare the names. Methods
                   with raw_names, i.e. LM_kNN_search, always compare the names as written.
        max_km:   geo restriction: only keep candidate pairs at most this many km apart
                   (default 100: one common threshold for all test sets, it loses no ground
                   truth link in any of them, see results/EXPERIMENTS.md; None = no restriction).
                   Pairs where a record has no coordinates are always kept: distance cannot
                   rule them out."""
        self.datasets = {dataset.name: dataset for dataset in datasets}
        if len(self.datasets) != len(datasets):
            raise ValueError("Every dataset can only be given once.")
        self.method = method
        self.phonetic = phonetic
        self.max_km = max_km

    def generate(self, source: DatasetName = None, target: DatasetName = None) -> set:
        """Candidate pairs (source_id, target_id) between two of the datasets (both default to
        the only two there are). Names are compared one at a time and name pairs are turned into
        record pairs at the end."""
        A, B = self._pick(source, target)
        names_a, names_b = self._names(A), self._names(B)
        geo_first = self.max_km is not None and self.method.geo_first
        if geo_first:
            points_a = _points(A, [rid for rid, _ in names_a])
            points_b = _points(B, [rid for rid, _ in names_b])
            name_pairs = self.method.candidates(
                names_a, names_b,
                blocked=lambda start, stop: _distances(points_a[start:stop], points_b) > self.max_km)  # nan: kept
        else:
            name_pairs = self.method.candidates(names_a, names_b)
        pairs = {(a[0], b[0]) for a, b in name_pairs}  # ((id_a, n), (id_b, m)) -> (id_a, id_b)
        if self.max_km is None or geo_first:
            return pairs
        return within_distance(pairs, A, B, self.max_km)

    def all_pairs(self) -> dict:
        """Runs the method on every pair of datasets, so a test set can hold any number of them:
        {(source, target): candidate pairs}, keyed by DatasetName. With datasets [a, b, c] the
        pairs are (a, b), (a, c) and (b, c), in the order the datasets were given."""
        return {(s, t): self.generate(s, t) for s, t in combinations(self.datasets, 2)}

    @staticmethod
    def evaluate(candidates, ground_truth, n_source, n_target) -> dict:
        """PC = share of true matches that are candidates (recall).
        PQ = share of candidates that are true matches (precision).
        RR = share of all possible pairs that were NOT kept (how much work was saved)."""
        candidates, ground_truth = set(candidates), set(ground_truth)
        found = len(candidates & ground_truth)
        return {
            "PC": found / len(ground_truth) if ground_truth else 0.0,
            "PQ": found / len(candidates) if candidates else 0.0,
            "RR": 1 - len(candidates) / (n_source * n_target),
            "candidates": len(candidates),
        }

    # ================================================================ preparing the names
    def _pick(self, source, target) -> tuple[Dataset, Dataset]:
        if source is None and target is None:
            if len(self.datasets) != 2:
                raise ValueError("Pass source= and target=, or use all_pairs(), when there are "
                                 "not exactly two datasets.")
            source, target = self.datasets
        return self.datasets[source], self.datasets[target]

    def _names(self, dataset: Dataset) -> dict:
        """What the method compares, one entry per name: {(record_id, n): name}. The letter-based
        methods get the phonetic (IPA) encodings of the title, or the title when `phonetic` is
        off; a method with raw_names (LM_kNN_search) gets the title as written. Name variants
        are never used. A record has one title; it can have several IPA encodings of it
        (Trismegistos), which are compared one at a time."""
        raw = self.method.raw_names
        out = {}
        for record in dataset:
            # the main name comes first in record.names
            names = record.phonetic if self.phonetic and not raw else record.names[:1]
            names = [name.strip() if raw else self._normalize(name) for name in names]
            out.update({(record.id, i): name for i, name in enumerate(dict.fromkeys(x for x in names if x))})
        return out

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase, remove accents / Hebrew vowel points / Arabic short vowels and tatweel,
        replace punctuation with spaces. Does NOT transliterate between scripts."""
        s = unicodedata.normalize("NFKC", str(s)).casefold().replace("ـ", "")
        s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
        return " ".join(re.sub(r"[^\w\s]", " ", s).split())


# ==================================================================== geo restriction
def within_distance(pairs, source: Dataset, target: Dataset, max_km) -> set:
    """Keeps a candidate pair (source_id, target_id) only if the two places are at most max_km
    apart. If a record has several points, the closest two count. Pairs where a record has no
    coordinates are always kept."""
    kept = set()
    for a, b in pairs:
        points_a, points_b = source[a].coordinates, target[b].coordinates
        if not points_a or not points_b or min(_km(p, q) for p in points_a for q in points_b) <= max_km:
            kept.add((a, b))
    return kept


def _km(p, q) -> float:
    """Great-circle (haversine) distance in km between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*p, *q))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _points(dataset: Dataset, record_ids) -> np.ndarray:
    """[len(record_ids), max points per record, 2] in radians, nan where a record has fewer points."""
    coords = [dataset[rid].coordinates for rid in record_ids]
    out = np.full((len(coords), max(1, max(map(len, coords), default=1)), 2), np.nan)
    for r, points in enumerate(coords):
        if points:
            out[r, :len(points)] = points
    return np.radians(out)


def _distances(points_a, points_b) -> np.ndarray:
    """Haversine km between every row of a and of b (arrays from `_points`): the closest two
    points if a record has several, nan if either record has no coordinates."""
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
