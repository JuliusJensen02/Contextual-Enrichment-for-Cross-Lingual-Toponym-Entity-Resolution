"""PassJoin-style partition-based filtering for edit-distance <= tau (Li et al., PassJoin).
Simplified: even partition + position window [p - tau, p + tau] (a valid, slightly looser
superset of the paper's multi-match-aware substring selection). Returns CANDIDATES;
set verify=True to keep only pairs whose edit distance is really <= tau."""
from collections import defaultdict


def _segments(length: int, tau: int):
    k = tau + 1
    base, extra = divmod(length, k)
    segs, pos = [], 0
    for i in range(k):
        seg_len = base if i < k - extra else base + 1
        segs.append((pos, seg_len))
        pos += seg_len
    return segs


def edit_distance_leq(a: str, b: str, tau: int) -> bool:
    if abs(len(a) - len(b)) > tau:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        if min(cur) > tau:
            return False
        prev = cur
    return prev[-1] <= tau


def passjoin(A: dict, B: dict, tau: int = 1, verify: bool = False) -> set:
    k = tau + 1
    index = defaultdict(set)          # (len, segment_no, segment_text) -> ids in B
    short_b = defaultdict(set)        # strings shorter than tau+1 cannot be partitioned
    by_len_b = defaultdict(set)
    for ib, s in B.items():
        L = len(s)
        by_len_b[L].add(ib)
        if L < k:
            short_b[L].add(ib)
            continue
        for i, (p, l) in enumerate(_segments(L, tau)):
            index[(L, i, s[p:p + l])].add(ib)

    out = set()
    for ia, r in A.items():
        lr = len(r)
        cands = set()
        if lr < k:                    # tiny query: length filter only
            for L in range(max(0, lr - tau), lr + tau + 1):
                cands |= by_len_b.get(L, set())
        else:
            for L in range(max(k, lr - tau), lr + tau + 1):
                for i, (p, l) in enumerate(_segments(L, tau)):
                    for start in range(max(0, p - tau), min(lr - l, p + tau) + 1):
                        cands |= index.get((L, i, r[start:start + l]), set())
            for L in range(max(0, lr - tau), min(k - 1, lr + tau) + 1):
                cands |= short_b.get(L, set())
        if verify:
            cands = {ib for ib in cands if edit_distance_leq(r, B[ib], tau)}
        out.update((ia, ib) for ib in cands)
    return out
