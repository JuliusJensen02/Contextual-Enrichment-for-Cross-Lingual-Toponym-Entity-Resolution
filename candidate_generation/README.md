# Candidate generation (blocking) for toponym entity matching: a Python guide

This guide shows how to implement the 7 shortlisted candidate-generation methods and compare them on your own data, so you can pick one blocker to feed the entity-matching step.

| # | Method | Type | File | Extra install | Run here? |
|---|---|---|---|---|---|
| 1 | LM embeddings + kNN search | Dense retrieval, unsupervised | `blockers/dense.py` | `sentence-transformers faiss-cpu` | not run |
| 2 | SC-Block-style fine-tuned encoder | Dense retrieval, supervised | `blockers/dense.py` | same | not run, **approximation** |
| 3 | Neural LSH (NLSHBlock) | Learned blocking | `blockers/dense.py` | same | not run, **stand-in only** |
| 4 | Token Blocking + Purging + Filtering + Meta-blocking | Schema-agnostic blocking | `blockers/token_meta.py` | none | tested (toy) |
| 5 | MinHash-LSH on character n-grams | Approximate hybrid blocking | `blockers/minhash_lsh.py` | `datasketch` | not run |
| 6 | (Extended) Q-Grams Blocking | Schema-aware blocking | `blockers/ext_qgrams.py` | none | tested (toy) |
| 7 | PassJoin | Edit-distance filtering | `blockers/passjoin.py` | none | tested vs brute force |

**What was and wasn't verified.** The sandbox I wrote this in had no network access, so `sentence-transformers`, `faiss` and `datasketch` could not be installed. Methods 1, 2, 3 and 5 are written against those libraries' APIs as I know them but have **not been executed**. Run the smoke test in section 8 first, and check library versions if a call fails. Methods 4, 6 and 7 and the helpers use only the standard library and were run: PassJoin was checked against brute-force edit distance on 90 random collections (tau = 1, 2, 3) and missed no pair. Methods 4 and 6 were only run on a 6-vs-7-record toy, which proves the plumbing, not their quality.

---

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install datasketch sentence-transformers faiss-cpu   # only needed for methods 1, 2, 3, 5
```

Project layout:

```
blockers/
  __init__.py        (empty file)
  common.py          normalisation, serialisation, metrics
  token_meta.py      method 4
  ext_qgrams.py      method 6
  passjoin.py        method 7
  minhash_lsh.py     method 5
  dense.py           methods 1, 2, 3
demo_data.py         tiny toponym example
run_comparison.py    runs every blocker, prints PC / PQ / RR
```

## 2. Conventions

- **Records** are JSON-like dicts with a unique `"id"`. Nested dicts and lists are fine; `flatten()` turns them into leaf values.
- **Task**: record linkage between two collections `A` and `B`. For deduplication inside one collection, pass the same dict twice, then drop `(x, x)` pairs and keep one orientation of each pair.
- **Every blocker has the same signature**: `fn(A, B) -> set of (id_a, id_b)`, where `A` and `B` are `{id: text}` dicts. That makes them interchangeable in the harness.
- **Three text views** are built from the same records:
  - *full*: all attributes, normalised. Used by token blocking.
  - *variants*: one string per name variant (`name`, `alt` names), keyed `(record_id, n)`. Used by methods 5, 6, 7. These methods compare **individual names**, so they must not see one long concatenated string per record. Map the variant pairs back with `collapse()`.
  - *raw with attribute names*: e.g. `name: Constantinople ; country: Turkey`, not normalised. Used by the LM encoders in methods 1-3.
- **Metrics** (from the Papadakis survey): Pair Completeness PC (recall), Pairs Quality PQ (precision), Reduction Ratio RR.

### `blockers/common.py`

```python
"""Shared helpers: text normalisation, record serialisation, block -> pairs, evaluation."""
import re
import unicodedata
from itertools import product


def normalize(s) -> str:
    """Casefold, strip diacritics / Hebrew niqqud / Arabic harakat / tatweel, drop punctuation."""
    s = unicodedata.normalize("NFKC", str(s)).casefold().replace("\u0640", "")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def flatten(value):
    """Yield every leaf value of a nested dict/list as a string (semi-structured -> flat)."""
    if value is None:
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from flatten(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from flatten(v)
    else:
        yield str(value)


def serialize(record: dict, attrs=None, with_names=False, norm=True) -> str:
    """Turn one record into one string.
    norm=True       -> normalised text (for the string-based blockers)
    with_names=True -> 'name: Konstantinopel ; country: Turkey' (nicer input for LM encoders)
    """
    keys = attrs or [k for k in record if k != "id"]
    parts = []
    for k in keys:
        vals = [normalize(v) if norm else v for v in flatten(record.get(k))]
        vals = [v for v in vals if v]
        if vals:
            parts.append(f"{k}: {' '.join(vals)}" if with_names else " ".join(vals))
    return " ; ".join(parts) if with_names else " ".join(parts)


def blocks_to_pairs(blocks) -> set:
    """blocks = {key: (ids_from_A, ids_from_B)} -> set of (id_a, id_b) candidate pairs."""
    pairs = set()
    for ids_a, ids_b in blocks.values():
        pairs.update(product(ids_a, ids_b))
    return pairs


def evaluate(candidates, gold, n_a, n_b) -> dict:
    """Pair Completeness (recall), Pairs Quality (precision), Reduction Ratio."""
    cand, gold = set(candidates), set(gold)
    tp = len(cand & gold)
    return {
        "PC": tp / len(gold) if gold else 0.0,
        "PQ": tp / len(cand) if cand else 0.0,
        "RR": 1 - len(cand) / (n_a * n_b) if n_a * n_b else 0.0,
        "candidates": len(cand),
    }


def explode_names(records, attrs) -> dict:
    """One entry per name VARIANT: {(record_id, n): normalised_variant}. Edit-distance and q-gram
    methods should compare variants one by one, not one long concatenated string per record."""
    out = {}
    for r in records:
        variants = [normalize(v) for k in attrs for v in flatten(r.get(k))]
        for n, v in enumerate(v for v in variants if v):
            out[(r["id"], n)] = v
    return out


def collapse(pairs) -> set:
    """Map variant-level pairs ((id_a, n), (id_b, m)) back to record-level pairs (id_a, id_b)."""
    return {(a[0], b[0]) for a, b in pairs}
```

Normalisation strips diacritics, Hebrew niqqud, Arabic harakat and tatweel. It does **not** transliterate, so "Bagdad" and "بغداد" still differ. Cross-script links only come from (a) alternate names you already have in the records or (b) the dense methods.

---

## 3. Method 1: LM embeddings + kNN search

Encode every record with a pre-trained multilingual sentence encoder, index one side with FAISS, and take each record's top-k nearest neighbours on the other side as candidates.

### `blockers/dense.py` (all three dense methods)

```python
"""Dense-retrieval blocking: (1) off-the-shelf LM embeddings + kNN, (2) contrastive fine-tuning,
(3) an LSH-on-embeddings stand-in for neural LSH.
Needs: pip install sentence-transformers faiss-cpu"""
import numpy as np


def encode(model, texts, batch_size=64) -> np.ndarray:
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=False).astype("float32")


def knn_candidates(emb_q, ids_q, emb_idx, ids_idx, k=10, hnsw=False) -> set:
    """For every query vector return its top-k nearest index vectors (cosine, vectors are normalised)."""
    import faiss
    d = emb_idx.shape[1]
    index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT) if hnsw else faiss.IndexFlatIP(d)
    index.add(emb_idx)
    _, nn = index.search(emb_q, min(k, len(ids_idx)))
    return {(ids_q[i], ids_idx[j]) for i, row in enumerate(nn) for j in row if j >= 0}


def dense_knn(A: dict, B: dict, model="sentence-transformers/LaBSE", k=10, batch_size=64,
              hnsw=False, both_directions=True, device=None) -> set:
    """Method 1. `model` = a model name OR an already loaded SentenceTransformer (e.g. fine-tuned)."""
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model, device=device) if isinstance(model, str) else model
    ids_a, ids_b = list(A), list(B)
    ea = encode(m, [A[i] for i in ids_a], batch_size)
    eb = encode(m, [B[i] for i in ids_b], batch_size)
    cands = knn_candidates(ea, ids_a, eb, ids_b, k, hnsw)                     # A -> B
    if both_directions:                                                        # B -> A, then union
        cands |= {(a, b) for b, a in knn_candidates(eb, ids_b, ea, ids_a, k, hnsw)}
    return cands


def finetune_contrastive(base_model: str, A: dict, B: dict, train_pairs, epochs=3,
                         batch_size=32, out_dir="blocker-model"):
    """Method 2 (APPROXIMATION of SC-Block): bi-encoder fine-tuned on known matching pairs with an
    in-batch-negatives contrastive loss. NOT the authors' exact supervised-contrastive objective."""
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from sentence_transformers.datasets import NoDuplicatesDataLoader
    model = SentenceTransformer(base_model)
    examples = [InputExample(texts=[A[a], B[b]]) for a, b in train_pairs]
    loader = NoDuplicatesDataLoader(examples, batch_size=batch_size)   # no repeated text per batch
    loss = losses.MultipleNegativesRankingLoss(model)
    model.fit(train_objectives=[(loader, loss)], epochs=epochs,
              warmup_steps=max(1, int(0.1 * len(loader) * epochs)), show_progress_bar=True)
    model.save(out_dir)
    return model


def dense_lsh(A: dict, B: dict, model, nbits=256, k=10, batch_size=64) -> set:
    """Method 3 (STAND-IN for NLSHBlock): random-hyperplane LSH codes over (fine-tuned) embeddings,
    Hamming-distance kNN. NLSHBlock itself LEARNS the hash function; this does not."""
    import faiss
    ids_a, ids_b = list(A), list(B)
    ea = encode(model, [A[i] for i in ids_a], batch_size)
    eb = encode(model, [B[i] for i in ids_b], batch_size)
    index = faiss.IndexLSH(eb.shape[1], nbits)
    index.add(eb)
    _, nn = index.search(ea, min(k, len(ids_b)))
    return {(ids_a[i], ids_b[j]) for i, row in enumerate(nn) for j in row if j >= 0}
```

Usage:

```python
from blockers.common import serialize
from blockers.dense import dense_knn

A = {r["id"]: serialize(r, with_names=True, norm=False) for r in records_a}
B = {r["id"]: serialize(r, with_names=True, norm=False) for r in records_b}
cands = dense_knn(A, B, model="sentence-transformers/LaBSE", k=10)
```

Things to tune and try:
- **k** is the main knob. Sweep k = 1, 5, 10, 20, 50 and plot PC against the number of candidates.
- **Model**: try `sentence-transformers/LaBSE` (built for cross-lingual sentence alignment) against `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. The Zeakis et al. study compared 12 language models, so compare a few on your data rather than trusting one.
- **Input text**: names only versus names + country/coordinates-as-text. Long, noisy text can dilute the name signal.
- `both_directions=True` unions A→B and B→A neighbours, which usually raises PC at some cost in candidates.
- `hnsw=True` switches FAISS from exact search to an approximate HNSW index for large collections.

## 4. Method 2: SC-Block-style fine-tuned encoder (approximation)

SC-Block fine-tunes a bi-encoder with a **supervised contrastive** objective so that matching records land close together, then retrieves with kNN. `finetune_contrastive()` in `dense.py` is an **approximation**: it uses sentence-transformers' in-batch-negatives loss on your known matching pairs. It is not the authors' exact objective. For a faithful version, look for the code link on the paper's arXiv page (https://arxiv.org/abs/2303.03132); I have not checked whether or where it is released.

```python
from blockers.dense import finetune_contrastive, dense_knn

# train_pairs: list of (id_a, id_b) known matches, used ONLY for training
model = finetune_contrastive("sentence-transformers/LaBSE", A, B, train_pairs, epochs=3)
cands = dense_knn(A, B, model=model, k=10)      # pass the fine-tuned model object
```

- **Split your gold pairs** by entity into train / dev / test (e.g. 60/20/20) and report PC on test pairs only. Training and evaluating on the same pairs gives meaningless PC.
- Compare against the same encoder **without** fine-tuning (method 1). If fine-tuning doesn't raise PC at the same |C|, drop it.
- With only a few hundred positive pairs, overfitting is likely: keep epochs low and watch dev PC.
- Needs known matches. If your datasets carry external links (e.g. to Wikidata), those can supply training pairs.
- `NoDuplicatesDataLoader` avoids repeating the same text within a batch, which would otherwise turn a true match into an in-batch negative.

## 5. Method 3: Neural LSH (stand-in only)

NLSHBlock (https://arxiv.org/abs/2401.18064) learns a neural hash function for blocking. I have only seen its abstract-level description, and I don't know of a released implementation. `dense_lsh()` is a **stand-in**: random-hyperplane LSH codes over the (optionally fine-tuned) embeddings, searched by Hamming distance. It lets you test the "hash embeddings into compact codes" idea, but it does not learn the hash function. If you cite NLSHBlock in your comparison, implement it from the paper or the authors' code.

```python
from blockers.dense import dense_lsh
cands = dense_lsh(A, B, model=model, nbits=256, k=10)   # model: fine-tuned object or a loaded SentenceTransformer
```

Tune `nbits` (try 64-512) and `k`.

---

## 6. Methods 4-7: classical blocking and filtering

### Method 4: Token Blocking + Block Purging + Block Filtering + Meta-blocking

One block per token shared by both collections. Purging removes huge, stop-word-like blocks. Filtering keeps each record only in its smallest blocks. Meta-blocking builds a graph of record pairs weighted by how many blocks they share and prunes weak edges. Described in https://doi.org/10.1145/3377455 (§3.3 and §4).

```python
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
```

Usage:

```python
from blockers.token_meta import token_meta_blocking
A = {r["id"]: serialize(r) for r in records_a}     # normalised, all attributes
B = {r["id"]: serialize(r) for r in records_b}
cands = token_meta_blocking(A, B, max_comparisons=None, filter_ratio=0.8,
                            scheme="cbs", prune="wnp", reciprocal=False)
```

- **What's implemented**: CBS and ARCS weighting, WEP and WNP pruning (plus the reciprocal variant). **Not implemented**: BLAST (chi-square weights with attribute entropy) and Supervised Meta-blocking / GSM. For those, use an existing library (section 9).
- **Parameter hints from the survey (§4.3)**: Block Filtering alone works best at r = 80%; applied after Block Purging, r = 50% is better. Treat these as starting points, not tuned values.
- **Toponym pitfall**: tokens like "city", "saint", "al", "of" create giant blocks. Use `max_comparisons` (for example a small fraction of |A|·|B|, tuned on PC) to purge them.
- Tokens only match within one script. Hebrew, Arabic and Latin spellings share no tokens unless alternate names bridge them.

### Method 5: MinHash-LSH on character n-grams

Each name becomes a set of character 3-grams. MinHash signatures plus banded LSH put names with high Jaccard overlap into the same bucket. This is the LSH core of KLSH-style hybrid blocking (survey §6), without the K-Means step.

```python
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
```

Usage (variant level, see section 2):

```python
from blockers.common import explode_names, collapse
from blockers.minhash_lsh import minhash_lsh
A_var = explode_names(records_a, ["name", "alt"])
B_var = explode_names(records_b, ["name", "alt"])
cands = collapse(minhash_lsh(A_var, B_var, n=3, num_perm=128, threshold=0.3))
```

Short place names have few 3-grams, so start with a low `threshold` (0.2-0.4) and raise it until PC begins to drop. Try `n=2` for very short names. More `num_perm` gives more accurate similarity estimates at a higher cost.

### Method 6: (Extended) Q-Grams Blocking

Every name is cut into q-grams. Plain Q-Grams Blocking uses each q-gram as a key. Extended Q-Grams concatenates combinations of at least `l = max(1, floor(k·t))` of a name's `k` q-grams, which makes keys more distinctive and blocks smaller (survey §3.2.1).

```python
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
```

Usage:

```python
from blockers.ext_qgrams import extended_qgrams_blocking
cands = collapse(extended_qgrams_blocking(A_var, B_var, q=3, t=None))        # plain q-grams
cands = collapse(extended_qgrams_blocking(A_var, B_var, q=3, t=0.8, max_keys=500))  # extended
```

- **Run the plain version too (`t=None`).** On my 5-name toy, extended q-grams at t=0.9 reached PC 0.33 where plain q-grams reached 1.0, because long names with several spelling differences ("Constantinople" / "Konstantinopel") share too few exact q-gram combinations. A toy with three gold pairs is not evidence, but check PC on your data.
- `max_keys` caps combinations per name (it raises `l`), because the number of combinations grows combinatorially with name length. That cap is my addition, not part of the original method.
- The survey's worked example for "france" lists four signatures. All ordered combinations give five, and the code uses all combinations.

### Method 7: PassJoin (edit-distance filtering)

PassJoin splits each string into tau+1 segments. Any string within edit distance tau must share at least one segment (pigeonhole principle), so segments act as an inverted index. Described in https://doi.org/10.1145/3377455 (§5); the original is Li et al.'s PassJoin paper.

```python
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
```

Usage:

```python
from blockers.passjoin import passjoin
cands = collapse(passjoin(A_var, B_var, tau=2))                  # candidates only
exact = collapse(passjoin(A_var, B_var, tau=2, verify=True))     # pairs truly within tau edits
```

- This is a **simplified** PassJoin: even partition with a ±tau position window, which is a valid but looser superset of the paper's selection. It never misses a pair within tau edits (tested), but returns more candidates than the original.
- `verify=False` returns raw candidates, which is what a blocking step needs. `verify=True` returns only pairs within tau edits, which already amounts to an edit-distance matcher.
- It is pure Python, so benchmark on a sample before running on a large collection.
- Edit distance doesn't bridge scripts or heavy transliteration differences. tau = 1-3 is a sensible range for place names.
- For small collections, an all-pairs edit-distance computation (e.g. with `rapidfuzz`) is a good sanity check on PassJoin's recall.

---

## 7. Compare everything: `run_comparison.py`

```python
"""Run every blocker on the same data and print PC / PQ / RR.
  python run_comparison.py --demo
  python run_comparison.py --a A.json --b B.json --gold gold.json --name-attrs name alt
A.json / B.json: list of records, each with an "id". gold.json: list of [id_a, id_b]."""
import argparse
import json
import time

from blockers.common import collapse, evaluate, explode_names, serialize


def load_records(path):
    with open(path, encoding="utf8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a"); ap.add_argument("--b"); ap.add_argument("--gold")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--name-attrs", nargs="+", default=["name", "alt"],
                    help="attributes holding the place name(s); used by the character-level methods")
    ap.add_argument("--k", type=int, default=5, help="neighbours per record for dense methods")
    args = ap.parse_args()

    if args.demo:
        from demo_data import A as RA, B as RB, GOLD
    else:
        RA, RB = load_records(args.a), load_records(args.b)
        GOLD = [tuple(p) for p in load_records(args.gold)]
    gold = set(map(tuple, GOLD))

    full = lambda recs: {r["id"]: serialize(r) for r in recs}                      # all attrs, normalised
    variants = lambda recs: explode_names(recs, args.name_attrs)                    # one entry per name variant
    raw = lambda recs: {r["id"]: serialize(r, with_names=True, norm=False) for r in recs}  # for LM encoders

    methods = []   # (label, view, callable)
    from blockers.token_meta import token_meta_blocking
    from blockers.ext_qgrams import extended_qgrams_blocking
    from blockers.passjoin import passjoin
    methods += [
        ("4 token+purge+filter+meta(WNP)", full, lambda a, b: token_meta_blocking(a, b, filter_ratio=0.8)),
        ("6a plain q-grams (q=3)", variants, lambda a, b: collapse(extended_qgrams_blocking(a, b, q=3, t=None))),
        ("6b extended q-grams (t=0.6)", variants, lambda a, b: collapse(extended_qgrams_blocking(a, b, q=3, t=0.6, max_keys=500))),
        ("7 passjoin tau=2 (candidates)", variants, lambda a, b: collapse(passjoin(a, b, tau=2))),
    ]
    try:
        from blockers.minhash_lsh import minhash_lsh
        methods.append(("5 minhash-lsh (3-grams)", variants, lambda a, b: collapse(minhash_lsh(a, b, threshold=0.3))))
    except ImportError:
        print("skip method 5 (pip install datasketch)")
    try:
        from blockers.dense import dense_knn
        import faiss, sentence_transformers  # noqa: F401
        methods.append(("1 LaBSE + kNN", raw, lambda a, b: dense_knn(a, b, k=args.k)))
    except ImportError:
        print("skip method 1 (pip install sentence-transformers faiss-cpu)")

    print(f"{'method':34s} {'PC':>6s} {'PQ':>6s} {'RR':>6s} {'|C|':>7s} {'sec':>6s}")
    for label, view, fn in methods:
        a, b = view(RA), view(RB)
        t0 = time.time()
        cands = fn(a, b)
        dt = time.time() - t0
        m = evaluate(cands, gold, len(RA), len(RB))
        print(f"{label:34s} {m['PC']:6.3f} {m['PQ']:6.3f} {m['RR']:6.3f} {m['candidates']:7d} {dt:6.2f}")


if __name__ == "__main__":
    main()
```

Run it:

```bash
python run_comparison.py --demo
python run_comparison.py --a A.json --b B.json --gold gold.json --name-attrs name alt --k 10
```

Output of `--demo` in the sandbox (methods 1 and 5 skipped because their packages weren't installed):

```
skip method 5 (pip install datasketch)
skip method 1 (pip install sentence-transformers faiss-cpu)
method                                 PC     PQ     RR     |C|    sec
4 token+purge+filter+meta(WNP)      1.000  0.625  0.810       8   0.00
6a plain q-grams (q=3)              1.000  0.625  0.810       8   0.00
6b extended q-grams (t=0.6)         1.000  1.000  0.881       5   0.00
7 passjoin tau=2 (candidates)       1.000  1.000  0.881       5   0.00
```

That is a 6-vs-7-record toy with 5 gold pairs. It checks that the plumbing works, not which method is better. Methods 2 and 3 are not in the harness: add them once you have a train/test split of gold pairs.

`demo_data.py`, the toy data used above:

```python
"""Tiny semi-structured toponym demo (A = historical gazetteer, B = modern gazetteer)."""
A = [
    {"id": "a1", "name": "Constantinople", "alt": ["Konstantiniyye"], "geo": {"lat": 41.0, "lon": 28.98}, "country": "Turkey"},
    {"id": "a2", "name": "Baghdad", "alt": ["Bagdad"], "geo": {"lat": 33.31, "lon": 44.37}, "country": "Iraq"},
    {"id": "a3", "name": "Alexandria", "alt": [], "geo": {"lat": 31.2, "lon": 29.92}, "country": "Egypt"},
    {"id": "a4", "name": "Antioch", "alt": ["Antakya"], "geo": {"lat": 36.2, "lon": 36.16}, "country": "Turkey"},
    {"id": "a5", "name": "Damascus", "alt": ["Dimashq"], "geo": {"lat": 33.51, "lon": 36.29}, "country": "Syria"},
    {"id": "a6", "name": "York", "alt": [], "geo": {"lat": 53.96, "lon": -1.08}, "country": "England"},
]
B = [
    {"id": "b1", "name": "Istanbul", "alt": ["Konstantinopel", "Constantinople"], "geo": {"lat": 41.01, "lon": 28.97}, "country": "Turkey"},
    {"id": "b2", "name": "Bagdad", "alt": ["Baghdād"], "geo": {"lat": 33.3, "lon": 44.4}, "country": "Iraq"},
    {"id": "b3", "name": "Alexandrie", "alt": ["Al-Iskandariyah"], "geo": {"lat": 31.2, "lon": 29.9}, "country": "Egypt"},
    {"id": "b4", "name": "Antakya", "alt": ["Antioche"], "geo": {"lat": 36.2, "lon": 36.17}, "country": "Turkey"},
    {"id": "b5", "name": "Dimashq", "alt": ["Damas"], "geo": {"lat": 33.5, "lon": 36.3}, "country": "Syria"},
    {"id": "b6", "name": "Cairo", "alt": ["Al-Qahira"], "geo": {"lat": 30.04, "lon": 31.24}, "country": "Egypt"},
    {"id": "b7", "name": "New York", "alt": [], "geo": {"lat": 40.7, "lon": -74.0}, "country": "USA"},
]
GOLD = [("a1", "b1"), ("a2", "b2"), ("a3", "b3"), ("a4", "b4"), ("a5", "b5")]
```

## 8. Smoke test, then real evaluation

1. `python run_comparison.py --demo` should print the table without errors. If it prints "skip method 1/5", install the missing packages and rerun.
2. `python test_pure.py` re-runs the PassJoin brute-force check and the toy tests (stdlib only).
3. Compare methods **at matched candidate-set size** (or matched RR). PC always rises as you allow more candidates, so a method with a bigger |C| looks better unless you control for it. Sweep each method's main parameter (k, threshold, tau, filter ratio) and plot PC against |C|.
4. Prioritise **PC**. The matcher only sees the candidates, so a pair missed here can't be recovered later. Then pick the method with the smallest |C| that keeps PC acceptably high, and check its runtime.
5. Keep train / dev / test separate for methods 2 and 3, and tune every method's parameters on dev pairs only.

## 9. Existing libraries (not checked)

- **pyJedAI** and **BlockingPy** are Python libraries for entity-resolution blocking. A search result describes BlockingPy as ANN-based blocking (n-gram encoding or embeddings, neighbour search, graph components). I haven't checked either library's current API, so read their documentation before relying on them. pyJedAI appears to bundle several of the blocking, meta-blocking and embedding methods covered here, which would give you BLAST and supervised meta-blocking without implementing them.
- The hand-written versions above are meant to be readable and to run without heavy dependencies, not to be the fastest.

## 10. Sources

- Papadakis, Skoutas, Thanos, Palpanas. *Blocking and Filtering Techniques for Entity Resolution: A Survey.* ACM CSUR 2020. https://doi.org/10.1145/3377455
- Zeakis, Papadakis, Skoutas, Koubarakis. *Pre-trained Embeddings for Entity Resolution: An Experimental Analysis.* https://arxiv.org/abs/2304.12329
- Brinkmann, Shraga, Bizer. *SC-Block.* https://arxiv.org/abs/2303.03132
- *Neural Locality Sensitive Hashing for Entity Blocking (NLSHBlock).* https://arxiv.org/abs/2401.18064
