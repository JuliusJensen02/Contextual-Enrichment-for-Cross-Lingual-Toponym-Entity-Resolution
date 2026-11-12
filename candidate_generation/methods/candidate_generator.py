"""Candidate generation (blocking) for cross-lingual toponym entity resolution.

Comparing every record in one gazetteer with every record in another is too expensive, so a
blocking method first picks the pairs that are worth comparing: the "candidates".
Every method here looks at the toponym NAMES only. Coordinates are a second, separate criterion:
with `max_km` set, every method's candidates are also restricted to places at most that far
apart (geo blocking, see `within_distance`).

Methods, by family:
  Q_grams        key-based     names sharing most of their letter pieces (Extended Q-Grams)
  PassJoin       edit distance names within `tau` letter edits (Levenshtein)
  MinHash_LSH    hashing       names whose letter pieces overlap (Jaccard), via MinHash + LSH
  TFIDF_kNN      sparse kNN    each name's k most similar names by TF-IDF letter pieces
  LM_kNN_search  neural kNN    each name's k most similar names by LaBSE embedding (cross-script)

Optional dependencies, imported only by the methods that need them:
scikit-learn (TFIDF_kNN, LM_kNN_search), sentence-transformers (LM_kNN_search),
datasketch (MinHash_LSH).
"""
import functools
import math
import re
import unicodedata
from collections import defaultdict
from itertools import combinations, product


def _geo_restricted(method):
    """Applies the geo restriction (when max_km is set) to everything a method returns."""
    @functools.wraps(method)
    def wrapper(self, source=None, target=None, **kwargs):
        pairs = method(self, source, target, **kwargs)
        return pairs if self.max_km is None else self.within_distance(pairs, source, target)
    return wrapper


class CandidateGenerator:
    def __init__(self, datasets: dict[str, dict], name_attrs=("name", "alt"), phonetic_attrs=None,
                 max_km=50, coords_attr="coords", keep_without_coords=True):
        """datasets:       {dataset_name: {record_id: record}}, two or more datasets. A record is a
                           dict of strings or lists of strings, plus optional coordinates, e.g.
                           {"name": "Antakya", "alt": ["Antioch"], "phonetic": ["ntk", "nts"],
                            "coords": [(36.2, 36.16)]}.
        name_attrs:     the attributes that hold the record's place names (used by LM_kNN_search,
                        and by the other methods when there is no phonetic encoding).
        phonetic_attrs: the attributes that hold phonetic encodings of the names. When given,
                        Q_grams, PassJoin, MinHash_LSH and TFIDF_kNN compare these instead.
        max_km:         geo restriction: only keep candidate pairs at most this many km apart
                        (default 50: the smallest threshold that lost no gold links on the
                        Pleiades-TM and MEHDIE samples; None = no restriction).
        coords_attr:    the attribute holding a record's (lat, lon) points; a list, because a
                        record can have several.
        keep_without_coords: keep pairs where a record has no coordinates (distance cannot rule
                        them out). False drops them."""
        self.datasets = datasets
        self.name_attrs = list(name_attrs)
        self.phonetic_attrs = list(phonetic_attrs) if phonetic_attrs else None
        self.max_km = max_km
        self.coords_attr = coords_attr
        self.keep_without_coords = keep_without_coords
        self._models = {}  # loaded language models, so each is loaded only once

    # ================================================================ the methods
    # Each method takes the names of two datasets (both default to the only two there are) and
    # returns a set of (source_id, target_id) candidate pairs. All of them compare names one at
    # a time and turn name pairs into record pairs at the end.

    @_geo_restricted
    def Q_grams(self, source=None, target=None, q=3, t=0.6, max_keys=500, max_comparisons=None) -> set:
        """Extended Q-Grams Blocking. A name's q-grams are its q-letter pieces
        ("antakya" -> ant, nta, tak, aky, kya). Its keys are every in-order combination of at
        least a share `t` of them; names that share a key become candidates.
        max_keys caps the keys per name; max_comparisons skips blocks bigger than that."""
        A, B = self._strings(source, target)
        blocks = defaultdict(lambda: (set(), set()))
        for side, names in enumerate((A, B)):
            for vid, name in names.items():
                for key in self._qgram_keys(name, q, t, max_keys):
                    blocks[key][side].add(vid)
        pairs = set()
        for a, b in blocks.values():
            if a and b and (max_comparisons is None or len(a) * len(b) <= max_comparisons):
                pairs.update(product(a, b))
        return self._to_record_pairs(pairs)

    @_geo_restricted
    def PassJoin(self, source=None, target=None, tau=1) -> set:
        """Pairs names that MAY be within `tau` edits (insert/delete/substitute a letter) of each
        other. Pigeonhole trick: cut a name into tau+1 pieces; tau edits can break at most tau
        of them, so a close enough name must contain at least one piece unchanged, near the
        same position. Never misses a pair within tau edits, but may keep some that aren't."""
        A, B = self._strings(source, target)
        parts = tau + 1

        index = defaultdict(set)      # (name length, piece number, piece text) -> target names
        by_length = defaultdict(set)  # name length -> target names
        for vid, name in B.items():
            by_length[len(name)].add(vid)
            if len(name) >= parts:
                for i, (start, length) in enumerate(self._pieces(len(name), parts)):
                    index[len(name), i, name[start:start + length]].add(vid)

        pairs = set()
        for vid, name in A.items():
            for L in range(max(0, len(name) - tau), len(name) + tau + 1):  # lengths within tau
                if L < parts or len(name) < parts:  # too short to cut into pieces: keep them all
                    matches = by_length.get(L, set())
                else:
                    matches = set()
                    for i, (start, length) in enumerate(self._pieces(L, parts)):
                        for pos in range(max(0, start - tau), min(len(name) - length, start + tau) + 1):
                            matches |= index.get((L, i, name[pos:pos + length]), set())
                pairs.update((vid, match) for match in matches)
        return self._to_record_pairs(pairs)

    @_geo_restricted
    def MinHash_LSH(self, source=None, target=None, n=3, num_perm=128, threshold=0.3) -> set:
        """Pairs names whose sets of letter n-grams overlap roughly `threshold` or more (Jaccard
        similarity), estimated quickly with MinHash signatures and locality-sensitive hashing."""
        from datasketch import MinHash, MinHashLSH

        def signature(name):
            padded = f" {name} "  # so the first and last letters get their own n-grams
            m = MinHash(num_perm=num_perm)
            for i in range(max(1, len(padded) - n + 1)):
                m.update(padded[i:i + n].encode("utf8"))
            return m

        A, B = self._strings(source, target)
        lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        for vid, name in B.items():
            lsh.insert(vid, signature(name))
        return self._to_record_pairs({(va, vb) for va, name in A.items() for vb in lsh.query(signature(name))})

    @_geo_restricted
    def TFIDF_kNN(self, source=None, target=None, k=3, ngram_range=(2, 3)) -> set:
        """Each name is a TF-IDF vector of its letter n-grams (rare pieces weigh more than common
        ones like "ia" or "al"). Pairs each name with its k most similar names on the other side,
        in both directions. Top-k instead of a threshold, so it behaves the same for short and
        long names. Names that share no n-gram at all are never paired."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        A, B = self._strings(source, target)
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=ngram_range)
        vectorizer.fit([*A.values(), *B.values()])
        vec_a, vec_b = vectorizer.transform(list(A.values())), vectorizer.transform(list(B.values()))
        # cosine distance 1 = no shared n-gram: those "neighbours" are arbitrary, so drop them
        return self._to_record_pairs(self._knn_both_ways(list(A), vec_a, list(B), vec_b, k, max_distance=0.999))

    @_geo_restricted
    def LM_kNN_search(self, source=None, target=None, model="sentence-transformers/LaBSE", k=3) -> set:
        """Embeds every name with a multilingual language model (LaBSE, BERT-based) and pairs
        each name with its k most similar names on the other side, in both directions (cosine).
        The only method that compares meaning rather than letters, so it works across scripts."""
        A, B = self._name_variants(source, target, normalize=False)  # the model wants raw names
        return self._to_record_pairs(self._knn_both_ways(list(A), self._embed(model, A), list(B), self._embed(model, B), k))

    def within_distance(self, pairs, source=None, target=None, max_km=None) -> set:
        """Geo restriction: keeps a candidate pair only if the two places are at most max_km
        apart (default: self.max_km). If a record has several points, the closest two count.
        Pairs where a record has no coordinates are kept if keep_without_coords is True."""
        max_km = self.max_km if max_km is None else max_km
        A, B = self._pick(source, target)
        kept = set()
        for a, b in pairs:
            points_a, points_b = A[a].get(self.coords_attr), B[b].get(self.coords_attr)
            if not points_a or not points_b:
                if self.keep_without_coords:
                    kept.add((a, b))
            elif min(self._km(p, q) for p in points_a for q in points_b) <= max_km:
                kept.add((a, b))
        return kept

    def all_pairs(self, method: str, **kwargs) -> dict:
        """Runs `method` (e.g. "PassJoin") on every pair of datasets, so a test set can hold any
        number of them: {(source, target): candidate pairs}. With datasets [a, b, c] the pairs
        are (a, b), (a, c) and (b, c), in the order the datasets were given."""
        return {(s, t): getattr(self, method)(s, t, **kwargs) for s, t in combinations(self.datasets, 2)}

    @staticmethod
    def evaluate(candidates, gold, n_source, n_target) -> dict:
        """PC = share of true matches that are candidates (recall).
        PQ = share of candidates that are true matches (precision).
        RR = share of all possible pairs that were NOT kept (how much work was saved)."""
        candidates, gold = set(candidates), set(gold)
        found = len(candidates & gold)
        return {
            "PC": found / len(gold) if gold else 0.0,
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

    def _strings(self, source, target):
        """What the letter-based methods compare: the phonetic encodings if given, else the names."""
        return self._name_variants(source, target, attrs=self.phonetic_attrs or self.name_attrs)

    def _name_variants(self, source, target, attrs=None, normalize=True):
        """One entry per name: {(record_id, n): name}. Names are compared one at a time, not all
        of a record's names glued together."""
        def variants(records):
            out = {}
            for rid, r in records.items():
                names = []
                for attr in attrs or self.name_attrs:
                    value = r.get(attr)
                    names += value if isinstance(value, (list, tuple)) else [value]
                names = [self._normalize(n) if normalize else str(n).strip() for n in names if n]
                out.update({(rid, i): name for i, name in enumerate(dict.fromkeys(x for x in names if x))})
            return out
        return tuple(variants(d) for d in self._pick(source, target))

    @staticmethod
    def _normalize(s: str) -> str:
        """Lowercase, remove accents / Hebrew vowel points / Arabic short vowels and tatweel,
        replace punctuation with spaces. Does NOT transliterate between scripts."""
        s = unicodedata.normalize("NFKC", str(s)).casefold().replace("ـ", "")
        s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
        return " ".join(re.sub(r"[^\w\s]", " ", s).split())

    @staticmethod
    def _to_record_pairs(name_pairs) -> set:
        """((id_a, n), (id_b, m)) name pairs -> (id_a, id_b) record pairs."""
        return {(a[0], b[0]) for a, b in name_pairs}

    # ================================================================ helpers
    @staticmethod
    def _knn_both_ways(ids_a, vec_a, ids_b, vec_b, k, max_distance=None) -> set:
        """Each row of vec_a with its k nearest rows of vec_b (cosine), and vice versa."""
        from sklearn.neighbors import NearestNeighbors

        def nearest(queries, points):
            nn = NearestNeighbors(n_neighbors=min(k, points.shape[0]), metric="cosine").fit(points)
            distances, indices = nn.kneighbors(queries)
            return [[j for d, j in zip(ds, js) if max_distance is None or d <= max_distance]
                    for ds, js in zip(distances, indices)]

        pairs = {(ids_a[i], ids_b[j]) for i, row in enumerate(nearest(vec_a, vec_b)) for j in row}
        pairs |= {(ids_a[j], ids_b[i]) for i, row in enumerate(nearest(vec_b, vec_a)) for j in row}
        return pairs

    @staticmethod
    def _qgram_keys(name, q, t, max_keys) -> set:
        name = name.replace(" ", "_")
        grams = [name[i:i + q] for i in range(len(name) - q + 1)] or [name]
        # Join every in-order combination of at least `least` q-grams. Raise `least` until a name
        # produces at most ~max_keys keys (long names would explode otherwise).
        total = len(grams)
        least = max(1, math.floor(total * t))
        while least < total and sum(math.comb(total, j) for j in range(least, total + 1)) > max_keys:
            least += 1
        return {"".join(c) for j in range(least, total + 1) for c in combinations(grams, j)}

    @staticmethod
    def _km(p, q) -> float:
        """Great-circle (haversine) distance in km between two (lat, lon) points."""
        lat1, lon1, lat2, lon2 = map(math.radians, (*p, *q))
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        return 2 * 6371.0 * math.asin(math.sqrt(h))

    @staticmethod
    def _pieces(length, parts) -> list:
        """Cut a string of `length` into `parts` near-equal pieces: [(start, piece length), ...]."""
        base, extra = divmod(length, parts)
        lengths = [base + (i >= parts - extra) for i in range(parts)]  # the last `extra` get +1
        return [(sum(lengths[:i]), lengths[i]) for i in range(parts)]

    def _embed(self, model, names: dict):
        if model not in self._models:
            from sentence_transformers import SentenceTransformer
            self._models[model] = SentenceTransformer(model)
        return self._models[model].encode(list(names.values()), normalize_embeddings=True,
                                          convert_to_numpy=True, show_progress_bar=False)
