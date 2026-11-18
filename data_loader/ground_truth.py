import pandas as pd

from .names import DatasetName, TestSetName

# One end of a ground truth link: which dataset, which record.
End = tuple[DatasetName, str]

SAME_AS = "same_as"


class GroundTruth:
    """The ground truth of one test set, in one format whatever the file on disk looks like.

    The files in datasets/em/ each have their own columns. They are normalized here, when
    loaded; the files themselves are left as they are. `frame` always has these columns:

        link_type        "same_as" for a match. MEHDIE also has other relations
                         ("different", "located_in", ...); the other files only hold matches.
        source_place_id  the record id in the source dataset
        source_dataset   the source dataset's label (DatasetName.label), e.g. "Kima"
        target_place_id  the record id in the target dataset
        target_dataset   the target dataset's label, e.g. "Yaqut"

        truth = TestSetLoader().load(TestSetName.PLEIADES_TRISMEGISTOS).ground_truth
        truth.frame      # the normalized table
        truth.links      # the matches: {((DatasetName, id), (DatasetName, id)), ...}
    """

    COLUMNS = ["link_type", "source_place_id", "source_dataset", "target_place_id", "target_dataset"]

    def __init__(self, name: TestSetName, raw: pd.DataFrame):
        """raw: the ground truth file as read from disk (strings only)."""
        self.name = name
        self.frame = NORMALIZERS[name](raw)[self.COLUMNS].reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.frame)

    def __repr__(self) -> str:
        return f"GroundTruth({self.name.name}: {len(self)} rows, {len(self.links)} matches)"

    @property
    def links(self) -> set[tuple[End, End]]:
        """The matches (the same_as rows), each as a pair of (DatasetName, record id) ends."""
        by_label = {dataset.label: dataset for dataset in DatasetName}
        same = self.frame[self.frame["link_type"] == SAME_AS]
        return {((by_label[source], source_id), (by_label[target], target_id))
                for source_id, source, target_id, target
                in zip(same["source_place_id"], same["source_dataset"], same["target_place_id"], same["target_dataset"])}


# ---------------------------------------------------------------- one normalizer per file format
def _mehdie(raw: pd.DataFrame) -> pd.DataFrame:
    """em_internal.csv already has the normalized columns."""
    return raw


def _matches(source_ids: pd.Series, source: DatasetName, target_ids: pd.Series, target: DatasetName) -> pd.DataFrame:
    """A file that only lists matching id pairs: every row is a same_as link."""
    return pd.DataFrame({
        "link_type": SAME_AS,
        "source_place_id": source_ids,
        "source_dataset": source.label,
        "target_place_id": target_ids,
        "target_dataset": target.label,
    })


def _pleiades_trismegistos(raw: pd.DataFrame) -> pd.DataFrame:
    """em.tsv: pleiades_id, trismegistos_id (+ titles and provenance, which are not kept)."""
    return _matches(raw["pleiades_id"], DatasetName.PLEIADES, raw["trismegistos_id"], DatasetName.TRISMEGISTOS)


def _wikidata_zh_ru(raw: pd.DataFrame) -> pd.DataFrame:
    """em.tsv: id_1 (Chinese record), id_2 (Russian record)."""
    return _matches(raw["id_1"], DatasetName.WIKIDATA_ZH, raw["id_2"], DatasetName.WIKIDATA_RU)


NORMALIZERS = {
    TestSetName.MEHDIE: _mehdie,
    TestSetName.PLEIADES_TRISMEGISTOS: _pleiades_trismegistos,
    TestSetName.WIKIDATA_ZH_RU: _wikidata_zh_ru,
}
