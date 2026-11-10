"""Extended Q-Grams Blocking (Baxter et al. / as described in Papadakis et al. 2020, Sec. 3.2.1)."""
from collections import defaultdict
from itertools import combinations
from math import comb, floor


def qgrams(s: str, q: int = 3) -> list:
    s = s.replace(" ", "_")
    return [s[i:i + q] for i in range(len(s) - q + 1)] or [s]


def extended_keys(s: str, q: int = 3, t=0.9, max_keys: int = 64) -> set:
    """t=None -> plain Q-Grams Blocking. Otherwise: concatenate (order-preserving) combinations of >= l q-grams, l = max(1, floor(k*t)).
    l is raised if needed so one string never produces more than ~max_keys keys."""
    grams = qgrams(s, q)
    if t is None:                      # plain Q-Grams Blocking: every single q-gram is a key
        return set(grams)
    k = len(grams)
    l = max(1, floor(k * t))
    while l < k and sum(comb(k, j) for j in range(l, k + 1)) > max_keys:
        l += 1
    return {"".join(c) for j in range(l, k + 1) for c in combinations(grams, j)}


def extended_qgrams_blocking(A: dict, B: dict, q=3, t=0.9, max_keys=64,
                             max_comparisons=None) -> set:
    ia, ib = defaultdict(set), defaultdict(set)
    for i, s in A.items():
        for key in extended_keys(s, q, t, max_keys):
            ia[key].add(i)
    for i, s in B.items():
        for key in extended_keys(s, q, t, max_keys):
            ib[key].add(i)
    pairs = set()
    for key in ia.keys() & ib.keys():
        if max_comparisons is not None and len(ia[key]) * len(ib[key]) > max_comparisons:
            continue
        pairs.update((a, b) for a in ia[key] for b in ib[key])
    return pairs
