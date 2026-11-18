from .names import DatasetName, TestSetName

# A ground truth match: two (dataset, record id) ends.
Link = tuple[tuple[DatasetName, str], tuple[DatasetName, str]]

# The two id columns of the ground truth files that only list matches.
ID_COLUMNS = {
    TestSetName.PLEIADES_TRISMEGISTOS: ("pleiades_id", "trismegistos_id"),
    TestSetName.WIKIDATA_ZH_RU: ("id_1", "id_2"),
}


def read_links(name: TestSetName, rows: list[dict[str, str]]) -> set[Link]:
    """The matches in the rows of a ground truth file of datasets/em/ (each file has its own columns)."""
    if name is TestSetName.MEHDIE:  # em_internal.csv also has other relations than same_as
        by_label = {dataset.label: dataset for dataset in DatasetName}
        return {((by_label[row["source_dataset"]], row["source_place_id"]),
                 (by_label[row["target_dataset"]], row["target_place_id"]))
                for row in rows if row["link_type"] == "same_as"}
    source, target = name.datasets
    source_column, target_column = ID_COLUMNS[name]
    return {((source, row[source_column]), (target, row[target_column])) for row in rows}
