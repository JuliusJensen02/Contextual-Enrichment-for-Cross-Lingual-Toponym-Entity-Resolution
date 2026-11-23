import random
from itertools import combinations

from .dataset import Dataset
from .ground_truth import Link
from .names import DatasetName, TestSetName


class TestSet:
    """Two or more datasets plus the ground truth links between them.

        mehdie = TestSetLoader().load(TestSetName.MEHDIE)
        mehdie.dataset(DatasetName.KIMA)
        mehdie.pairs                                               # every pair of its datasets
        mehdie.links_between(DatasetName.KIMA, DatasetName.YAQUT)  # {(kima_id, yaqut_id), ...}
        mehdie.sample(n_links=200, n_distractors=300, seed=13)     # a smaller TestSet

    Only links whose two records are both in the datasets are kept, each once.
    """

    __test__ = False  # not a pytest test class, despite the name

    def __init__(self, name: TestSetName, datasets: list[Dataset], links: set[Link]):
        self.name = name
        self.datasets = datasets
        self._by_name = {dataset.name: dataset for dataset in datasets}
        self.links = {tuple(sorted(link, key=_end_key)) for link in links  # one direction only
                      if all(name in self._by_name and rid in self._by_name[name] for name, rid in link)}

    def dataset(self, name: DatasetName) -> Dataset:
        return self._by_name[name]

    @property
    def pairs(self) -> list[tuple[DatasetName, DatasetName]]:
        """Every pair of datasets: [a, b, c] gives (a, b), (a, c) and (b, c)."""
        return list(combinations(self._by_name, 2))

    def links_between(self, source: DatasetName, target: DatasetName) -> set[tuple[str, str]]:
        """The links between two of the datasets, as (source_id, target_id)."""
        out = set()
        for (name_1, id_1), (name_2, id_2) in self.links:
            if (name_1, name_2) == (source, target):
                out.add((id_1, id_2))
            elif (name_1, name_2) == (target, source):
                out.add((id_2, id_1))
        return out

    def without(self, *names: DatasetName) -> "TestSet":
        """The test set without the given datasets (and so without their links)."""
        return TestSet(self.name, [dataset for dataset in self.datasets if dataset.name not in names], self.links)

    def sample(self, n_links: int, n_distractors: int, seed: int) -> "TestSet":
        """The records of n_links random links, plus n_distractors random unlinked records per
        dataset (something to reject)."""
        rng = random.Random(seed)
        keep = {dataset.name: set() for dataset in self.datasets}
        for link in rng.sample(sorted(self.links, key=lambda link: [_end_key(end) for end in link]),
                               min(n_links, len(self.links))):
            for name, rid in link:
                keep[name].add(rid)
        linked = {end for link in self.links for end in link}
        for dataset in self.datasets:
            unlinked = [rid for rid in sorted(dataset.ids) if (dataset.name, rid) not in linked]
            keep[dataset.name] |= set(rng.sample(unlinked, min(n_distractors, len(unlinked))))
        sampled = [dataset.subset(sorted(keep[dataset.name])) for dataset in self.datasets]
        return TestSet(self.name, sampled, self.links)


def _end_key(end) -> tuple[str, str]:
    """Sort key for one end of a link (enum members do not sort)."""
    name, record_id = end
    return name.name, record_id
