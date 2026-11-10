import random, itertools
from blockers.common import normalize, serialize, evaluate
from blockers.token_meta import token_blocking, token_meta_blocking, block_filtering, block_purging
from blockers.ext_qgrams import extended_keys, extended_qgrams_blocking
from blockers.passjoin import passjoin, edit_distance_leq

# --- PassJoin: no false negatives vs brute force, verify=True == exact
random.seed(1)
alpha = "abcd"
for tau in (1, 2, 3):
    for trial in range(30):
        A = {i: "".join(random.choice(alpha) for _ in range(random.randint(0, 9))) for i in range(25)}
        B = {i: "".join(random.choice(alpha) for _ in range(random.randint(0, 9))) for i in range(25)}
        truth = {(a, b) for a in A for b in B if edit_distance_leq(A[a], B[b], tau)}
        cand = passjoin(A, B, tau)
        assert truth <= cand, (tau, trial, truth - cand)
        assert passjoin(A, B, tau, verify=True) == truth
print("passjoin ok")

# --- ext q-grams
print(sorted(extended_keys("france", 3, 0.9)))
assert len(extended_keys("a" * 40, 3, 0.9, 64)) <= 64 + 5

# --- toy toponyms
A = {1: "constantinople turkey", 2: "baghdad iraq", 3: "alexandria egypt", 4: "new york usa"}
B = {10: "konstantinopel turkey", 11: "bagdad iraq", 12: "alexandrie egypt", 13: "york england", 14: "cairo egypt"}
gold = {(1, 10), (2, 11), (3, 12)}
for name, fn in [("token+meta", lambda a, b: token_meta_blocking(a, b)),
                 ("token(no meta)", lambda a, b: {p for v in token_blocking(a, b).values() for p in itertools.product(*v)}),
                 ("extq", lambda a, b: extended_qgrams_blocking(a, b, q=3, t=0.8)),
                 ("passjoin t=2", lambda a, b: passjoin({k: v.split()[0] for k, v in a.items()}, {k: v.split()[0] for k, v in b.items()}, 2))]:
    c = fn(A, B)
    print(name, evaluate(c, gold, len(A), len(B)))
print(serialize({"id": 1, "name": "Ṣanʿāʾ", "tags": {"country": "Yemen", "alt": ["Sana'a", "صنعاء"]}}))
print(serialize({"id": 1, "name": "Constantinople", "country": "Turkey"}, with_names=True, norm=False))
