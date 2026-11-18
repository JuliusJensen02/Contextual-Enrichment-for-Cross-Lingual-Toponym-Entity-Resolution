from collections import defaultdict

from base import BlockingMethod


class PassJoin(BlockingMethod):
    """Pairs names that MAY be within `tau` edits (insert/delete/substitute a letter) of each
    other (Levenshtein). Pigeonhole trick: cut a name into tau+1 pieces; tau edits can break at
    most tau of them, so a close enough name must contain at least one piece unchanged, near the
    same position. Never misses a pair within tau edits, but may keep some that aren't."""

    name = "PassJoin"

    def __init__(self, tau=1):
        self.tau = tau

    def candidates(self, source: dict, target: dict) -> set:
        tau, parts = self.tau, self.tau + 1

        index = defaultdict(set)      # (name length, piece number, piece text) -> target names
        by_length = defaultdict(set)  # name length -> target names
        for name_id, name in target.items():
            by_length[len(name)].add(name_id)
            if len(name) >= parts:
                for i, (start, length) in enumerate(self._pieces(len(name), parts)):
                    index[len(name), i, name[start:start + length]].add(name_id)

        pairs = set()
        for name_id, name in source.items():
            for L in range(max(0, len(name) - tau), len(name) + tau + 1):  # lengths within tau
                if L < parts or len(name) < parts:  # too short to cut into pieces: keep them all
                    matches = by_length.get(L, set())
                else:
                    matches = set()
                    for i, (start, length) in enumerate(self._pieces(L, parts)):
                        for pos in range(max(0, start - tau), min(len(name) - length, start + tau) + 1):
                            matches |= index.get((L, i, name[pos:pos + length]), set())
                pairs.update((name_id, match) for match in matches)
        return pairs

    @staticmethod
    def _pieces(length, parts) -> list:
        """Cut a string of `length` into `parts` near-equal pieces: [(start, piece length), ...]."""
        base, extra = divmod(length, parts)
        lengths = [base + (i >= parts - extra) for i in range(parts)]  # the last `extra` get +1
        return [(sum(lengths[:i]), lengths[i]) for i in range(parts)]
