"""Load the project's test sets by enum: minimized datasets plus normalized ground truth."""
from .dataset import Dataset
from .ground_truth import GroundTruth
from .loader import TestSetLoader
from .names import DatasetName, TestSetName
from .testset import TestSet

__all__ = ["Dataset", "DatasetName", "GroundTruth", "TestSet", "TestSetLoader", "TestSetName"]
