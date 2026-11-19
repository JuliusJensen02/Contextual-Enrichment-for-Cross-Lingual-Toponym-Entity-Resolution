"""Load the project's test sets: their datasets as Records, their ground truth links, and the
stored candidates between their datasets."""
from .candidates import CandidateSet
from .dataset import Dataset
from .ground_truth import read_links
from .loader import TestSetLoader
from .names import DatasetName, TestSetName
from .record import CATEGORIES, Record
from .testset import TestSet

__all__ = ["CATEGORIES", "CandidateSet", "Dataset", "DatasetName", "Record", "TestSet", "TestSetLoader",
           "TestSetName", "read_links"]
