from abc import abstractmethod

from .blocking_method import BlockingMethod


class KNNMethod(BlockingMethod):
    """Base class for the nearest-neighbour methods. Each name is turned into a vector and
    paired with its k most similar names on the other side (cosine), in both directions.
    Top-k instead of a threshold, so it behaves the same for short and long names.

    A subclass only says how names become vectors (`vectorize`). Needs scikit-learn."""

    # Neighbours further away than this (cosine distance) are dropped. None = keep all k.
    max_distance = None

    def __init__(self, k=3):
        self.k = k

    @abstractmethod
    def vectorize(self, source_names: list, target_names: list) -> tuple:
        """Two lists of names -> (source vectors, target vectors), one row per name."""

    def candidates(self, source: dict, target: dict) -> set:
        ids_a, ids_b = list(source), list(target)
        vec_a, vec_b = self.vectorize(list(source.values()), list(target.values()))
        pairs = {(ids_a[i], ids_b[j]) for i, row in enumerate(self._nearest(vec_a, vec_b)) for j in row}
        pairs |= {(ids_a[j], ids_b[i]) for i, row in enumerate(self._nearest(vec_b, vec_a)) for j in row}
        return pairs

    def _nearest(self, queries, points) -> list:
        """For each row of `queries`: the row numbers of its k nearest rows of `points`."""
        from sklearn.neighbors import NearestNeighbors

        nn = NearestNeighbors(n_neighbors=min(self.k, points.shape[0]), metric="cosine").fit(points)
        distances, indices = nn.kneighbors(queries)
        return [[j for d, j in zip(ds, js) if self.max_distance is None or d <= self.max_distance]
                for ds, js in zip(distances, indices)]
