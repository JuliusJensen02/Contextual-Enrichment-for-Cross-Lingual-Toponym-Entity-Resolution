import random
from itertools import combinations

from .dataset import Dataset
from .ground_truth import End, GroundTruth
from .names import DatasetName, TestSetName


class TestSet:
    """Two or more datasets plus the ground truth between them.

        mehdie = TestSetLoader().load(TestSetName.MEHDIE)
        mehdie.datasets                                            # [Dataset(KIMA, ...), ...]
        mehdie.ground_truth                                        # the GroundTruth (normalized table)
        mehdie.pairs                                               # every pair of its datasets
        mehdie.links_between(DatasetName.KIMA, DatasetName.YAQUT)  # {(kima_id, yaqut_id), ...}
        mehdie.sample(n_links=200, n_distractors=300, seed=13)     # a smaller TestSet

    `links` holds every match of the ground truth once, as a pair of (DatasetName, record id)
    ends. Only matches whose two records are both in the datasets are kept.
    """

    __test__ = False  # not a pytest test class, despite the name

    def __init__(self, name: TestSetName, datasets: list[Dataset], ground_truth: GroundTruth):
        self.name = name
        self.datasets = datasets
        self.ground_truth = ground_truth
        self._by_name = {dataset.name: dataset for dataset in datasets}
        # a link listed in both directions counts once: order its two ends
        self.links = {tuple(sorted(link, key=_end_key)) for link in ground_truth.links
                      if all(name in self._by_name and rid in self._by_name[name] for name, rid in link)}

    def __repr__(self) -> str:
        sizes = ", ".join(f"{dataset.label} {len(dataset)}" for dataset in self.datasets)
        return f"TestSet({self.name.name}: {sizes} records; {len(self.links)} ground truth links)"

    def dataset(self, name: DatasetName) -> Dataset:
        return self._by_name[name]

    @property
    def pairs(self) -> list[tuple[DatasetName, DatasetName]]:
        """Every pair of datasets: [a, b, c] gives (a, b), (a, c) and (b, c)."""
        return list(combinations(self._by_name, 2))

    def links_between(self, source: DatasetName, target: DatasetName) -> set[tuple[str, str]]:
        """The ground truth links between two of the datasets, as (source_id, target_id)."""
        out = set()
        for (name_1, id_1), (name_2, id_2) in self.links:
            if (name_1, name_2) == (source, target):
                out.add((id_1, id_2))
            elif (name_1, name_2) == (target, source):
                out.add((id_2, id_1))
        return out

    def sample(self, n_links: int, n_distractors: int, seed: int) -> "TestSet":
        """A smaller test set: the records of n_links random ground truth links, plus
        n_distractors random records without any link per dataset (something to reject).
        Every link whose two records both ended up in the sample is kept."""
        rng = random.Random(seed)
        ordered = sorted(self.links, key=lambda link: [_end_key(end) for end in link])
        keep = {dataset.name: set() for dataset in self.datasets}
        for link in rng.sample(ordered, min(n_links, len(ordered))):
            for name, rid in link:
                keep[name].add(rid)
        linked = {end for link in self.links for end in link}
        for dataset in self.datasets:
            unlinked = sorted(rid for rid in dataset.ids if (dataset.name, rid) not in linked)
            keep[dataset.name] |= set(rng.sample(unlinked, min(n_distractors, len(unlinked))))
        sampled = [dataset.subset(sorted(keep[dataset.name])) for dataset in self.datasets]  # fixed order
        return TestSet(self.name, sampled, self.ground_truth)


def _end_key(end: End) -> tuple[str, str]:
    """Sort key for one end of a link: enum members themselves do not sort."""
    name, record_id = end
    return name.name, record_id
