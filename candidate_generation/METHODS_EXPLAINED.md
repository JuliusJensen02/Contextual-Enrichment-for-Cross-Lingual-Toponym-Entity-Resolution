# Candidate generation, explained simply

Comparing every place in gazetteer A with every place in gazetteer B is too slow
(10,000 × 10,000 = 100 million pairs). **Candidate generation** (also called *blocking*) quickly
picks out the pairs that *might* be the same place. Only those are checked carefully later.

Running example used below: is **"Antakya"** (Turkish) the same place as **"Antakia"** (Greek
transliteration)? Both are the ancient city of Antioch.

---

## Part 1: `CandidateGenerator` ([candidate_generator.py](candidate_generator.py))

This class holds the datasets and does the work that is the same for every method. The actual
name comparison is handed to one of the methods in Part 2.

```python
CandidateGenerator(datasets, PassJoin(tau=1)).generate()
```

### `__init__`
Stores the settings: the datasets, which method to use, which attributes hold names
(`name`, `alt`), optional phonetic attributes, and the geo limit `max_km` (default 50 km).

### `generate(source, target)`
The main entry point. Steps:
1. Pick the two datasets.
2. Collect all names from both (`_names`).
3. Ask the method which **names** are similar.
4. Turn name pairs into **record** pairs.
5. Throw away pairs that are more than `max_km` apart (`within_distance`).

**Example:** record `T1 = {"name": "Antakya", "alt": ["Antioch"]}` and
`P7 = {"name": "Antakia"}`. The method says `"antakya"` ≈ `"antakia"`, so the record pair
`(T1, P7)` becomes a candidate.

### `all_pairs()`
Runs `generate` on every combination of datasets.

**Example:** datasets `[a, b, c]` → runs `(a, b)`, `(a, c)`, `(b, c)`.

### `evaluate(candidates, ground_truth, n_source, n_target)`
Scores how good the candidates are:

| Metric | Meaning | Formula |
|---|---|---|
| **PC** (recall) | How many true matches did we keep? | found / true matches |
| **PQ** (precision) | How many candidates are true matches? | found / candidates |
| **RR** (reduction) | How much work did we save? | 1 − candidates / all pairs |

**Example:** 100 × 100 records, 4 true matches, 10 candidates of which 3 are true:
PC = 3/4 = 0.75, PQ = 3/10 = 0.30, RR = 1 − 10/10,000 = 0.999.

### `_pick(source, target)`
Looks up the two datasets by name. If none are given and there are exactly two datasets, it
uses those two; otherwise it raises an error.

### `_names(records)`
Collects every name of every record, one entry per name, keyed by `(record_id, n)`. Duplicates
are removed. Names are normalized (see below), unless the method wants raw names
(`LM_kNN_search`). If `phonetic_attrs` is set, the phonetic codes are used instead of the names.

**Example:** `{"T1": {"name": "Antakya", "alt": ["Antioch"]}}` →
`{("T1", 0): "antakya", ("T1", 1): "antioch"}`

### `_normalize(s)`
Lowercase, remove accents / Hebrew vowel points / Arabic short vowels and tatweel, and replace
punctuation with spaces. It does **not** translate between scripts.

**Example:** `"Ḥalab!"` → `"halab"`

### `within_distance(pairs, source, target, max_km, ...)`
Geo blocking. Keeps a pair only if the two places are at most `max_km` apart. If a record has
several coordinates, the closest two points are used. Pairs where a record has no coordinates
are kept (by default), since distance can't rule them out.

**Example:** Antakya `(36.20, 36.16)` and Antakia `(36.20, 36.15)` are ~1 km apart → kept.
Antakya and a "Antakia" in Spain would be > 50 km apart → dropped.

### `_km(p, q)`
Distance in km between two `(lat, lon)` points on the Earth's surface (haversine formula).

---

## Part 2: The blocking methods ([methods/](methods/))

Each method answers one question: *"Which names from A look similar to which names from B?"*

### Q-Grams (`Q_grams`, [q_grams.py](methods/q_grams.py)) — shared letter pieces

1. Cut each name into overlapping pieces of `q` letters (**q-grams**).
2. Build **keys** by gluing together every in-order combination of at least a share `t` of
   those pieces.
3. Names that share at least one key become candidates.

**Example** (`q=3`, `t=0.6`):
- `antakya` → `ant, nta, tak, aky, kya` (5 pieces; keys use at least 3 of them)
- `antakia` → `ant, nta, tak, aki, kia`
- Both produce the key `ant+nta+tak` → **candidate**.

`max_keys` stops long names from producing too many keys; `max_comparisons` skips huge blocks.

### PassJoin (`PassJoin`, [pass_join.py](methods/pass_join.py)) — few letter edits

Finds names that are within `tau` **edits** (insert, delete or change one letter) of each other.

Trick (pigeonhole): cut a name into `tau + 1` pieces. `tau` edits can break at most `tau` pieces,
so at least one piece must survive unchanged. So we only compare names that share a piece at
roughly the same position.

**Example** (`tau=1`, so 2 pieces):
- `antakia` → `ant | akia`
- `antakya` contains `ant` at the same position → **candidate**.
- True distance: `y → i` is 1 edit ✔.

It never misses a pair within `tau` edits, but may keep a few that are not.

### MinHash LSH (`MinHash_LSH`, [minhash_lsh.py](methods/minhash_lsh.py)) — overlapping letter sets

1. Turn each name into a **set** of 3-letter pieces (with a space added at both ends).
2. Measure overlap with **Jaccard similarity** = shared pieces / all pieces.
3. Computing this for every pair is slow, so **MinHash** makes a short "fingerprint" of each set,
   and **LSH** puts similar fingerprints in the same bucket. Names in the same bucket become
   candidates if their estimated overlap is ≥ `threshold` (default 0.3).

**Example:**
- ` antakya ` → `{" an", ant, nta, tak, aky, kya, "ya "}`
- ` antakia ` → `{" an", ant, nta, tak, aki, kia, "ia "}`
- Shared = 4, total distinct = 10 → Jaccard = 0.4 ≥ 0.3 → **candidate**.

### TF-IDF kNN (`TFIDF_kNN`, [tfidf_knn.py](methods/tfidf_knn.py)) — top-k most similar spellings

1. Turn each name into a vector of its 2- and 3-letter pieces.
2. **TF-IDF** weighting: rare pieces count more than common ones (e.g. `al`, `ia`).
3. For each name, take its `k` most similar names on the other side (cosine similarity), in both
   directions. Names sharing no piece at all are never paired.

**Example** (`k=3`): for `antakya`, the 3 closest target names might be `antakia`, `antakiya`,
`antalya` → all three become candidates. The rare piece `tak` makes `antakia` rank highest.

### LM kNN Search (`LM_kNN_search`, [lm_knn_search.py](methods/lm_knn_search.py)) — similar meaning, any script

1. Feed each raw name into a multilingual language model (**LaBSE**), which turns it into a
   vector representing its *meaning*.
2. For each name, take its `k` most similar names on the other side, in both directions.

This is the only method that does not compare letters, so it works **across scripts**.

**Example:** `Antioch`, `Αντιόχεια` (Greek) and `أنطاكية` (Arabic) share no letters, but LaBSE
puts their vectors close together → **candidates**.

---

## Part 3: Base classes ([base/](base/))

### `BlockingMethod` ([blocking_method.py](base/blocking_method.py))
The interface all methods follow: a `candidates(source, target)` method that returns similar
name pairs, and a `raw_names` flag (whether the method wants un-normalized names).

### `KNNMethod` ([knn_method.py](base/knn_method.py))
Shared code for the two kNN methods (TF-IDF and LM).
- `vectorize(...)`: each subclass says how names become vectors.
- `candidates(...)`: finds the `k` nearest neighbours A → B **and** B → A, and joins both.
- `_nearest(...)`: the actual neighbour search (cosine distance). Neighbours further than
  `max_distance` are dropped.

**Example** (`k=1`): `antakya` → nearest is `antakia`; and `antakia` → nearest is `antakya`.
Searching both ways catches pairs that only one side would find.

---

## Quick comparison

| Method | Compares | Pairs when… | Cross-script? |
|---|---|---|---|
| Q-Grams | letter pieces | they share enough pieces | no |
| PassJoin | letters | ≤ `tau` edits apart | no |
| MinHash LSH | sets of letter pieces | overlap ≥ `threshold` | no |
| TF-IDF kNN | weighted letter pieces | among the `k` most similar | no |
| LM kNN | meaning (LaBSE) | among the `k` most similar | **yes** |
