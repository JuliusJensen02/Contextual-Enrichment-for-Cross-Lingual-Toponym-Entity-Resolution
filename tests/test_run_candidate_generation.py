"""candidate_generation/run_candidate_generation.py: building the runs and the result table."""
import csv
import sys
from argparse import Namespace

import pytest

import run_candidate_generation as runner
from data_loader import DatasetName, GroundTruth, TestSet, TestSetName
from methods import LMKNNSearch, PassJoin

KIMA, YAQUT, THURAYYA = DatasetName.KIMA, DatasetName.YAQUT, DatasetName.THURAYYA


def arguments(**overrides) -> Namespace:
    defaults = dict(methods=runner.ALL_METHODS, qgram_q=[3], qgram_t=[0.6], qgram_max_keys=[500], tau=[1],
                    minhash_n=[3], minhash_threshold=[0.3], minhash_num_perm=[128], tfidf_ngrams=["2-3"],
                    k=[3], model="sentence-transformers/LaBSE")
    return Namespace(**(defaults | overrides))


# ============================================================================ build_methods
def test_build_methods_makes_one_run_per_method_with_the_defaults():
    runs = runner.build_methods(arguments())

    assert [method.name for method, _ in runs] == runner.ALL_METHODS
    assert [params for _, params in runs] == ["q=3,t=0.6", "tau=1", "n=3,thr=0.3", "k=3", "k=3"]


def test_build_methods_makes_one_run_per_parameter_value():
    runs = runner.build_methods(arguments(methods=["PassJoin", "TFIDF_kNN"], tau=[0, 1, 2],
                                          k=[1, 5], tfidf_ngrams=["2-3", "1-2"]))

    assert [params for _, params in runs] == ["tau=0", "tau=1", "tau=2", "k=1", "k=5", "k=1,n=1-2", "k=5,n=1-2"]
    assert [method.tau for method, _ in runs[:3]] == [0, 1, 2]
    assert runs[-1][0].ngram_range == (1, 2) and runs[-1][0].k == 5


def test_build_methods_only_names_parameters_that_are_not_the_default():
    runs = runner.build_methods(arguments(methods=["Q_grams", "MinHash_LSH"], qgram_max_keys=[50],
                                          minhash_num_perm=[64]))

    assert [params for _, params in runs] == ["q=3,t=0.6,keys=50", "n=3,thr=0.3,perm=64"]


def test_inputs_for():
    assert runner.inputs_for(PassJoin(), "on") == ["ipa"]
    assert runner.inputs_for(PassJoin(), "off") == ["names"]
    assert runner.inputs_for(PassJoin(), "both") == ["ipa", "names"]
    assert runner.inputs_for(LMKNNSearch(), "on") == ["names"]  # the language model never gets IPA


# ============================================================================ report
@pytest.fixture
def by_name(dataset_factory):
    return {
        KIMA: dataset_factory(KIMA, [{"id": f"k{i}"} for i in range(10)]),
        YAQUT: dataset_factory(YAQUT, [{"id": f"y{i}"} for i in range(10)]),
        THURAYYA: dataset_factory(THURAYYA, [{"id": f"t{i}"} for i in range(5)]),
    }


def test_report_for_one_pair_has_one_row_and_no_total(by_name):
    results = {(KIMA, YAQUT): {("k0", "y0"), ("k1", "y9")}}
    truth = {(KIMA, YAQUT): {("k0", "y0"), ("k2", "y2")}}

    rows = runner.report(results, truth, by_name, per_pair=True)

    assert rows == [{"pair": "Kima-Yaqut", "truth": 2, "PC": 0.5, "PQ": 0.5, "RR": pytest.approx(0.98),
                     "candidates": 2}]


def test_report_totals_several_pairs(by_name):
    results = {(KIMA, YAQUT): {("k0", "y0"), ("k1", "y9")}, (KIMA, THURAYYA): {("k0", "t0")}}
    truth = {(KIMA, YAQUT): {("k0", "y0"), ("k2", "y2")}, (KIMA, THURAYYA): set()}

    rows = runner.report(results, truth, by_name, per_pair=True)

    assert [row["pair"] for row in rows] == ["Kima-Yaqut", "Kima-Thurayya", "ALL PAIRS"]
    assert rows[1]["PC"] is None  # no ground truth between these two: PC is undefined
    assert rows[2] == {"pair": "ALL PAIRS", "truth": 2, "PC": 0.5, "PQ": pytest.approx(1 / 3),
                       "RR": pytest.approx(1 - 3 / 150), "candidates": 3}


def test_report_without_per_pair_only_gives_the_total(by_name):
    results = {(KIMA, YAQUT): set(), (KIMA, THURAYYA): set()}
    truth = {(KIMA, YAQUT): set(), (KIMA, THURAYYA): set()}

    rows = runner.report(results, truth, by_name, per_pair=False)

    assert rows == [{"pair": "ALL PAIRS", "truth": 0, "PC": None, "PQ": 0, "RR": 1.0, "candidates": 0}]


# ============================================================================ the whole run
def test_main_runs_a_test_set_and_writes_the_table(dataset_factory, monkeypatch, tmp_path, capsys):
    kima = dataset_factory(KIMA, [
        {"id": "k1", "title": "Antakya", "title_ipa": "antakja"},
        {"id": "k2", "title": "Halab", "title_ipa": "halab"},
    ])
    yaqut = dataset_factory(YAQUT, [
        {"id": "y1", "title": "Antakia", "title_ipa": "antakia"},
        {"id": "y2", "title": "Baghdad", "title_ipa": "bagdad"},
    ])
    thurayya = dataset_factory(THURAYYA, [{"id": "t1", "title": "Halab", "title_ipa": "halab"}])
    truth = GroundTruth(TestSetName.MEHDIE, __import__("pandas").DataFrame(
        [("same_as", "k1", "Kima", "y1", "Yaqut"), ("same_as", "k2", "Kima", "t1", "Thurayya")],
        columns=GroundTruth.COLUMNS))
    test_set = TestSet(TestSetName.MEHDIE, [kima, yaqut, thurayya], truth)

    class FakeLoader:
        def load(self, name):
            assert name is TestSetName.MEHDIE
            return test_set

    out = tmp_path / "results.csv"
    monkeypatch.setattr(runner, "LOADER", FakeLoader())
    monkeypatch.setattr(sys, "argv", ["run_candidate_generation.py", "--testset", "mehdie", "--full",
                                      "--methods", "PassJoin", "--tau", "0", "1", "--per-pair",
                                      "--show", "1", "--out", str(out)])

    runner.main()

    with out.open(encoding="utf8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert list(rows[0]) == runner.CSV_COLUMNS
    totals = {row["params"]: row for row in rows if row["pair"] == "ALL PAIRS"}
    assert totals["tau=0"]["PC"] == "0.5" and totals["tau=0"]["candidates"] == "1"   # only halab = halab
    assert totals["tau=1"]["PC"] == "1.0"                                            # antakja ~ antakia too
    assert {row["input"] for row in rows} == {"ipa"} and {row["max_km"] for row in rows} == {"100"}
    printed = capsys.readouterr().out
    assert "3 dataset pair(s)" in printed
    assert "missed: Antakya  <->  Antakia" in printed
