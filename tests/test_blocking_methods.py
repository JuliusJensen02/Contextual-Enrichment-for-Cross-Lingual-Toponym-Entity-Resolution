"""candidate_generation/methods: the blocking methods, each on names only."""
import random

import numpy as np
import pytest

from base import BlockingMethod, KNNMethod
from methods import LMKNNSearch, MinHashLSH, PassJoin, QGrams, TfidfKNN

SOURCE = {"a1": "antakya", "a2": "damascus", "a3": "jerusalem"}
TARGET = {"b1": "antakia", "b2": "damaskus", "b3": "baghdad"}


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def test_every_method_implements_the_interface():
    for method in (QGrams(), PassJoin(), MinHashLSH(), TfidfKNN(), LMKNNSearch()):
        assert isinstance(method, BlockingMethod)
        assert method.name
    assert LMKNNSearch.raw_names and not TfidfKNN.raw_names
    assert TfidfKNN.geo_first and LMKNNSearch.geo_first and not PassJoin.geo_first


# ============================================================================ Q_grams
def test_qgrams_keys_are_in_order_combinations_of_the_q_grams():
    assert QGrams(q=3, t=1.0)._keys("abcd") == {"abcbcd"}
    assert QGrams(q=3, t=0.5)._keys("abcd") == {"abc", "bcd", "abcbcd"}
    assert QGrams(q=3)._keys("ab") == {"ab"}          # shorter than q: the name itself
    assert QGrams(q=2, t=1.0)._keys("a b") == {"a__b"}  # spaces count as a letter


def test_qgrams_max_keys_caps_the_keys_of_a_long_name():
    name = "abcdefghijklmnopqrstuvwxyz"

    assert len(QGrams(q=3, t=0.1, max_keys=500)._keys(name)) <= 500
    assert len(QGrams(q=3, t=0.1, max_keys=5)._keys(name)) <= 25  # at worst: all but one q-gram


def test_qgrams_pairs_names_that_share_most_of_their_q_grams():
    pairs = QGrams(q=3, t=0.6).candidates(SOURCE, TARGET)

    assert ("a1", "b1") in pairs          # antakya / antakia
    assert ("a3", "b3") not in pairs      # jerusalem / baghdad
    assert QGrams().candidates({"x": "same"}, {"y": "same"}) == {("x", "y")}


def test_qgrams_max_comparisons_skips_big_blocks():
    source = {f"a{i}": "antakya" for i in range(3)}
    target = {f"b{i}": "antakya" for i in range(3)}

    assert len(QGrams().candidates(source, target)) == 9
    assert QGrams(max_comparisons=8).candidates(source, target) == set()


# ============================================================================ PassJoin
def test_passjoin_pieces_cover_the_string_and_the_last_ones_are_longer():
    assert PassJoin._pieces(7, 2) == [(0, 3), (3, 4)]
    assert PassJoin._pieces(6, 3) == [(0, 2), (2, 2), (4, 2)]
    assert PassJoin._pieces(8, 3) == [(0, 2), (2, 3), (5, 3)]


def test_passjoin_tau_zero_only_pairs_identical_names():
    pairs = PassJoin(tau=0).candidates({"a": "antakya", "b": "antakia"}, {"c": "antakya"})

    assert pairs == {("a", "c")}


def test_passjoin_finds_the_close_names():
    pairs = PassJoin(tau=1).candidates(SOURCE, TARGET)

    assert {("a1", "b1"), ("a2", "b2")} <= pairs
    assert ("a3", "b3") not in pairs


@pytest.mark.parametrize("tau", [0, 1, 2, 3])
def test_passjoin_never_misses_a_pair_within_tau_edits(tau):
    rng = random.Random(tau)
    words = ["".join(rng.choice("abc") for _ in range(rng.randint(0, 8))) for _ in range(120)]
    source = {f"a{i}": word for i, word in enumerate(words[:60])}
    target = {f"b{i}": word for i, word in enumerate(words[60:])}

    pairs = PassJoin(tau=tau).candidates(source, target)

    within_tau = {(a, b) for a, x in source.items() for b, y in target.items() if levenshtein(x, y) <= tau}
    assert within_tau, "the random names should contain close pairs"
    assert within_tau <= pairs


def test_passjoin_never_pairs_names_whose_lengths_differ_by_more_than_tau():
    pairs = PassJoin(tau=1).candidates({"a": "abc"}, {"b": "abcde", "c": "abcd"})

    assert pairs == {("a", "c")}


# ============================================================================ MinHash_LSH
def test_minhash_pairs_names_with_overlapping_n_grams():
    pairs = MinHashLSH(n=3, threshold=0.3).candidates(SOURCE, TARGET)

    assert ("a1", "b1") in pairs
    assert ("a3", "b3") not in pairs


def test_minhash_identical_names_always_collide_and_short_names_do_not_crash():
    pairs = MinHashLSH(n=3, threshold=0.9).candidates({"a": "antakya", "s": "x"}, {"b": "antakya", "t": ""})

    assert ("a", "b") in pairs
    assert ("a", "t") not in pairs


# ============================================================================ TFIDF_kNN
def test_tfidf_knn_pairs_each_name_with_its_most_similar_name():
    pairs = TfidfKNN(k=1).candidates(SOURCE, TARGET)

    assert {("a1", "b1"), ("a2", "b2")} <= pairs


def test_tfidf_knn_never_pairs_names_without_a_shared_n_gram():
    pairs = TfidfKNN(k=3).candidates({"a": "aaaa"}, {"b": "zzzz", "c": "aaab"})

    assert pairs == {("a", "c")}


def test_tfidf_knn_k_larger_than_the_other_side_is_fine():
    pairs = TfidfKNN(k=50).candidates(SOURCE, TARGET)

    assert pairs <= {(a, b) for a in SOURCE for b in TARGET}
    assert ("a1", "b1") in pairs


# ============================================================================ the shared kNN search
class OneHot(KNNMethod):
    """Names are "x,y" unit vectors, so the similarities are known exactly."""

    name = "OneHot"

    def vectorize(self, source_names, target_names):
        def vectors(names):
            array = np.array([[float(v) for v in name.split(",")] for name in names])
            return array / np.linalg.norm(array, axis=1, keepdims=True)
        return vectors(source_names), vectors(target_names)


KNN_SOURCE = {"east": "1,0", "north": "0,1"}
KNN_TARGET = {"east2": "1,0.1", "north2": "0.1,1", "diagonal": "1,1"}


def test_knn_takes_neighbours_in_both_directions():
    pairs = OneHot(k=1).candidates(KNN_SOURCE, KNN_TARGET)

    # each source's best target, plus each target's best source ("diagonal" ties: either source)
    assert {("east", "east2"), ("north", "north2")} <= pairs
    assert len(pairs) == 3
    assert any(target == "diagonal" for _, target in pairs)


def test_knn_without_blocked_pairs_gives_the_same_result_either_way():
    nothing_blocked = lambda start, stop: np.zeros((min(stop, 2) - start, 3), dtype=bool)  # noqa: E731

    for k in (1, 2, 3, 10):
        method = OneHot(k=k)
        assert method.candidates(KNN_SOURCE, KNN_TARGET, blocked=nothing_blocked) == \
            method.candidates(KNN_SOURCE, KNN_TARGET)


def test_knn_picks_the_best_neighbour_among_the_pairs_that_are_not_blocked():
    def blocked(start, stop):
        mask = np.zeros((2, 3), dtype=bool)
        mask[0, 0] = True  # east may not be paired with east2
        return mask[start:stop]

    pairs = OneHot(k=1).candidates(KNN_SOURCE, KNN_TARGET, blocked=blocked)

    assert ("east", "east2") not in pairs
    assert ("east", "diagonal") in pairs      # east's best allowed neighbour
    assert ("north", "east2") in pairs        # east2's best allowed neighbour


def test_knn_returns_nothing_when_every_pair_is_blocked():
    everything = lambda start, stop: np.ones((min(stop, 2) - start, 3), dtype=bool)  # noqa: E731

    assert OneHot(k=2).candidates(KNN_SOURCE, KNN_TARGET, blocked=everything) == set()


def test_knn_blocked_search_is_the_same_in_small_chunks():
    rng = np.random.default_rng(0)
    source = {f"a{i}": f"{x},{y}" for i, (x, y) in enumerate(rng.uniform(0.1, 1, (25, 2)))}
    target = {f"b{i}": f"{x},{y}" for i, (x, y) in enumerate(rng.uniform(0.1, 1, (17, 2)))}
    mask = rng.random((25, 17)) < 0.3
    blocked = lambda start, stop: mask[start:stop]  # noqa: E731

    whole, chunked = OneHot(k=3), OneHot(k=3)
    chunked.chunk = 4

    result = chunked.candidates(source, target, blocked=blocked)
    assert result == whole.candidates(source, target, blocked=blocked)
    ids_a, ids_b = list(source), list(target)
    assert not any(mask[ids_a.index(a), ids_b.index(b)] for a, b in result)


def test_knn_max_distance_drops_far_neighbours():
    method = OneHot(k=3)
    method.max_distance = 0.1

    pairs = method.candidates(KNN_SOURCE, KNN_TARGET)

    assert pairs == {("east", "east2"), ("north", "north2")}
    nothing_blocked = lambda start, stop: np.zeros((min(stop, 2) - start, 3), dtype=bool)  # noqa: E731
    assert method.candidates(KNN_SOURCE, KNN_TARGET, blocked=nothing_blocked) == pairs


# ============================================================================ LM_kNN_search
def test_lm_knn_embeds_each_list_of_names_once_per_model(monkeypatch):
    calls = []

    class FakeEncoder:
        def encode(self, names, **kwargs):
            calls.append(tuple(names))
            return np.eye(len(names), 4)

    monkeypatch.setattr(LMKNNSearch, "_encoders", {"fake-model": FakeEncoder()})
    monkeypatch.setattr(LMKNNSearch, "_embeddings", {})

    first = LMKNNSearch(model="fake-model", k=1).candidates({"a": "x", "b": "y"}, {"c": "x", "d": "y"})
    second = LMKNNSearch(model="fake-model", k=2).candidates({"a": "x", "b": "y"}, {"c": "x", "d": "y"})

    assert first == {("a", "c"), ("b", "d")}
    assert first <= second
    assert calls == [("x", "y")]  # source and target hold the same names: embedded once, then cached
