"""candidate_generation/pipeline.py, with the language model replaced by known vectors."""
import numpy as np
import pytest

import pipeline
from data_loader import DatasetName
from methods import LMKNNSearch

KIMA, YAQUT = DatasetName.KIMA, DatasetName.YAQUT
COPENHAGEN, PARIS = ("55.6761", "12.5683"), ("48.8566", "2.3522")

# The "embedding" of every title used below: unit vectors, so the dot product is the cosine.
EMBEDDINGS = {
    "alpha": [1.0, 0.0, 0.0], "alpha2": [1.0, 0.0, 0.0],
    "beta": [0.0, 1.0, 0.0], "beta2": [0.0, 1.0, 0.0],
    "gamma": [0.0, 0.0, 1.0], "gamma2": [0.0, 0.0, 1.0],
}


@pytest.fixture(autouse=True)
def fake_language_model(monkeypatch):
    def embed(self, names):
        return np.array([EMBEDDINGS[name] for name in names], dtype=np.float32)
    monkeypatch.setattr(LMKNNSearch, "_embed", embed)


def record(record_id, title, ipa, point=("", "")):
    return {"id": record_id, "title": title, "title_ipa": ipa, "lat": point[0], "lon": point[1]}


@pytest.fixture
def source(dataset_factory):
    return dataset_factory(KIMA, [
        record("a", "alpha", "alfa", COPENHAGEN),
        record("b", "beta", "beta", COPENHAGEN),
        record("c", "gamma", "gama", COPENHAGEN),
    ])


@pytest.fixture
def target(dataset_factory):
    return dataset_factory(YAQUT, [
        record("a2", "alpha2", "alfa", COPENHAGEN),
        record("b2", "beta2", "beta", COPENHAGEN),
        record("c2", "gamma2", "gama", COPENHAGEN),
    ])


def test_each_record_is_paired_with_its_best_match(source, target):
    pairs = pipeline.CandidatePipeline([source, target], k=1).generate()

    assert pairs == {("a", "a2"), ("b", "b2"), ("c", "c2")}


def test_pairs_with_a_score_of_zero_are_never_candidates(source, target):
    # k covers everything, but only the matching records share a title vector or an IPA n-gram
    pairs = pipeline.CandidatePipeline([source, target], k=3, title_weight=1.0).generate()

    assert pairs == {("a", "a2"), ("b", "b2"), ("c", "c2")}


def test_title_weight_decides_which_similarity_counts(dataset_factory):
    source = dataset_factory(KIMA, [record("a", "alpha", "beta")])
    target = dataset_factory(YAQUT, [record("same_title", "alpha2", "zzzz"), record("same_sound", "gamma", "beta")])

    def generate(weight):
        return pipeline.CandidatePipeline([source, target], k=1, title_weight=weight).generate()

    # k is per record in both directions, so compare what the source record itself keeps
    assert ("a", "same_title") in generate(1.0) and ("a", "same_sound") not in generate(1.0)
    assert ("a", "same_sound") in generate(0.0) and ("a", "same_title") not in generate(0.0)


def test_the_geo_filter_drops_far_pairs_but_keeps_records_without_coordinates(dataset_factory):
    source = dataset_factory(KIMA, [record("a", "alpha", "alfa", COPENHAGEN)])
    target = dataset_factory(YAQUT, [
        record("far", "alpha2", "alfa", PARIS),
        record("unknown", "alpha2", "alfa"),
    ])

    assert pipeline.CandidatePipeline([source, target], k=5).generate() == {("a", "unknown")}
    assert pipeline.CandidatePipeline([source, target], k=5, max_km=2000).generate() == {("a", "far"), ("a", "unknown")}


def test_a_pair_is_kept_if_either_side_keeps_it(dataset_factory):
    source = dataset_factory(KIMA, [record("a1", "alpha", "alfa"), record("a2", "alpha", "alfa")])
    target = dataset_factory(YAQUT, [record("b", "alpha2", "alfa")])

    # "b" keeps only one of the two, but each source record keeps "b"
    assert pipeline.CandidatePipeline([source, target], k=1).generate() == {("a1", "b"), ("a2", "b")}


def test_scoring_in_chunks_gives_the_same_candidates(dataset_factory, monkeypatch):
    rng = np.random.default_rng(1)
    titles = list(EMBEDDINGS)
    letters = ["alfa", "beta", "gama", "delta", "alba", "meta"]

    def random_dataset(name, n):
        return dataset_factory(name, [
            record(f"{name.label}{i}", titles[rng.integers(len(titles))], letters[rng.integers(len(letters))],
                   (str(55 + rng.uniform(0, 2)), str(12 + rng.uniform(0, 2))))
            for i in range(n)])

    source, target = random_dataset(KIMA, 23), random_dataset(YAQUT, 11)
    whole = pipeline.CandidatePipeline([source, target], k=2).generate()

    monkeypatch.setattr(pipeline, "CHUNK", 5)
    chunked = pipeline.CandidatePipeline([source, target], k=2).generate()

    assert len(chunked) == len(whole)  # ties may be broken differently, the amount of work may not
    assert {a for a, _ in chunked} == {a for a, _ in whole} == set(source.ids)


def test_all_pairs_is_keyed_by_dataset_pair(source, target):
    results = pipeline.CandidatePipeline([source, target], k=1).all_pairs()

    assert list(results) == [(KIMA, YAQUT)]
    assert results[(KIMA, YAQUT)] == {("a", "a2"), ("b", "b2"), ("c", "c2")}


def test_pipeline_distances_match_the_candidate_generator(source, target):
    import candidate_generator

    ours = pipeline._distances(pipeline._points(source), pipeline._points(target))
    theirs = candidate_generator._distances(candidate_generator._points(source, source.ids),
                                            candidate_generator._points(target, target.ids))

    assert np.allclose(ours, theirs, equal_nan=True)
