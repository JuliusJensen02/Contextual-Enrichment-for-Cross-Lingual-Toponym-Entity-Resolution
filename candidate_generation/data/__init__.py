"""Dataset adapters that normalise every gazetteer to one schema."""

from candidate_generation.data.mehdie import load_mehdie
from candidate_generation.data.mehdie_testsets import load_mehdie_testsets
from candidate_generation.data.pleiades_trismegistos import load_pleiades_trismegistos
from candidate_generation.data.schema import Dataset, Record, Task

ADAPTERS = {
    "mehdie": load_mehdie,
    "mehdie_testsets": load_mehdie_testsets,
    "pleiades_trismegistos": load_pleiades_trismegistos,
}

__all__ = ["ADAPTERS", "Dataset", "Record", "Task"]
