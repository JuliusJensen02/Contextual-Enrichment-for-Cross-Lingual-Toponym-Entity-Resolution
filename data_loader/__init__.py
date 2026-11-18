"""Load the project's test sets by enum: minimized datasets plus normalized ground truth, and
the stored candidates between their datasets."""
from .candidates import CandidateSet
from .dataset import Dataset
from .ground_truth import GroundTruth
from .loader import TestSetLoader
from .names import DatasetName, TestSetName
from .testset import TestSet

__all__ = ["CandidateSet", "Dataset", "DatasetName", "GroundTruth", "TestSet", "TestSetLoader", "TestSetName"]
