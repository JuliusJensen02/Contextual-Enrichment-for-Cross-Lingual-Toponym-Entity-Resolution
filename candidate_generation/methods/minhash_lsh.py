from base import BlockingMethod


class MinHashLSH(BlockingMethod):
    """Pairs names whose sets of letter n-grams overlap roughly `threshold` or more (Jaccard
    similarity), estimated quickly with MinHash signatures and locality-sensitive hashing.
    Needs datasketch."""

    name = "MinHash_LSH"

    def __init__(self, n=3, num_perm=128, threshold=0.3):
        self.n = n
        self.num_perm = num_perm
        self.threshold = threshold

    def candidates(self, source: dict, target: dict) -> set:
        from datasketch import MinHashLSH as LSHIndex

        lsh = LSHIndex(threshold=self.threshold, num_perm=self.num_perm)
        for name_id, name in target.items():
            lsh.insert(name_id, self._signature(name))
        return {(a, b) for a, name in source.items() for b in lsh.query(self._signature(name))}

    def _signature(self, name):
        from datasketch import MinHash

        padded = f" {name} "  # so the first and last letters get their own n-grams
        m = MinHash(num_perm=self.num_perm)
        for i in range(max(1, len(padded) - self.n + 1)):
            m.update(padded[i:i + self.n].encode("utf8"))
        return m
