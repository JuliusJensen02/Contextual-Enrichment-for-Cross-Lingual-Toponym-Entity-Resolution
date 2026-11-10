"""Token Blocking + Block Purging + Block Filtering + Meta-blocking (clean-clean / record linkage)."""
import math
from collections import defaultdict
from itertools import product


def token_blocking(A: dict, B: dict) -> dict:
    """A, B = {id: normalised text}. One block per token that occurs in BOTH collections."""
    ia, ib = defaultdict(set), defaultdict(set)
    for i, t in A.items():
        for tok in set(t.split()):
            ia[tok].add(i)
    for i, t in B.items():
        for tok in set(t.split()):
            ib[tok].add(i)
    return {k: (ia[k], ib[k]) for k in ia.keys() & ib.keys()}


def block_purging(blocks: dict, max_comparisons: int) -> dict:
    """Drop blocks with more than max_comparisons (|A_b| * |B_b|) -- stop-word-like tokens."""
    return {k: v for k, v in blocks.items() if len(v[0]) * len(v[1]) <= max_comparisons}


def block_filtering(blocks: dict, ratio: float = 0.8) -> dict:
    """Keep every entity only in the `ratio` fraction of its smallest blocks."""
    card = {k: len(a) * len(b) for k, (a, b) in blocks.items()}
    out = defaultdict(lambda: (set(), set()))
    for side in (0, 1):
        ent_blocks = defaultdict(list)
        for k, blk in blocks.items():
            for e in blk[side]:
                ent_blocks[e].append(k)
        for e, ks in ent_blocks.items():
            ks.sort(key=lambda k: card[k])
            for k in ks[: max(1, math.ceil(ratio * len(ks)))]:
                out[k][side].add(e)
    return {k: v for k, v in out.items() if v[0] and v[1]}


def meta_blocking(blocks: dict, scheme="cbs", prune="wnp", reciprocal=False) -> set:
    """Blocking-graph weighting + pruning. scheme: 'cbs' (common blocks) | 'arcs'.
    prune: 'wep' (global mean threshold) | 'wnp' (per-node mean threshold)."""
    w = defaultdict(float)
    for a_ids, b_ids in blocks.values():
        inc = 1.0 if scheme == "cbs" else 1.0 / (len(a_ids) * len(b_ids))
        for pair in product(a_ids, b_ids):
            w[pair] += inc
    if not w:
        return set()
    if prune == "wep":
        thr = sum(w.values()) / len(w)
        return {p for p, x in w.items() if x >= thr}
    na, nb = defaultdict(list), defaultdict(list)
    for (a, b), x in w.items():
        na[a].append(x)
        nb[b].append(x)
    ta = {a: sum(v) / len(v) for a, v in na.items()}
    tb = {b: sum(v) / len(v) for b, v in nb.items()}
    keep = set()
    for (a, b), x in w.items():
        ok_a, ok_b = x >= ta[a], x >= tb[b]
        if (ok_a and ok_b) if reciprocal else (ok_a or ok_b):
            keep.add((a, b))
    return keep


def token_meta_blocking(A, B, max_comparisons=None, filter_ratio=0.8,
                        scheme="cbs", prune="wnp", reciprocal=False) -> set:
    blocks = token_blocking(A, B)
    if max_comparisons is not None:
        blocks = block_purging(blocks, max_comparisons)
    if filter_ratio is not None:
        blocks = block_filtering(blocks, filter_ratio)
    return meta_blocking(blocks, scheme, prune, reciprocal)
