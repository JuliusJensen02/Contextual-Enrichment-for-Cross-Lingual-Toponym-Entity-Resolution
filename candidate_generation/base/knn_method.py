from abc import abstractmethod

import numpy as np

from .blocking_method import BlockingMethod


class KNNMethod(BlockingMethod):
    """Base class for the nearest-neighbour methods. Each name is turned into a vector and
    paired with its k most similar names on the other side (cosine), in both directions.
    Top-k instead of a threshold, so it behaves the same for short and long names.

    A subclass only says how names become vectors (`vectorize`). Needs scikit-learn."""

    # Neighbours further away than this (cosine distance) are dropped. None = keep all k.
    max_distance = None
    geo_first = True
    chunk = 1000  # source names compared at a time when `blocked` is given

    def __init__(self, k=3):
        self.k = k

    @abstractmethod
    def vectorize(self, source_names: list, target_names: list) -> tuple:
        """Two lists of names -> (source vectors, target vectors), one row per name."""

    def candidates(self, source: dict, target: dict, blocked=None) -> set:
        """blocked: None, or a function (start, stop) -> boolean array [stop - start, len(target)]
        that is True where source name start..stop and a target name may not be paired (the geo
        filter). Blocked pairs are left out before the k neighbours are picked."""
        ids_a, ids_b = list(source), list(target)
        vec_a, vec_b = self.vectorize(list(source.values()), list(target.values()))
        if blocked is not None:
            return {(ids_a[i], ids_b[j]) for i, j in self._nearest_allowed(vec_a, vec_b, blocked)}
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

    def _nearest_allowed(self, vec_a, vec_b, blocked) -> set:
        """(row of a, row of b) for each row's k most similar rows on the other side among the
        pairs that are not blocked, in both directions. The vectors have length 1, so the dot
        product is the cosine similarity."""
        n, m = vec_a.shape[0], vec_b.shape[0]
        k_rows, k_cols = min(self.k, m), min(self.k, n)
        min_sim = -np.inf if self.max_distance is None else 1 - self.max_distance
        vec_b_t = vec_b.T.tocsr() if hasattr(vec_b, "tocsr") else vec_b.T
        pairs = set()
        best_sim = np.full((0, m), -np.inf, dtype=np.float32)  # per row of b: its k best rows of a so far
        best_row = np.zeros((0, m), dtype=np.int64)
        for c in range(0, n, self.chunk):
            sim = vec_a[c:c + self.chunk] @ vec_b_t
            sim = np.array(sim.toarray() if hasattr(sim, "toarray") else sim, dtype=np.float32)
            sim[blocked(c, c + self.chunk)] = -np.inf
            top = np.argpartition(-sim, k_rows - 1, axis=1)[:, :k_rows]
            for i, js in enumerate(top):
                pairs.update((c + i, j) for j in js if sim[i, j] >= min_sim and sim[i, j] > -np.inf)
            rows = np.arange(c, c + len(sim))[:, None].repeat(m, 1)
            best_sim, best_row = np.vstack([best_sim, sim]), np.vstack([best_row, rows])
            keep = np.argpartition(-best_sim, k_cols - 1, axis=0)[:k_cols]
            best_sim, best_row = np.take_along_axis(best_sim, keep, 0), np.take_along_axis(best_row, keep, 0)
        for j in range(m):
            pairs.update((i, j) for s, i in zip(best_sim[:, j], best_row[:, j]) if s >= min_sim and s > -np.inf)
        return pairs
