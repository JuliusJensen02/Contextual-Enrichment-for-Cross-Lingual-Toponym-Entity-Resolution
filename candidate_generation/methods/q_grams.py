import math
from collections import defaultdict
from itertools import combinations, product

from base import BlockingMethod


class QGrams(BlockingMethod):
    """Extended Q-Grams Blocking (key-based). A name's q-grams are its q-letter pieces
    ("antakya" -> ant, nta, tak, aky, kya). Its keys are every in-order combination of at
    least a share `t` of them; names that share a key become candidates.
    max_keys caps the keys per name; max_comparisons skips blocks bigger than that."""

    name = "Q_grams"

    def __init__(self, q=3, t=0.6, max_keys=500, max_comparisons=None):
        self.q = q
        self.t = t
        self.max_keys = max_keys
        self.max_comparisons = max_comparisons

    def candidates(self, source: dict, target: dict) -> set:
        blocks = defaultdict(lambda: (set(), set()))
        for side, names in enumerate((source, target)):
            for name_id, name in names.items():
                for key in self._keys(name):
                    blocks[key][side].add(name_id)
        pairs = set()
        for a, b in blocks.values():
            if a and b and (self.max_comparisons is None or len(a) * len(b) <= self.max_comparisons):
                pairs.update(product(a, b))
        return pairs

    def _keys(self, name) -> set:
        name = name.replace(" ", "_")
        grams = [name[i:i + self.q] for i in range(len(name) - self.q + 1)] or [name]
        # Join every in-order combination of at least `least` q-grams. Raise `least` until a name
        # produces at most ~max_keys keys (long names would explode otherwise).
        total = len(grams)
        least = max(1, math.floor(total * self.t))
        while least < total and sum(math.comb(total, j) for j in range(least, total + 1)) > self.max_keys:
            least += 1
        return {"".join(c) for j in range(least, total + 1) for c in combinations(grams, j)}
