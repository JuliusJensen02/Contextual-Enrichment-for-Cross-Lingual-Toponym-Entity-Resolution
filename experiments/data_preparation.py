"""Data preparation for matching methods: load candidates, hydrate with full records, filter by attributes.

Architecture: Load full records (cached by dataset) → Build complete Pairs → Filter attributes

This ensures caching works effectively even when permuting attribute_categories across experiments.
Uses dataset-specific category mappings from cat_caller.py to ensure proper field selection per dataset.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from data_loader import DatasetName, Record, TestSetName


# ============================================================================
# CATEGORY MAPPINGS (from cat_caller.py patterns)
# ============================================================================

# Shared categories for most datasets (Arabic, Persian)
_BASE_CATEGORIES = {
    "name_variants":    ["title_ipa", "name_variants"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country"],
    "temporal":         ["begin_date", "end_date"],
    "classification":   ["types"],
}

# Extended categories for Wikipedia datasets (Wikidata)
_WIKI_CATEGORIES = {
    "name_variants":    ["title_ipa", "name_variants", "wiki_title"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country", "capital", "neighbours", "population"],
    "temporal":         ["inception", "dissolved"],
    "classification":   ["instance_of_label"],
    "description":      ["description", "described_by"],
}

# Map each dataset to its category definitions
DATASET_CATEGORIES = {
    DatasetName.KIMA:         {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.THURAYYA:     {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.YAQUT:        {**_BASE_CATEGORIES, "description": ["description"]},
    DatasetName.PLEIADES:     {**_BASE_CATEGORIES, "description": ["details", "description"]},
    DatasetName.TRISMEGISTOS: {**_BASE_CATEGORIES, "description": ["text_snippets"]},
    DatasetName.WIKIDATA_RU:  _WIKI_CATEGORIES,
    DatasetName.WIKIDATA_ZH:  _WIKI_CATEGORIES,
}

# Valid category names across all datasets
AVAILABLE_CATEGORIES = {
    "name_variants", "absolute", "relation", "temporal", "classification", "description"
}


# ============================================================================
# DATA TYPES
# ============================================================================

class Pair(NamedTuple):
    """A query record and its candidate records."""
    query: Record
    candidates: list[Record]


# ============================================================================
# FILE PATH MAPPING
# ============================================================================

# TestSetName -> folder in 03_candidate_generation/
_TEST_SET_FOLDERS = {
    TestSetName.MEHDIE: "MEHDIE",
    TestSetName.PLEIADES_TRISMEGISTOS: "Pleades_Trismegistos",
    TestSetName.WIKIDATA_ZH_RU: "Wikidata-zh-ru",
}

# DatasetName -> filename prefix
_DATASET_NAME_MAP = {
    DatasetName.KIMA: "kima",
    DatasetName.YAQUT: "yaqut",
    DatasetName.THURAYYA: "thurayya",
    DatasetName.PLEIADES: "pleiades",
    DatasetName.TRISMEGISTOS: "trismegistos",
    DatasetName.WIKIDATA_ZH: "wikidata_zh",
    DatasetName.WIKIDATA_RU: "wikidata_ru",
}


# ============================================================================
# RECORD LOADING (load complete records with ALL fields, cached by dataset only)
# ============================================================================

@lru_cache(maxsize=16)
def _load_full_dataset(dataset: DatasetName) -> dict[str, Record]:
    """Load all records from a dataset with ALL fields, cached in memory.
    
    Returns:
        Dict mapping record_id -> Record (with all available fields)
    """
    datasets_root = Path(__file__).resolve().parents[1] / "datasets"
    tsv_path = datasets_root / "02_minimized_datasets" / dataset.folder / dataset.file
    
    if not tsv_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {tsv_path}")
    
    # Read TSV (keep all as strings to preserve leading zeros)
    df = pd.read_csv(
        tsv_path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig"
    )
    
    # Load records with ALL fields
    records = {}
    for _, row in df.iterrows():
        # Build row dict with all possible fields
        row_dict = {col: row.get(col, "") for col in [
            "id", "title", "title_ipa", "name_variants", "wiki_title",
            "lat", "lon", "country", "capital", "neighbours", "population",
            "begin_date", "end_date", "inception", "dissolved",
            "types", "instance_of_label", "details", "described_by", "description", "text_snippets"
        ]}
        record = Record.from_row(dataset, row_dict)
        records[record.id] = record
    
    return records


# ============================================================================
# CANDIDATE PAIRS LOADING
# ============================================================================

def _load_candidate_pairs_from_file(test_set: TestSetName, source: DatasetName, target: DatasetName) -> dict[str, list[str]]:
    """Load precomputed candidate IDs from JSON file.
    
    Returns:
        Dict mapping source_id -> [target_ids]
    """
    datasets_root = Path(__file__).resolve().parents[1] / "datasets"
    folder_name = _TEST_SET_FOLDERS[test_set]
    
    source_name = _DATASET_NAME_MAP[source]
    target_name = _DATASET_NAME_MAP[target]
    filename = f"{source_name}_{target_name}.json"
    
    candidates_file = datasets_root / "03_candidate_generation" / folder_name / filename
    
    if not candidates_file.exists():
        raise FileNotFoundError(f"Candidates file not found: {candidates_file}")
    
    data = json.loads(candidates_file.read_text(encoding="utf-8"))
    return data.get("candidates", {})


def _build_complete_pairs(candidates_map: dict[str, list[str]], source_records: dict[str, Record], target_records: dict[str, Record]) -> list[Pair]:
    """Build Pair objects with complete records from candidates mapping.
    
    Args:
        candidates_map: {source_id: [target_ids]} from JSON
        source_records: {id: Record} for query side
        target_records: {id: Record} for candidate side
    
    Returns:
        List of Pair with complete records
    """
    pairs = []
    for source_id, target_ids in candidates_map.items():
        if source_id not in source_records:
            raise ValueError(f"Source ID {source_id} not found in source records")
        
        query = source_records[source_id]
        candidates = [target_records[tid] for tid in target_ids if tid in target_records]
        
        if candidates:
            pairs.append(Pair(query, candidates))
    
    return pairs


# ============================================================================
# ATTRIBUTE FILTERING
# ============================================================================

def _filter_pair_attributes(pairs: list[Pair], attributes: list[str]) -> list[Pair]:
    """Filter Pair records to only requested attributes.
    
    Creates new Records containing only the requested fields (plus id and title).
    This is a cheap operation - real work is caching full records.
    
    Args:
        pairs: List of Pair with complete records
        attributes: Categories to include (e.g., ["name_variants", "absolute"])
    
    Returns:
        List of Pair with filtered records
    """
    if not attributes:
        return pairs
    
    filtered_pairs = []
    for pair in pairs:
        # Filter query record
        filtered_query = _filter_record_attributes(pair.query, attributes)
        
        # Filter candidate records
        filtered_candidates = [_filter_record_attributes(cand, attributes) for cand in pair.candidates]
        
        filtered_pairs.append(Pair(filtered_query, filtered_candidates))
    
    return filtered_pairs


def _filter_record_attributes(record: Record, attribute_categories: list[str]) -> Record:
    """Filter a record to only requested attributes.
    
    Creates a new Record dict with only the requested fields (plus id and title always).
    """
    # Infer dataset from record properties
    dataset = record.dataset if hasattr(record, 'dataset') else None
    
    # Get field mappings for this dataset
    if dataset:
        dataset_cats = DATASET_CATEGORIES.get(dataset, {})
    else:
        dataset_cats = {}
    
    # Determine which fields to keep
    keep_fields = {"id", "title"}
    for category in attribute_categories:
        if category in dataset_cats:
            keep_fields.update(dataset_cats[category])
    
    # Build filtered row dict
    row_dict = {}
    for field in keep_fields:
        value = getattr(record, field, None)
        row_dict[field] = value if value is not None else ""
    
    # Create new Record with only these fields
    return Record.from_row(dataset, row_dict)


# ============================================================================
# PUBLIC API
# ============================================================================

class DataLoader:
    """Loads candidate pairs with complete records, filtered to requested attributes.
    
    Architecture:
      1. Load full records (cached by dataset only - no attributes in cache key)
      2. Load candidate pair mappings from JSON
      3. Build complete Pair objects
      4. Filter to only requested attributes (cheap operation)
    
    This ensures caching works across different attribute permutations.
    
    Example:
        loader = DataLoader(
            test_set=TestSetName.MEHDIE,
            source_dataset=DatasetName.KIMA,
            target_dataset=DatasetName.YAQUT,
            attribute_categories=["name_variants", "absolute"]
        )
        pairs = loader.load()  # list[Pair]
    """

    def __init__(
        self,
        test_set: TestSetName,
        source_dataset: DatasetName,
        target_dataset: DatasetName,
        attribute_categories: list[str],
    ):
        """Initialize the loader.
        
        Args:
            test_set: TestSetName.MEHDIE, PLEIADES_TRISMEGISTOS, or WIKIDATA_ZH_RU
            source_dataset: Query dataset (e.g., KIMA)
            target_dataset: Candidate dataset (e.g., YAQUT)
            attribute_categories: Categories to include (["name_variants", "absolute"])
        
        Raises:
            ValueError: If any attribute category is invalid
        """
        # Validate attributes
        for cat in attribute_categories:
            if cat not in AVAILABLE_CATEGORIES:
                raise ValueError(f"Invalid category '{cat}'. Valid: {sorted(AVAILABLE_CATEGORIES)}")
        
        self.test_set = test_set
        self.source_dataset = source_dataset
        self.target_dataset = target_dataset
        self.attribute_categories = attribute_categories
    
    def load(self) -> list[Pair]:
        """Load candidate pairs with requested attributes.
        
        Returns:
            List of Pair(query, candidates) with filtered attributes
        """
        # Step 1: Load full records (cached by dataset only)
        source_records = _load_full_dataset(self.source_dataset)
        target_records = _load_full_dataset(self.target_dataset)
        
        # Step 2: Load candidate pair mappings
        candidates_map = _load_candidate_pairs_from_file(self.test_set, self.source_dataset, self.target_dataset)
        
        # Step 3: Build complete pairs
        complete_pairs = _build_complete_pairs(candidates_map, source_records, target_records)
        
        # Step 4: Filter to requested attributes
        filtered_pairs = _filter_pair_attributes(complete_pairs, self.attribute_categories)
        
        return filtered_pairs


def load_pairs(
    test_set: TestSetName,
    source_dataset: DatasetName,
    target_dataset: DatasetName,
    attribute_categories: list[str],
) -> list[Pair]:
    """Load candidate pairs for entity matching experiments.
    
    Unified loader for all matching methods (bi-encoder, Ditto, LLMs).
    
    Args:
        test_set: TestSetName.MEHDIE, PLEIADES_TRISMEGISTOS, or WIKIDATA_ZH_RU
        source_dataset: Query dataset (e.g., KIMA)
        target_dataset: Candidate dataset (e.g., YAQUT)
        attribute_categories: Categories to include (["name_variants", "absolute"])
    
    Returns:
        List of Pair(query, candidates) with filtered attributes
    
    Example:
        pairs = load_pairs(
            TestSetName.MEHDIE,
            DatasetName.KIMA,
            DatasetName.YAQUT,
            ["name_variants", "absolute"]
        )
        for pair in pairs:
            print(f"Query: {pair.query.title}")
            for cand in pair.candidates:
                print(f"  Candidate: {cand.title}")
    """
    loader = DataLoader(test_set, source_dataset, target_dataset, attribute_categories)
    return loader.load()


"""
EXAMPLE OUTPUT:

When running load_pairs():

    pairs = load_pairs(
        test_set=TestSetName.MEHDIE,
        source_dataset=DatasetName.KIMA,
        target_dataset=DatasetName.YAQUT,
        attribute_categories=["name_variants", "absolute"]
    )

Returns: list[Pair]
  - Pair(0):
      query: Record(id=<query_id>, name_variants=<list>, absolute=<coords>)
      candidates: [Record(id=<cand_id>, name_variants=<list>, absolute=<coords>), ...]
  - Pair(1):
      query: Record(id=<query_id>, name_variants=<list>, absolute=<coords>)
      candidates: [Record(id=<cand_id>, name_variants=<list>, absolute=<coords>), ...]
  - ... (total pairs varies by test_set)

Each Record contains ONLY the requested attributes:
  - name_variants: list of alternative names
  - absolute: tuple of (lat, lon) coordinates
  - description: text snippets or full descriptions
  - temporal: begin/end dates
  - relation: country/capital/borders info
  - classification: entity types
"""
