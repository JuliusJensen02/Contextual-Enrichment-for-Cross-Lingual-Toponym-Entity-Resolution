"""Experiments infrastructure for running matching methods on prepared data.

This module provides unified data preparation for entity matching experiments across
all matching methods (bi-encoder, Ditto, LLMs) using consistent attribute categories
and efficient caching.

QUICK START:

    from experiments import load_pairs
    from data_loader import TestSetName, DatasetName

    pairs = load_pairs(
        test_set=TestSetName.MEHDIE,
        source_dataset=DatasetName.KIMA,
        target_dataset=DatasetName.YAQUT,
        attribute_categories=["name_variants", "absolute"]
    )

    for pair in pairs:
        query_record = pair.query
        candidate_records = pair.candidates
        # Your matching logic here
"""
from .data_preparation import DataLoader, load_pairs

__all__ = ["DataLoader", "load_pairs"]
