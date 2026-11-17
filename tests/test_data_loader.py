"""data_loader: Dataset, GroundTruth, TestSet and TestSetLoader."""
import pandas as pd
import pytest

from data_loader import CandidateSet, DatasetName, GroundTruth, TestSet, TestSetLoader, TestSetName

KIMA, YAQUT, THURAYYA = DatasetName.KIMA, DatasetName.YAQUT, DatasetName.THURAYYA


def internal_links(rows) -> pd.DataFrame:
    """A MEHDIE ground truth table from (link_type, source_id, source, target_id, target) rows."""
    return pd.DataFrame(rows, columns=GroundTruth.COLUMNS, dtype=str)


# ============================================================================ Dataset
def test_names_put_the_title_first_and_split_all_variant_separators(dataset_factory):
    dataset = dataset_factory(KIMA, [
        {"id": "1", "title": "Antakya", "name_variants": "Antioch | Antiochia; Antakiya، أنطاكية"},
    ])

    assert dataset.names["1"] == ["Antakya", "Antioch", "Antiochia", "Antakiya", "أنطاكية"]


def test_names_drop_duplicates_blanks_language_tags_and_trailing_qualifiers(dataset_factory):
    dataset = dataset_factory(DatasetName.PLEIADES, [
        {"id": "1", "title": "Aethusa (island)", "name_variants": "Aethusa | Ἄλπεις@grc |  | Alpes@la-x"},
    ])

    assert dataset.names["1"] == ["Aethusa", "Ἄλπεις", "Alpes"]


def test_names_include_the_wikipedia_title_when_the_dataset_has_one(dataset_factory):
    dataset = dataset_factory(DatasetName.WIKIDATA_RU, [
        {"id": "Q1", "title": "Москва", "name_variants": "Moskva", "wiki_title": "Москва (город)"},
        {"id": "Q2", "title": "Казань", "name_variants": "", "wiki_title": "Казань"},
    ])

    assert dataset.names == {"Q1": ["Москва", "Moskva"], "Q2": ["Казань"]}


def test_phonetic_splits_on_pipes_and_drops_blanks_and_duplicates(dataset_factory):
    dataset = dataset_factory(DatasetName.TRISMEGISTOS, [
        {"id": "1", "title_ipa": "memfis | mempʰis | memfis"},
        {"id": "2", "title_ipa": ""},
    ])

    assert dataset.phonetic == {"1": ["memfis", "mempʰis"], "2": []}


def test_coordinates_can_be_missing_single_or_several(dataset_factory):
    dataset = dataset_factory(KIMA, [
        {"id": "none"},
        {"id": "one", "lat": "31.5", "lon": "34.25"},
        {"id": "pipes", "lat": "10 | 11", "lon": "20 | 21"},
        {"id": "semicolons", "lat": "10; 11", "lon": "20; 21"},
    ])

    assert dataset.coordinates == {
        "none": [],
        "one": [(31.5, 34.25)],
        "pipes": [(10.0, 20.0), (11.0, 21.0)],
        "semicolons": [(10.0, 20.0), (11.0, 21.0)],
    }


def test_len_contains_ids_and_label(dataset_factory):
    dataset = dataset_factory(KIMA, [{"id": "007"}, {"id": "8"}])

    assert len(dataset) == 2
    assert dataset.ids == ["007", "8"]
    assert "007" in dataset and "7" not in dataset
    assert dataset.label == "Kima"
    assert repr(dataset) == "Dataset(KIMA, 2 records)"


def test_filter_and_subset_return_new_datasets(dataset_factory):
    dataset = dataset_factory(KIMA, [
        {"id": "a", "lat": "1", "lon": "1"},
        {"id": "b"},
        {"id": "c", "lat": "3", "lon": "3"},
    ])

    with_coordinates = dataset.filter(dataset.frame.lat != "")
    reordered = dataset.subset(["c", "a"])

    assert with_coordinates.ids == ["a", "c"]
    assert reordered.ids == ["c", "a"]          # the given order, not the row order
    assert reordered.coordinates == {"c": [(3.0, 3.0)], "a": [(1.0, 1.0)]}
    assert reordered.name is KIMA
    assert dataset.ids == ["a", "b", "c"]       # the original is untouched


# ============================================================================ GroundTruth
def test_mehdie_ground_truth_only_counts_same_as_rows_as_links():
    truth = GroundTruth(TestSetName.MEHDIE, internal_links([
        ("same_as", "1", "Kima", "10", "Yaqut"),
        ("different", "2", "Kima", "20", "Yaqut"),
        ("same_as", "3", "Yaqut", "30", "Thurayya"),
    ]))

    assert len(truth) == 3
    assert truth.links == {((KIMA, "1"), (YAQUT, "10")), ((YAQUT, "3"), (THURAYYA, "30"))}


def test_pleiades_trismegistos_ground_truth_is_normalized():
    raw = pd.DataFrame({"pleiades_id": ["100", "200"], "trismegistos_id": ["7", "8"],
                        "pleiades_title": ["a", "b"], "sources": ["x", "y"]})

    truth = GroundTruth(TestSetName.PLEIADES_TRISMEGISTOS, raw)

    assert list(truth.frame.columns) == GroundTruth.COLUMNS
    assert set(truth.frame["link_type"]) == {"same_as"}
    assert truth.links == {((DatasetName.PLEIADES, "100"), (DatasetName.TRISMEGISTOS, "7")),
                           ((DatasetName.PLEIADES, "200"), (DatasetName.TRISMEGISTOS, "8"))}


def test_wikidata_ground_truth_is_normalized():
    raw = pd.DataFrame({"id_1": ["Q1"], "id_2": ["Q1"]})

    truth = GroundTruth(TestSetName.WIKIDATA_ZH_RU, raw)

    assert truth.links == {((DatasetName.WIKIDATA_ZH, "Q1"), (DatasetName.WIKIDATA_RU, "Q1"))}


# ============================================================================ TestSet
@pytest.fixture
def mehdie(dataset_factory) -> TestSet:
    kima = dataset_factory(KIMA, [{"id": f"k{i}"} for i in range(6)])
    yaqut = dataset_factory(YAQUT, [{"id": f"y{i}"} for i in range(6)])
    thurayya = dataset_factory(THURAYYA, [{"id": f"t{i}"} for i in range(6)])
    truth = GroundTruth(TestSetName.MEHDIE, internal_links([
        ("same_as", "k0", "Kima", "y0", "Yaqut"),
        ("same_as", "y0", "Yaqut", "k0", "Kima"),         # the same link, listed the other way
        ("same_as", "k1", "Kima", "y1", "Yaqut"),
        ("same_as", "y2", "Yaqut", "t2", "Thurayya"),
        ("same_as", "k3", "Kima", "t3", "Thurayya"),
        ("same_as", "k4", "Kima", "missing", "Yaqut"),     # the Yaqut record is not in the dataset
        ("different", "k5", "Kima", "y5", "Yaqut"),
    ]))
    return TestSet(TestSetName.MEHDIE, [kima, yaqut, thurayya], truth)


def test_links_count_once_and_need_both_records(mehdie):
    assert len(mehdie.links) == 4
    assert all((KIMA, "k4") not in link for link in mehdie.links)


def test_pairs_are_every_combination_of_the_datasets(mehdie):
    assert mehdie.pairs == [(KIMA, YAQUT), (KIMA, THURAYYA), (YAQUT, THURAYYA)]


def test_links_between_follows_the_requested_direction(mehdie):
    assert mehdie.links_between(KIMA, YAQUT) == {("k0", "y0"), ("k1", "y1")}
    assert mehdie.links_between(YAQUT, KIMA) == {("y0", "k0"), ("y1", "k1")}
    assert mehdie.links_between(YAQUT, THURAYYA) == {("y2", "t2")}
    assert mehdie.dataset(THURAYYA).label == "Thurayya"


def test_sample_keeps_the_linked_records_and_adds_unlinked_distractors(mehdie):
    sample = mehdie.sample(n_links=2, n_distractors=1, seed=13)

    assert len(sample.links) >= 2
    assert sample.links <= mehdie.links
    linked = {end for link in mehdie.links for end in link}
    for dataset in sample.datasets:
        distractors = [rid for rid in dataset.ids if (dataset.name, rid) not in linked]
        assert len(distractors) == 1
        assert dataset.ids == sorted(dataset.ids)
    for link in sample.links:  # both records of every kept link are in the sample
        assert all(rid in sample.dataset(name) for name, rid in link)


def test_sample_is_reproducible_and_depends_on_the_seed(mehdie):
    def ids(test_set):
        return [dataset.ids for dataset in test_set.datasets]

    assert ids(mehdie.sample(2, 1, seed=13)) == ids(mehdie.sample(2, 1, seed=13))
    assert any(ids(mehdie.sample(2, 1, seed=13)) != ids(mehdie.sample(2, 1, seed=seed)) for seed in range(20))


def test_sample_asking_for_more_than_there_is_returns_everything(mehdie):
    sample = mehdie.sample(n_links=1000, n_distractors=1000, seed=1)

    assert sample.links == mehdie.links
    assert [len(dataset) for dataset in sample.datasets] == [6, 6, 6]


# ============================================================================ TestSetLoader
def test_loader_reads_strings_only_and_keeps_empty_cells_empty(tmp_path):
    folder = tmp_path / "02_minimized_datasets" / "Wikidata-zh-ru"
    folder.mkdir(parents=True)
    header = "id\ttitle\ttitle_ipa\tname_variants\tlat\tlon\n"
    (folder / "wikidata_zh.tsv").write_text(header + "007\t北京\tpeitɕiŋ\tNA\t\t\n", encoding="utf8")
    (folder / "wikidata_ru.tsv").write_text(header + "007\tПекин\tpʲekʲin\t\t39.9\t116.4\n", encoding="utf8")
    em = tmp_path / "em" / "Wikidata-zh-ru"
    em.mkdir(parents=True)
    (em / "em.tsv").write_text("id_1\tid_2\n007\t007\n", encoding="utf8")

    test_set = TestSetLoader(tmp_path).load(TestSetName.WIKIDATA_ZH_RU)

    zh = test_set.dataset(DatasetName.WIKIDATA_ZH)
    assert zh.ids == ["007"]                      # the leading zeros survive
    assert zh.frame.loc[0, "lat"] == ""           # not NaN
    assert zh.frame.loc[0, "name_variants"] == "NA"  # not read as a missing value
    assert test_set.links_between(DatasetName.WIKIDATA_ZH, DatasetName.WIKIDATA_RU) == {("007", "007")}


# ============================================================================ the real files
SHARED_COLUMNS = ["id", "title", "title_ipa", "name_variants", "lat", "lon"]


@pytest.mark.parametrize("name", list(TestSetName), ids=lambda name: name.name)
def test_the_datasets_in_the_repo_load_and_are_consistent(name):
    test_set = TestSetLoader().load(name)

    assert [dataset.name for dataset in test_set.datasets] == list(name.datasets)
    assert test_set.links, "no ground truth link has both its records in the datasets"
    for dataset in test_set.datasets:
        assert len(dataset) > 0
        assert set(SHARED_COLUMNS) <= set(dataset.frame.columns)
        assert len(set(dataset.ids)) == len(dataset.ids), f"{dataset.label} has duplicate ids"
        assert all(dataset.ids), f"{dataset.label} has a record without an id"
        assert len(dataset.coordinates) == len(dataset)  # every lat / lon cell parses
        for points in dataset.coordinates.values():
            assert all(-90 <= lat <= 90 and -180 <= lon <= 180 for lat, lon in points)
    for source, target in test_set.pairs:
        for source_id, target_id in test_set.links_between(source, target):
            assert source_id in test_set.dataset(source) and target_id in test_set.dataset(target)


# ============================================================================ CandidateSet
@pytest.fixture
def candidate_set(dataset_factory):
    source = dataset_factory(KIMA, [{"id": "k1", "title": "Akko", "lat": "32.9"}, {"id": "k2", "title": "Yafo"}])
    target = dataset_factory(YAQUT, [{"id": "y1", "title": "عكا"}, {"id": "y2", "title": "يافا"}])
    return CandidateSet(source, target, {"k1": ["y2", "y1"], "k2": []}, links={("k1", "y1")})


def test_candidate_set_lists_its_pairs_in_the_stored_order(candidate_set):
    assert candidate_set.pairs == [("k1", "y2"), ("k1", "y1")]
    assert len(candidate_set) == 2
    assert candidate_set.links == {("k1", "y1")}


def test_records_hold_the_id_and_only_the_chosen_columns(candidate_set):
    records = list(candidate_set.records(["title"]))

    assert records == [
        ({"id": "k1", "title": "Akko"}, [{"id": "y2", "title": "يافا"}, {"id": "y1", "title": "عكا"}]),
        ({"id": "k2", "title": "Yafo"}, []),
    ]


def test_records_can_take_other_columns_for_the_target_and_default_to_all(candidate_set):
    record, candidates = next(candidate_set.records(["title", "lat"], target_columns=[]))
    assert record == {"id": "k1", "title": "Akko", "lat": "32.9"}
    assert candidates == [{"id": "y2"}, {"id": "y1"}]

    record, _ = next(candidate_set.records())
    assert list(record) == list(candidate_set.source.frame.columns)


def test_frame_has_one_row_per_pair_with_prefixed_columns(candidate_set):
    frame = candidate_set.frame(["title"])

    assert list(frame.columns) == ["source_id", "source_title", "target_id", "target_title"]
    assert frame.values.tolist() == [["k1", "Akko", "y2", "يافا"], ["k1", "Akko", "y1", "عكا"]]


def test_an_unknown_column_is_reported(candidate_set):
    with pytest.raises(KeyError, match="no column"):
        list(candidate_set.records(["population"]))


@pytest.mark.parametrize("name", list(TestSetName), ids=lambda name: name.name)
def test_the_candidates_in_the_repo_load_and_refer_to_known_records(name):
    for candidate_set in TestSetLoader().load_candidates(name):
        assert list(candidate_set.candidates) == candidate_set.source.ids
        assert all(target_id in candidate_set.target for _, target_id in candidate_set.pairs)
        assert len(set(candidate_set.pairs)) == len(candidate_set.pairs)
