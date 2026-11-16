from base import KNNMethod


class LMKNNSearch(KNNMethod):
    """Neural kNN. Embeds every name with a multilingual language model (LaBSE, BERT-based) and
    pairs each name with its k most similar names on the other side, in both directions. The
    only method that compares meaning rather than letters, so it works across scripts.
    Needs sentence-transformers."""

    name = "LM_kNN_search"
    raw_names = True  # the model wants the names as written

    # Shared by all instances, so that trying several k embeds every list of names only once:
    _encoders = {}    # model name -> loaded model
    _embeddings = {}  # (model name, names) -> their embeddings

    def __init__(self, model="sentence-transformers/LaBSE", k=3):
        super().__init__(k)
        self.model = model

    def vectorize(self, source_names: list, target_names: list) -> tuple:
        return self._embed(source_names), self._embed(target_names)

    def _embed(self, names: list):
        key = (self.model, tuple(names))
        if key not in self._embeddings:
            if self.model not in self._encoders:
                from sentence_transformers import SentenceTransformer
                self._encoders[self.model] = SentenceTransformer(self.model)
            self._embeddings[key] = self._encoders[self.model].encode(
                names, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        return self._embeddings[key]
