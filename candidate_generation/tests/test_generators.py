"""Name-only enforcement, and generator behaviour on small inputs."""

import numpy as np
import pytest

from candidate_generation.data.build import make_record
from candidate_generation.data.schema import assert_name_only, name_table
from candidate_generation.engine import run_direction, top_targets
from candidate_generation.generators import (
    Dense,
    EmbeddingStore,
    Generator,
    MehdieBpf,
    TfidfChar,
)
from candidate_generation.generators.mehdie_bpf import (
    CLASS_BIT,
    blocks_of_ipa,
    blocks_of_letters,
)
from candidate_generation.generators.union_rrf import (
    UNRANKED,
    ranks_from_scores,
    reciprocal_rank_fusion,
    set_union_rank,
)


class FakeBackend:
    """Deterministic character-count vectors."""

    def encode(self, strings):
        vectors = np.zeros((len(strings), 64), dtype=np.float32)
        for row, text in enumerate(strings):
            for char in text:
                vectors[row, ord(char) % 64] += 1
        return vectors / np.maximum(
            np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9
        )


SPEC = {"repo": "fake", "revision": "0"}


def generators():
    return [
        MehdieBpf(),
        TfidfChar(),
        Dense("dense", EmbeddingStore(FakeBackend(), SPEC, None)),
    ]


QUERY = [make_record("q1", "a", ["Alexandria"]), make_record("q2", "a", ["بلنسية"])]
TARGET = [
    make_record("t1", "b", ["Aleksandreia"], 31.0, 29.0, "city"),
    make_record("t2", "b", ["בלנסיה"], 39.0, -0.3, "city"),
    make_record("t3", "b", ["Oo"], 1.0, 2.0, "river"),
]


def test_assert_rejects_attribute_fields():
    for field in ("lat", "lon", "feature_type"):
        with pytest.raises(AssertionError):
            assert_name_only({"name", field})
    with pytest.raises(AssertionError):
        assert_name_only({"record_id"})
    assert_name_only({"name", "name_variants", "transliteration", "ipa"})


def test_a_generator_declaring_coordinates_cannot_be_defined():
    with pytest.raises(AssertionError):

        class Leaky(Generator):
            name = "leaky"
            input_fields = frozenset({"name", "lat"})

            def _prepare(self, query, target): ...

            def score(self, query_indices): ...


def test_generators_refuse_raw_records():
    with pytest.raises(TypeError):
        TfidfChar().prepare(QUERY, TARGET)


def test_name_table_has_no_attribute_fields():
    table = name_table(TARGET)
    assert not {"lat", "lon", "feature_type"} & set(vars(table))


def test_scores_do_not_depend_on_coordinates_or_feature_type():
    changed = [
        make_record(r.record_id, "b", list(r.all_names), 0.0, 0.0, "other")
        for r in TARGET
    ]
    indices = np.arange(2)
    for first, second in zip(generators(), generators()):
        first.prepare(name_table(QUERY), name_table(TARGET))
        second.prepare(name_table(QUERY), name_table(changed))
        np.testing.assert_array_equal(first.score(indices), second.score(indices))


def test_bpf_class_contains_b_p_f():
    assert (
        blocks_of_ipa("b")
        == blocks_of_ipa("p")
        == blocks_of_ipa("f")
        == CLASS_BIT["labial"]
    )
    assert (
        blocks_of_letters("ב")
        == blocks_of_letters("ب")
        == blocks_of_letters("p")
        == CLASS_BIT["labial"]
    )


def test_bpf_affricate_is_one_segment():
    assert blocks_of_ipa("dʒ") == CLASS_BIT["sibilant"]


def test_bpf_ranks_by_shared_blocks_then_jaro():
    query = [make_record("q", "a", ["Bar"])]
    target = [
        make_record("same", "b", ["Bar"]),
        make_record("one", "b", ["Pa"]),
        make_record("no", "b", ["Mu"]),
    ]
    generator = MehdieBpf()
    generator.prepare(name_table(query), name_table(target))
    scores = generator.score(np.array([0]))[0]
    assert scores[0] > scores[1]
    assert np.isnan(scores[2])


def test_tfidf_finds_the_cross_script_form():
    generator = TfidfChar()
    generator.prepare(name_table(QUERY), name_table(TARGET))
    scores = generator.score(np.arange(2))
    assert np.nanargmax(scores[0]) == 0
    assert np.nanargmax(scores[1]) == 1


def test_a_variant_match_is_found():
    query = [make_record("q", "a", ["Roma"])]
    target = [
        make_record("hit", "b", ["Urbs", "Roma"]),
        make_record("miss", "b", ["Zed"]),
    ]
    generator = TfidfChar()
    generator.prepare(name_table(query), name_table(target))
    assert generator.score(np.array([0]))[0, 0] == pytest.approx(1.0)


def test_nameless_records_are_never_retrieved():
    query = [make_record("q", "a", [])]
    for generator in generators():
        generator.prepare(name_table(query), name_table(TARGET))
        assert np.isnan(generator.score(np.array([0]))).all()


def test_ranks_ties_follow_target_order_and_nan_is_unranked():
    ranks = ranks_from_scores(np.array([[0.5, 0.9, 0.5, np.nan]]))
    assert ranks.tolist() == [[2, 1, 3, UNRANKED]]


def test_rrf_on_known_values():
    first = np.array([[1, 2, UNRANKED]])
    second = np.array([[2, 1, UNRANKED]])
    fused = reciprocal_rank_fusion([first, second], constant=60)
    assert fused[0, 0] == pytest.approx(1 / 61 + 1 / 62)
    assert fused[0, 0] == pytest.approx(fused[0, 1])
    assert np.isnan(fused[0, 2])


def test_set_union_rank_takes_the_best():
    assert set_union_rank([np.array([3, UNRANKED]), np.array([7, 2])]).tolist() == [
        3,
        2,
    ]


def test_top_targets_marks_missing_entries():
    ranks = np.array([[2, 1, UNRANKED]])
    assert top_targets(ranks, 3).tolist() == [[1, 0, -1]]


def test_engine_matches_brute_force_ranks():
    result = run_direction(
        "toy",
        "forward",
        name_table(QUERY),
        name_table(TARGET),
        [("q1", "t1"), ("q2", "t2")],
        generators(),
        {"union_rrf": ["tfidf_char", "dense"]},
        60,
        100,
        1,
        2,
    )
    tfidf = TfidfChar()
    tfidf.prepare(name_table(QUERY), name_table(TARGET))
    expected = ranks_from_scores(np.round(tfidf.score(np.arange(2)), 6))
    assert result.ranks["tfidf_char"].tolist() == [expected[0, 0], expected[1, 1]]
    # q2: t2 is first for TF-IDF but last for the fake embedder, which scores cross-script
    # pairs 0, while t1 is second and first. So fusion correctly prefers t1.
    assert result.ranks["union_rrf"].tolist() == [1, 2]
    assert result.top["union_rrf"].tolist()[0][:2] == [0, 1]


def test_engine_is_independent_of_chunking():
    def run(chunk_size):
        return run_direction(
            "toy",
            "forward",
            name_table(QUERY),
            name_table(TARGET),
            [("q1", "t1")],
            generators(),
            {"union_rrf": ["tfidf_char", "dense"]},
            60,
            100,
            chunk_size,
            2,
        )

    np.testing.assert_array_equal(run(1).top["union_rrf"], run(2).top["union_rrf"])
