from base import KNNMethod


class TfidfKNN(KNNMethod):
    """Sparse kNN. Each name is a TF-IDF vector of its letter n-grams (rare pieces weigh more
    than common ones like "ia" or "al"). Pairs each name with its k most similar names on the
    other side, in both directions. Names that share no n-gram at all are never paired."""

    name = "TFIDF_kNN"
    # cosine distance 1 = no shared n-gram: those "neighbours" are arbitrary, so drop them
    max_distance = 0.999

    def __init__(self, k=3, ngram_range=(2, 3)):
        super().__init__(k)
        self.ngram_range = ngram_range

    def vectorize(self, source_names: list, target_names: list) -> tuple:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=self.ngram_range)
        vectorizer.fit(source_names + target_names)
        return vectorizer.transform(source_names), vectorizer.transform(target_names)
