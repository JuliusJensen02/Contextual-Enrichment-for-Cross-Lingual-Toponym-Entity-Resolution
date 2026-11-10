"""Add derived IPA columns to the project's gazetteer datasets.

By default, this script updates the source datasets in place, preserving the
original name columns and inserting IPA columns immediately after them. Use
``--output-dir`` to write generated copies elsewhere instead.

Install the phonetics dependencies before running this script:

    pip install --no-deps panphon==0.22.2 epitran==1.35.3
    pip install -r candidate_generation/requirements.txt

Examples:

    python scripts/phonetic_encoding.py
    python scripts/phonetic_encoding.py mehdie_db_yaqut_extract wikidata_zh
    python scripts/phonetic_encoding.py --output-dir generated
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from candidate_generation.data.phonetics import phonetic_forms


@dataclass(frozen=True)
class DatasetSpec:
    """Describe a source file and the columns whose values should be encoded."""

    path: Path
    source_columns: tuple[str, ...]


DATASETS: dict[str, DatasetSpec] = {
    "mehdie_db_kima_flat": DatasetSpec(
        Path("final_datasets") / "MEHDIE" / "flattened" / "mehdie_db_kima_flat.tsv",
        ("title",),
    ),
    "mehdie_db_thurayya_flat": DatasetSpec(
        Path("final_datasets") / "MEHDIE" / "flattened" / "mehdie_db_thurayya_flat.tsv",
        ("title",),
    ),
    "mehdie_db_yaqut_flat": DatasetSpec(
        Path("final_datasets") / "MEHDIE" / "flattened" / "mehdie_db_yaqut_flat.tsv",
        ("title",),
    ),
    "pleiades": DatasetSpec(
        Path("final_datasets")
        / "Pleades_Trismegistos"
        / "pleiades_greek_trismegistos_latin"
        / "pleiades.tsv",
        ("title",),
    ),
    "trismegistos": DatasetSpec(
        Path("final_datasets")
        / "Pleades_Trismegistos"
        / "pleiades_greek_trismegistos_latin"
        / "trismegistos.tsv",
        ("names_latin", "names_egyptian", "names_coptic", "modern_name"),
    ),
    "wikidata_ru": DatasetSpec(
        Path("final_datasets") / "Wikidata-zh-ru" / "wikidata_ru.tsv",
        ("title",),
    ),
    "wikidata_zh": DatasetSpec(
        Path("final_datasets") / "Wikidata-zh-ru" / "wikidata_zh.tsv",
        ("title",),
    ),
}


def _encode_value(value: str | None) -> str:
    """Return the shared IPA form for a cell, preserving blank cells."""
    if not value or not value.strip():
        return ""
    return phonetic_forms(value.strip())[1]


def enrich_dataset(
    input_path: Path,
    output_path: Path,
    source_columns: tuple[str, ...],
) -> int:
    """Write ``output_path`` with IPA columns immediately after each source."""
    delimiter = "\t" if input_path.suffix.lower() == ".tsv" else ","

    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} has no header row")
        missing_columns = [
            column for column in source_columns if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(f"{input_path} is missing columns: {missing_columns}")

        fieldnames = list(reader.fieldnames)
        ipa_columns = {
            column: f"{column}_ipa" for column in source_columns
        }
        for ipa_column in ipa_columns.values():
            if ipa_column in fieldnames:
                fieldnames.remove(ipa_column)
        for source_column in source_columns:
            fieldnames.insert(
                fieldnames.index(source_column) + 1,
                ipa_columns[source_column],
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=fieldnames,
                delimiter=delimiter,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            row_count = 0
            for row in reader:
                for source_column, ipa_column in ipa_columns.items():
                    row[ipa_column] = _encode_value(row.get(source_column))
                writer.writerow(row)
                row_count += 1

    return row_count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "datasets",
        nargs="*",
        choices=sorted(DATASETS),
        metavar="DATASET",
        help="dataset names to process (default: all)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="repository root containing final_datasets (default: repository root)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="write generated copies below this directory, preserving relative paths",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    selected = args.datasets or list(DATASETS)
    data_root = args.data_root.resolve()

    for name in selected:
        spec = DATASETS[name]
        input_path = data_root / spec.path
        if not input_path.is_file():
            raise FileNotFoundError(f"Dataset not found: {input_path}")

        if args.output_dir is not None:
            relative_path = spec.path.with_name(
                f"{spec.path.stem}_ipa{spec.path.suffix}"
            )
            output_path = args.output_dir.resolve() / relative_path
            row_count = enrich_dataset(
                input_path, output_path, spec.source_columns
            )
        else:
            with NamedTemporaryFile(
                mode="wb",
                dir=input_path.parent,
                prefix=f".{input_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            try:
                row_count = enrich_dataset(
                    input_path, temporary_path, spec.source_columns
                )
                os.replace(temporary_path, input_path)
            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise
            output_path = input_path

        print(f"{name}: wrote {row_count:,} rows to {output_path}")


if __name__ == "__main__":
    main()
