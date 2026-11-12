"""Candidate generation (blocking) for cross-lingual toponym entity resolution.

Comparing every record in one gazetteer with every record in another is too expensive, so a
blocking method first picks the pairs that are worth comparing: the "candidates".

The CandidateGenerator holds the datasets and does everything that is the same for every
method: picking the names out of the records, turning name pairs into record pairs, and the geo
restriction. HOW names are compared is a BlockingMethod (the interface in
base/blocking_method.py); one of the methods in methods/ is injected into it:

  Q_grams        q_grams.py        key-based      names sharing most of their letter pieces
  PassJoin       pass_join.py      edit distance  names within `tau` letter edits (Levenshtein)
  MinHash_LSH    minhash_lsh.py    hashing        names whose letter pieces overlap (Jaccard)
  TFIDF_kNN      tfidf_knn.py      sparse kNN     each name's k most similar names by TF-IDF
  LM_kNN_search  lm_knn_search.py  neural kNN     each name's k most similar names by LaBSE embedding

The two kNN methods share their neighbour search through the base class in base/knn_method.py.

  CandidateGenerator(datasets, PassJoin(tau=1)).generate()

Every method looks at the toponym NAMES only. Coordinates are a second, separate criterion:
with `max_km` set, the candidates are also restricted to places at most that far apart (geo
blocking, see `within_distance`).
"""
import math
import re
import unicodedata
from itertools import combinations

from base import BlockingMethod


class CandidateGenerator:
    def __init__(self, datasets: dict[str, dict], method: BlockingMethod, name_attrs=("name", "alt"),
                 phonetic_attrs=None, max_km=50, coords_attr="coords", keep_without_coords=True):
        """datasets:       {dataset_name: {record_id: record}}, two or more datasets. A record is a
                           dict of strings or lists of strings, plus optional coordinates, e.g.
                           {"name": "Antakya", "alt": ["Antioch"], "phonetic": ["ntk", "nts"],
                            "coords": [(36.2, 36.16)]}.
        method:         the blocking method that compares the names.
        name_attrs:     the attributes that hold the record's place names.
        phonetic_attrs: the attributes that hold phonetic encodings of the names. When given,
                        the letter-based methods compare these instead of the names (methods
                        with raw_names, i.e. LM_kNN_search, always get the names).
        max_km:         geo restriction: only keep candidate pairs at most this many km apart
                        (default 50: the smallest threshold that lost no ground truth links on
                        the Pleiades-TM and MEHDIE samples; None = no restriction).
        coords_attr:    the attribute holding a record's (lat, lon) points; a list, because a
                        record can have several.
        keep_without_coords: keep pairs where a record has no coordinates (distance cannot rule
                        them out). False drops them."""
        self.datasets = datasets
        self.method = method
        self.name_attrs = list(name_attrs)
        self.phonetic_attrs = list(phonetic_attrs) if phonetic_attrs else None
        self.max_km = max_km
        self.coords_attr = coords_attr
        self.keep_without_coords = keep_without_coords

    def generate(self, source=None, target=None) -> set:
        """Candidate pairs (source_id, target_id) between two datasets, given by name (both
        default to the only two there are). Names are compared one at a time and name pairs are
        turned into record pairs at the end."""
        A, B = self._pick(source, target)
        name_pairs = self.method.candidates(self._names(A), self._names(B))
        pairs = {(a[0], b[0]) for a, b in name_pairs}  # ((id_a, n), (id_b, m)) -> (id_a, id_b)
        if self.max_km is None:
            return pairs
        return within_distance(pairs, A, B, self.max_km, self.coords_attr, self.keep_without_coords)

    def all_pairs(self) -> dict:
        """Runs the method on every pair of datasets, so a test set can hold any number of them:
        {(source, target): candidate pairs}. With datasets [a, b, c] the pairs are (a, b),
        (a, c) and (b, c), in the order the datasets were given."""
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
    def _pick(self, source, target) -> tuple[dict, dict]:
        if source is None and target is None:
            if len(self.datasets) != 2:
                raise ValueError("Pass source= and target=, or use all_pairs(), when there are "
                                 "not exactly two datasets.")
            source, target = self.datasets
        return self.datasets[source], self.datasets[target]

    def _names(self, records: dict) -> dict:
        """What the method compares, one entry per name: {(record_id, n): name}. Names are
        compared one at a time, not all of a record's names glued together."""
        raw = self.method.raw_names
        attrs = self.name_attrs if raw else self.phonetic_attrs or self.name_attrs
        out = {}
        for rid, r in records.items():
            names = []
            for attr in attrs:
                value = r.get(attr)
                names += value if isinstance(value, (list, tuple)) else [value]
            names = [str(n).strip() if raw else self._normalize(n) for n in names if n]
            out.update({(rid, i): name for i, name in enumerate(dict.fromkeys(x for x in names if x))})
        return out

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase, remove accents / Hebrew vowel points / Arabic short vowels and tatweel,
        replace punctuation with spaces. Does NOT transliterate between scripts."""
        s = unicodedata.normalize("NFKC", str(s)).casefold().replace("ـ", "")
        s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
        return " ".join(re.sub(r"[^\w\s]", " ", s).split())


# ==================================================================== geo restriction
def within_distance(pairs, source: dict, target: dict, max_km, coords_attr="coords",
                    keep_without_coords=True) -> set:
    """Keeps a candidate pair only if the two places are at most max_km apart. source, target:
    the two datasets' {record_id: record}. If a record has several points, the closest two
    count. Pairs where a record has no coordinates are kept if keep_without_coords is True."""
    kept = set()
    for a, b in pairs:
        points_a, points_b = source[a].get(coords_attr), target[b].get(coords_attr)
        if not points_a or not points_b:
            if keep_without_coords:
                kept.add((a, b))
        elif min(_km(p, q) for p in points_a for q in points_b) <= max_km:
            kept.add((a, b))
    return kept


def _km(p, q) -> float:
    """Great-circle (haversine) distance in km between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*p, *q))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))
