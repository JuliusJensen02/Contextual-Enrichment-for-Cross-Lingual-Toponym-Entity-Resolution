"""Similarity scores between every record of one dataset and every record of another.

The blocking methods in methods/ answer yes or no (or give k neighbours). In the combined score
of the pipeline each of them is replaced by the score its answer is based on:

  tfidf    TFIDF_kNN      TF-IDF cosine on letter n-grams
  jaccard  MinHash_LSH    Jaccard overlap of the padded letter n-grams (what MinHash estimates)
  qgram    Q_grams        shared q-grams divided by the q-grams of the longer name
  edit     PassJoin       edit distance scaled to 0-1 (1 = identical)
  jaro     (none)         Jaro-Winkler similarity
  labse    LM_kNN_search  cosine of the LaBSE embeddings

Every scorer gives `chunk(start, stop)`: a dense float32 array [stop - start, target records]
with values between 0 and 1. A record with an empty string scores 0 against everything.
"""
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer


class Tfidf:
    def __init__(self, a: list[str], b: list[str], ngrams=(2, 3)):
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=ngrams).fit(a + b)
        self.a, self.b_t = vectorizer.transform(a), vectorizer.transform(b).T.tocsr()

    def chunk(self, start, stop):
        return (self.a[start:stop] @ self.b_t).toarray().astype(np.float32)


class _SetOverlap:
    """Base of the two scores that count the letter pieces two names share."""

    def __init__(self, a: list[str], b: list[str], n: int):
        vocabulary = {}

        def matrix(names):
            indptr, indices = [0], []
            for name in names:
                indices.extend(vocabulary.setdefault(gram, len(vocabulary)) for gram in self.grams(name, n))
                indptr.append(len(indices))
            return indptr, indices

        (ptr_a, idx_a), (ptr_b, idx_b) = matrix(a), matrix(b)
        shape = lambda ptr: (len(ptr) - 1, max(1, len(vocabulary)))  # noqa: E731
        self.a = csr_matrix((np.ones(len(idx_a), np.float32), idx_a, ptr_a), shape=shape(ptr_a))
        self.b_t = csr_matrix((np.ones(len(idx_b), np.float32), idx_b, ptr_b), shape=shape(ptr_b)).T.tocsr()
        self.size_a, self.size_b = np.diff(ptr_a).astype(np.float32), np.diff(ptr_b).astype(np.float32)

    def chunk(self, start, stop):
        shared = (self.a[start:stop] @ self.b_t).toarray().astype(np.float32)
        total = self.total(shared, self.size_a[start:stop, None], self.size_b[None, :])
        return np.divide(shared, total, out=np.zeros_like(shared), where=total > 0)


class Jaccard(_SetOverlap):
    @staticmethod
    def grams(name, n) -> set:
        if not name:
            return set()
        padded = f" {name} "  # as MinHashLSH._signature
        return {padded[i:i + n] for i in range(max(1, len(padded) - n + 1))}

    @staticmethod
    def total(shared, size_a, size_b):
        return size_a + size_b - shared


class QGram(_SetOverlap):
    @staticmethod
    def grams(name, q) -> set:
        if not name:
            return set()
        name = name.replace(" ", "_")  # as QGrams._keys
        return {name[i:i + q] for i in range(len(name) - q + 1)} or {name}

    @staticmethod
    def total(shared, size_a, size_b):
        return np.maximum(size_a, size_b) + 0 * shared


class _RapidFuzz:
    scorer = None

    def __init__(self, a: list[str], b: list[str], workers=1):
        self.a, self.b, self.workers = a, b, workers
        self.empty_a = np.array([not name for name in a])
        self.empty_b = np.array([not name for name in b])

    def chunk(self, start, stop):
        from rapidfuzz import process

        scores = process.cdist(self.a[start:stop], self.b, scorer=self.scorer, dtype=np.float32,
                               workers=self.workers)
        scores[self.empty_a[start:stop]] = 0
        scores[:, self.empty_b] = 0
        return scores


class Edit(_RapidFuzz):
    def __init__(self, a, b, workers=1):
        from rapidfuzz.distance import Levenshtein

        super().__init__(a, b, workers)
        self.scorer = Levenshtein.normalized_similarity


class JaroWinkler(_RapidFuzz):
    def __init__(self, a, b, workers=1):
        from rapidfuzz.distance import JaroWinkler as jw

        super().__init__(a, b, workers)
        self.scorer = jw.similarity


class Embedding:
    """Cosine of two sets of unit-length embeddings (one row per record)."""

    def __init__(self, a: np.ndarray, b: np.ndarray):
        self.a, self.b_t = a.astype(np.float32), np.ascontiguousarray(b.T.astype(np.float32))

    def chunk(self, start, stop):
        return self.a[start:stop] @ self.b_t


def letter_scorer(spec: str, a: list[str], b: list[str]):
    """spec: "tfidf:2-3", "jaccard:3", "qgram:2", "edit" or "jaro"."""
    kind, _, setting = spec.partition(":")
    if kind == "tfidf":
        low, _, high = setting.partition("-")
        return Tfidf(a, b, (int(low), int(high or low)))
    if kind == "jaccard":
        return Jaccard(a, b, int(setting))
    if kind == "qgram":
        return QGram(a, b, int(setting))
    if kind == "edit":
        return Edit(a, b)
    if kind == "jaro":
        return JaroWinkler(a, b)
    raise ValueError(f"Unknown score: {spec}")
