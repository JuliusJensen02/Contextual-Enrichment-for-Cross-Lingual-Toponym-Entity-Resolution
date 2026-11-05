"""The frozen variants: oracle always has the true match, real is never altered."""

import copy
import math

import pyarrow.parquet as pq

from candidate_generation.frozen import (
    COLUMNS,
    FrozenWriter,
    build_oracle,
    build_real,
    sha256_file,
)

QUERIES = ["q1", "q2", "q3", "q4"]
CANDIDATES = [["a", "b", "c"], ["d", "e", "f"], [], ["x", "y"]]
SCORES = [[0.3, 0.2, 0.1], [0.3, 0.2, 0.1], [], [0.2, 0.1]]
# q1's match is retrieved, q2's is missing, q3 has no candidates, q4 has no match at all.
TRUTH = {"q1": {"b"}, "q2": {"z", "e", "w"}, "q3": {"m"}}


def real_rows(seed=1):
    return build_real(QUERIES, CANDIDATES, SCORES, TRUTH, 3, seed, "toy")


def test_real_is_exactly_the_generator_output():
    for row, candidates, scores in zip(real_rows(), CANDIDATES, SCORES):
        assert row["candidate_id"] == candidates
        assert row["score"] == scores
        assert row["rank"] == list(range(1, len(candidates) + 1))
        assert not any(row["oracle_injected"])


def test_real_marks_ground_truth():
    rows = real_rows()
    assert rows[0]["is_ground_truth"] == [False, True, False]
    assert rows[1]["is_ground_truth"] == [False, True, False]


def test_oracle_always_contains_every_true_match():
    for seed in range(200):
        real = real_rows(seed)
        oracle = build_oracle(QUERIES, real, TRUTH, 3, seed, "toy")
        for query, row in zip(QUERIES, oracle):
            assert TRUTH.get(query, set()) <= set(row["candidate_id"])


def test_oracle_injects_for_a_query_with_no_candidates():
    oracle = build_oracle(QUERIES, real_rows(), TRUTH, 3, 1, "toy")
    assert oracle[2]["candidate_id"] == ["m"]
    assert oracle[2]["oracle_injected"] == [True]
    assert oracle[2]["query_id"] == ["q3"]


def test_oracle_never_alters_real():
    real = real_rows()
    before = copy.deepcopy(real)
    build_oracle(QUERIES, real, TRUTH, 3, 1, "toy")
    assert real == before


def test_oracle_keeps_the_same_set_and_relative_order():
    real = real_rows()
    oracle = build_oracle(QUERIES, real, TRUTH, 3, 1, "toy")
    for before, after in zip(real, oracle):
        kept = [
            c for c, i in zip(after["candidate_id"], after["oracle_injected"]) if not i
        ]
        assert kept == before["candidate_id"]
        order = sorted(
            range(len(after["candidate_id"])), key=after["shuffle_position"].__getitem__
        )
        shuffled = [
            after["candidate_id"][i] for i in order if not after["oracle_injected"][i]
        ]
        original = sorted(
            range(len(before["candidate_id"])),
            key=before["shuffle_position"].__getitem__,
        )
        assert shuffled == [before["candidate_id"][i] for i in original]


def test_oracle_rows_without_injection_equal_real():
    real = real_rows()
    oracle = build_oracle(QUERIES, real, TRUTH, 3, 1, "toy")
    assert oracle[0] == real[0] and oracle[3] == real[3]


def test_oracle_marks_only_injected_rows():
    oracle = build_oracle(QUERIES, real_rows(), TRUTH, 3, 1, "toy")
    row = oracle[1]
    injected = {
        c for c, flag in zip(row["candidate_id"], row["oracle_injected"]) if flag
    }
    assert injected == {"z", "w"}
    assert all(
        row["is_ground_truth"][row["candidate_id"].index(c)] for c in ("z", "e", "w")
    )
    assert all(math.isnan(s) for s, f in zip(row["score"], row["oracle_injected"]) if f)
    assert row["rank"] == list(range(1, 6))
    assert sorted(row["shuffle_position"]) == list(range(1, 6))


def test_injection_position_varies_with_seed():
    positions = set()
    for seed in range(50):
        row = build_oracle(QUERIES, real_rows(seed), {"q2": {"z"}}, 3, seed, "toy")[1]
        positions.add(row["candidate_id"].index("z"))
    assert len(positions) == 4


def test_shuffle_is_a_seeded_permutation():
    assert sorted(real_rows()[0]["shuffle_position"]) == [1, 2, 3]
    assert real_rows(5) == real_rows(5)
    assert any(real_rows(s)[0]["shuffle_position"] != [1, 2, 3] for s in range(10))


def test_written_file_has_the_exact_columns_and_a_stable_hash(tmp_path):
    hashes = []
    for run in range(2):
        real = real_rows()
        writer = FrozenWriter(tmp_path / f"{run}.parquet")
        writer.write(real)
        writer.write(build_oracle(QUERIES, real, TRUTH, 3, 1, "toy"))
        hashes.append(writer.close())
    assert hashes[0] == hashes[1] == sha256_file(tmp_path / "1.parquet")
    assert tuple(pq.read_schema(tmp_path / "0.parquet").names) == COLUMNS
