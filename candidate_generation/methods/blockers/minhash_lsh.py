"""MinHash-LSH on character n-grams (the LSH core of KLSH-style hybrid blocking, no K-Means step).
Needs: pip install datasketch"""
from datasketch import MinHash, MinHashLSH


def char_shingles(s: str, n: int = 3) -> set:
    s = f" {s} "                                   # pad so first/last letters get their own grams
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def _minhash(text: str, n: int, num_perm: int) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for g in char_shingles(text, n):
        m.update(g.encode("utf8"))
    return m


def minhash_lsh(A: dict, B: dict, n: int = 3, num_perm: int = 128, threshold: float = 0.3) -> set:
    """threshold = approximate Jaccard similarity of the shingle sets. Short place names have few
    shingles, so start LOW (0.2-0.4) and raise it until Pair Completeness starts to drop."""
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for ib, t in B.items():
        lsh.insert(ib, _minhash(t, n, num_perm))
    out = set()
    for ia, t in A.items():
        for ib in lsh.query(_minhash(t, n, num_perm)):
            out.add((ia, ib))
    return out
