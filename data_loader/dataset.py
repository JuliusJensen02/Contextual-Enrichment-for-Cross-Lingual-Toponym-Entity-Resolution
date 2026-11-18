from .names import DatasetName
from .record import Record


class Dataset:
    """The records of one (minimized) dataset, in file order.

        kima = TestSetLoader().load(TestSetName.MEHDIE).dataset(DatasetName.KIMA)
        kima["138113"]                  # a Record
        for record in kima: ...
        kima.subset(["138113", "138114"])
    """

    def __init__(self, name: DatasetName, records):
        self.name = name
        self.records: list[Record] = list(records)
        self._by_id = {record.id: record for record in self.records}

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, record_id: str) -> Record:
        return self._by_id[record_id]

    def __contains__(self, record_id) -> bool:
        return record_id in self._by_id

    def __repr__(self) -> str:
        return f"Dataset({self.name.name}, {len(self)} records)"

    @property
    def label(self) -> str:
        return self.name.label

    @property
    def ids(self) -> list[str]:
        return [record.id for record in self.records]

    def subset(self, record_ids) -> "Dataset":
        """The given records, in the given order, as a new Dataset."""
        return Dataset(self.name, (self[record_id] for record_id in record_ids))
