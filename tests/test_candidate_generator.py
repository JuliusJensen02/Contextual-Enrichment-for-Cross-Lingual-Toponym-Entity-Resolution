"""candidate_generation/candidate_generator.py: names, record pairs, geo filter, evaluation."""
import numpy as np
import pytest

from base import BlockingMethod
from candidate_generator import CandidateGenerator, _distances, _km, _points, within_distance
from data_loader import DatasetName
from methods import PassJoin, TfidfKNN

KIMA, YAQUT, THURAYYA = DatasetName.KIMA, DatasetName.YAQUT, DatasetName.THURAYYA

COPENHAGEN, AARHUS, PARIS = (55.6761, 12.5683), (56.1629, 10.2039), (48.8566, 2.3522)


class Recorder(BlockingMethod):
    """Pairs every name with every name, and remembers what it was given."""

    name = "Recorder"

    def candidates(self, source, target):
        self.source, self.target = source, target
        return {(a, b) for a in source for b in target}


class RawRecorder(Recorder):
    raw_names = True


def place(record_id, title, ipa="", point=None, variants=""):
    lat, lon = map(str, point) if point else ("", "")
    return {"id": record_id, "title": title, "title_ipa": ipa, "name_variants": variants, "lat": lat, "lon": lon}


@pytest.fixture
def kima(dataset_factory):
    return dataset_factory(KIMA, [
        place("k1", "København", "kopenhavn", COPENHAGEN, variants="Copenhagen"),
        place("k2", "Århus", "orhus", AARHUS),
        place("k3", "Nowhere", "nouer"),
    ])


@pytest.fixture
def yaqut(dataset_factory):
    return dataset_factory(YAQUT, [
        place("y1", "Kopenhagen", "kopenhagn", COPENHAGEN),
        place("y2", "Paris", "pari | paris", PARIS),
    ])


# ============================================================================ what the methods get
def test_letter_based_methods_get_the_normalized_ipa_by_default(kima, yaqut):
    method = Recorder()

    CandidateGenerator([kima, yaqut], method, max_km=None).generate()

    assert method.source == {("k1", 0): "kopenhavn", ("k2", 0): "orhus", ("k3", 0): "nouer"}
    assert method.target == {("y1", 0): "kopenhagn", ("y2", 0): "pari", ("y2", 1): "paris"}


def test_phonetic_off_gives_the_normalized_title_and_never_the_variants(kima, yaqut):
    method = Recorder()

    CandidateGenerator([kima, yaqut], method, phonetic=False, max_km=None).generate()

    assert method.source == {("k1", 0): "københavn", ("k2", 0): "arhus", ("k3", 0): "nowhere"}
    assert "copenhagen" not in method.source.values()


def test_raw_name_methods_get_the_title_as_written_even_with_phonetic_on(kima, yaqut):
    method = RawRecorder()

    CandidateGenerator([kima, yaqut], method, phonetic=True, max_km=None).generate()

    assert method.source == {("k1", 0): "København", ("k2", 0): "Århus", ("k3", 0): "Nowhere"}


def test_records_without_a_name_are_left_out(dataset_factory, yaqut):
    kima = dataset_factory(KIMA, [place("k1", "Something", ipa=""), place("k2", "Other", ipa="oter")])
    method = Recorder()

    pairs = CandidateGenerator([kima, yaqut], method, max_km=None).generate()

    assert list(method.source) == [("k2", 0)]
    assert {a for a, _ in pairs} == {"k2"}


@pytest.mark.parametrize("raw, expected", [
    ("Ḥalab", "halab"),
    ("  SAINT-Étienne  ", "saint etienne"),
    ("دِمَشْق", "دمشق"),             # Arabic short vowels
    ("محـــمد", "محمد"),             # tatweel
    ("יְרוּשָׁלַיִם", "ירושלים"),        # Hebrew vowel points
    ("al-Qāhira (Egypt)", "al qahira egypt"),
    ("", ""),
])
def test_normalize(raw, expected):
    assert CandidateGenerator._normalize(raw) == expected


def test_name_pairs_become_record_pairs(kima, yaqut):
    pairs = CandidateGenerator([kima, yaqut], Recorder(), max_km=None).generate()

    assert pairs == {(a, b) for a in ("k1", "k2", "k3") for b in ("y1", "y2")}


# ============================================================================ geo filter
def test_km_matches_known_distances():
    assert _km(COPENHAGEN, COPENHAGEN) == 0
    assert _km(COPENHAGEN, AARHUS) == pytest.approx(157, abs=3)
    assert _km(COPENHAGEN, PARIS) == pytest.approx(1026, abs=10)
    assert _km(COPENHAGEN, PARIS) == pytest.approx(_km(PARIS, COPENHAGEN))


def test_within_distance_keeps_close_pairs_and_pairs_without_coordinates(kima, yaqut):
    every_pair = {(a, b) for a in kima.ids for b in yaqut.ids}

    assert within_distance(every_pair, kima, yaqut, 100) == {("k1", "y1"), ("k3", "y1"), ("k3", "y2")}
    assert within_distance(every_pair, kima, yaqut, 200) == {("k1", "y1"), ("k2", "y1"), ("k3", "y1"), ("k3", "y2")}
    assert within_distance(every_pair, kima, yaqut, 5000) == every_pair


def test_within_distance_uses_the_closest_two_points(dataset_factory, yaqut):
    kima = dataset_factory(KIMA, [{"id": "k1", "title": "x", "lat": "48.8566 | 55.6761", "lon": "2.3522 | 12.5683"}])

    assert within_distance({("k1", "y1"), ("k1", "y2")}, kima, yaqut, 1) == {("k1", "y1"), ("k1", "y2")}


def test_vectorized_distances_agree_with_the_scalar_formula(dataset_factory):
    a = dataset_factory(KIMA, [
        place("a1", "x", point=COPENHAGEN),
        {"id": "a2", "title": "x", "lat": "48.8566 | 56.1629", "lon": "2.3522 | 10.2039"},
        place("a3", "x"),
    ])
    b = dataset_factory(YAQUT, [place("b1", "x", point=AARHUS), place("b2", "x", point=PARIS), place("b3", "x")])

    distances = _distances(_points(a, a.ids), _points(b, b.ids))

    assert distances.shape == (3, 3)
    assert distances[0, 0] == pytest.approx(_km(COPENHAGEN, AARHUS), rel=1e-4)
    assert distances[0, 1] == pytest.approx(_km(COPENHAGEN, PARIS), rel=1e-4)
    assert distances[1, 0] == pytest.approx(0, abs=1e-2)   # the closest of the record's two points
    assert distances[1, 1] == pytest.approx(0, abs=1e-2)
    assert np.isnan(distances[2]).all() and np.isnan(distances[:, 2]).all()


def test_points_of_a_dataset_without_any_coordinates(dataset_factory):
    dataset = dataset_factory(KIMA, [place("a", "x"), place("b", "y")])

    points = _points(dataset, dataset.ids)

    assert points.shape == (2, 1, 2) and np.isnan(points).all()
    assert np.isnan(_distances(points, points)).all()


def test_geo_filter_is_applied_to_the_candidates_of_a_method(kima, yaqut):
    generator = CandidateGenerator([kima, yaqut], Recorder())  # max_km defaults to 100

    assert generator.generate() == {("k1", "y1"), ("k3", "y1"), ("k3", "y2")}


def test_knn_methods_pick_their_neighbours_after_the_geo_filter(dataset_factory):
    # "antakya" in Paris is the best match by name, but only the Copenhagen record is close enough.
    source = dataset_factory(KIMA, [place("s", "x", "antakya", COPENHAGEN)])
    target = dataset_factory(YAQUT, [
        place("far", "x", "antakya", PARIS),
        place("near", "x", "antakia", COPENHAGEN),
    ])

    without_geo = CandidateGenerator([source, target], TfidfKNN(k=1), max_km=None).generate()
    with_geo = CandidateGenerator([source, target], TfidfKNN(k=1), max_km=100).generate()

    assert ("s", "far") in without_geo
    assert with_geo == {("s", "near")}


def test_geo_first_and_geo_afterwards_agree_when_k_covers_everything(kima, yaqut):
    knn = CandidateGenerator([kima, yaqut], TfidfKNN(k=10), max_km=100).generate()
    unfiltered = CandidateGenerator([kima, yaqut], TfidfKNN(k=10), max_km=None).generate()

    assert knn == within_distance(unfiltered, kima, yaqut, 100)


# ============================================================================ several datasets
def test_generate_needs_source_and_target_with_more_than_two_datasets(kima, yaqut, dataset_factory):
    thurayya = dataset_factory(THURAYYA, [place("t1", "Kobenhavn", "kopenhavn", COPENHAGEN)])
    generator = CandidateGenerator([kima, yaqut, thurayya], PassJoin(tau=1))

    with pytest.raises(ValueError):
        generator.generate()
    assert generator.generate(KIMA, THURAYYA) == {("k1", "t1")}
    assert generator.generate(THURAYYA, KIMA) == {("t1", "k1")}


def test_all_pairs_runs_every_pair_of_datasets_in_order(kima, yaqut, dataset_factory):
    thurayya = dataset_factory(THURAYYA, [place("t1", "Kobenhavn", "kopenhavn", COPENHAGEN)])

    results = CandidateGenerator([kima, yaqut, thurayya], PassJoin(tau=1)).all_pairs()

    assert list(results) == [(KIMA, YAQUT), (KIMA, THURAYYA), (YAQUT, THURAYYA)]
    assert results[(KIMA, YAQUT)] == {("k1", "y1")}
    assert results[(YAQUT, THURAYYA)] == {("y1", "t1")}


def test_the_same_dataset_twice_is_rejected(kima):
    with pytest.raises(ValueError):
        CandidateGenerator([kima, kima], PassJoin())


# ============================================================================ evaluation
def test_evaluate():
    truth = {("a", "x"), ("b", "y"), ("c", "z"), ("d", "w")}
    candidates = [("a", "x"), ("b", "y"), ("a", "y"), ("a", "x")]  # a duplicate counts once

    result = CandidateGenerator.evaluate(candidates, truth, n_source=10, n_target=10)

    assert result == {"PC": 0.5, "PQ": pytest.approx(2 / 3), "RR": pytest.approx(0.97), "candidates": 3}


def test_evaluate_without_candidates_or_ground_truth():
    assert CandidateGenerator.evaluate(set(), {("a", "x")}, 2, 2) == {"PC": 0.0, "PQ": 0.0, "RR": 1.0, "candidates": 0}
    assert CandidateGenerator.evaluate({("a", "x")}, set(), 2, 2)["PC"] == 0.0
