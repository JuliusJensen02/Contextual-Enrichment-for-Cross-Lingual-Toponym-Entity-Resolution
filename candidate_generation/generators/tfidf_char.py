"""TF-IDF over character n-grams of the shared representation, with cosine similarity."""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from candidate_generation.data.schema import NameTable
from candidate_generation.generators.base import Generator, StringGroups, group_max


class TfidfChar(Generator):
    """Scores a pair by the best cosine over both records' name forms."""

    name = "tfidf_char"
    input_fields = frozenset({"name", "name_variants", "ipa", "transliteration"})

    def __init__(
        self, representation: str = "ipa", ngram_range: tuple[int, int] = (2, 4)
    ):
        self.representation = representation
        self.ngram_range = tuple(ngram_range)

    def _prepare(self, query: NameTable, target: NameTable) -> None:
        self.query_strings = StringGroups(query.representation(self.representation))
        self.target_strings = StringGroups(target.representation(self.representation))
        vocabulary_source = sorted(
            set(self.query_strings.flat) | set(self.target_strings.flat)
        )
        # Fitted on both sides without labels. IDF has to know both corpora, since a
        # query n-gram absent from one side would otherwise get an arbitrary weight.
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=self.ngram_range,
            lowercase=False,
            dtype=np.float32,
        ).fit(vocabulary_source)
        self.query_matrix = self.vectorizer.transform(self.query_strings.flat).tocsr()
        self.target_matrix_t = self.vectorizer.transform(
            self.target_strings.flat
        ).T.tocsc()

    def score(self, query_indices: np.ndarray) -> np.ndarray:
        positions, offsets = self.query_strings.chunk(query_indices)
        cosine = (self.query_matrix[positions] @ self.target_matrix_t).toarray()
        scores = group_max(cosine, offsets, self.target_strings.offsets[:-1])
        scores[scores <= 0] = np.nan
        return scores.astype(np.float32)

    def metadata(self) -> dict:
        return {
            **super().metadata(),
            "representation": self.representation,
            "analyzer": "char_wb",
            "ngram_range": list(self.ngram_range),
        }
