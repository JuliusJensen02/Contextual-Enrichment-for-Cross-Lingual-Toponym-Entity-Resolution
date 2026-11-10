#!/usr/bin/env python3
"""Join Trismegistos text rows to place attributes and write TSV partitions.

Usage: python scripts/trismegistos/combine_trismegistos.py
       [--texts PATH] [--places PATH] [--output-dir DIR]
       [--rows-per-partition N]
By default, partitions and a manifest are written to
final_datasets/Pleades_Trismegistos/trismegistos_texts_combined_parts/.
"""

import argparse
import csv
import json
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "final_datasets" / "Pleades_Trismegistos"
ID_COLUMN = "trismegistos_id"

csv.field_size_limit(10**9)


def combine(
    texts_path: Path,
    places_path: Path,
    output_dir: Path,
    rows_per_partition: int = 10_000,
) -> tuple[int, int, int]:
    """Write a partitioned left join; return (rows, unmatched, partitions)."""
    if rows_per_partition < 1:
        raise ValueError("rows_per_partition must be at least 1")
    input_paths = {path.resolve() for path in (texts_path, places_path)}
    if output_dir.resolve() in input_paths or any(output_dir.resolve() in path.parents for path in input_paths):
        raise ValueError("Output directory must not contain or overwrite either input file")

    with texts_path.open(encoding="utf-8", newline="") as texts_file:
        texts_reader = csv.DictReader(texts_file, delimiter="\t")
        text_fields = texts_reader.fieldnames
        if not text_fields or ID_COLUMN not in text_fields:
            raise ValueError(f"{texts_path} must have a {ID_COLUMN!r} column")

        with places_path.open(encoding="utf-8", newline="") as places_file:
            places_reader = csv.DictReader(places_file, delimiter="\t")
            place_fields = places_reader.fieldnames
            if not place_fields or ID_COLUMN not in place_fields:
                raise ValueError(f"{places_path} must have a {ID_COLUMN!r} column")

            added_fields = [field for field in place_fields if field != ID_COLUMN]
            overlaps = set(text_fields).intersection(added_fields)
            if overlaps:
                raise ValueError(
                    "Input files have duplicate non-key column names: "
                    + ", ".join(sorted(overlaps))
                )

            places = {}
            for row in places_reader:
                place_id = row[ID_COLUMN]
                if not place_id:
                    raise ValueError(f"{places_path} contains a row with an empty {ID_COLUMN}")
                if place_id in places:
                    raise ValueError(f"{places_path} contains duplicate {ID_COLUMN} {place_id!r}")
                places[place_id] = {field: row[field] for field in added_fields}

    output_dir.mkdir(parents=True, exist_ok=True)
    empty_place = dict.fromkeys(added_fields, "")
    row_count = 0
    unmatched_count = 0
    partitions = []
    run_id = uuid4().hex
    with texts_path.open(encoding="utf-8", newline="") as texts_file:
        texts_reader = csv.DictReader(texts_file, delimiter="\t")
        output_file = None
        writer = None
        partition_rows = 0
        try:
            for row in texts_reader:
                if writer is None or partition_rows >= rows_per_partition:
                    if output_file is not None:
                        output_file.close()
                        partitions[-1]["rows"] = partition_rows
                    partition_number = len(partitions) + 1
                    partition_name = f"part-{run_id}-{partition_number:05d}.tsv"
                    output_file = (output_dir / partition_name).open(
                        "w", encoding="utf-8", newline=""
                    )
                    writer = csv.DictWriter(
                        output_file,
                        fieldnames=text_fields + added_fields,
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    partitions.append({"file": partition_name, "rows": 0})
                    partition_rows = 0

                place = places.get(row[ID_COLUMN])
                if place is None:
                    unmatched_count += 1
                    place = empty_place
                row.update(place)
                writer.writerow(row)
                row_count += 1
                partition_rows += 1
        finally:
            if output_file is not None and not output_file.closed:
                output_file.close()
        if partitions:
            partitions[-1]["rows"] = partition_rows

    manifest = {
        "format_version": 1,
        "fieldnames": text_fields + added_fields,
        "row_count": row_count,
        "partitions": partitions,
    }
    manifest_path = output_dir / "manifest.json"
    temporary_manifest = output_dir / "manifest.json.tmp"
    with temporary_manifest.open("w", encoding="utf-8", newline="\n") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.write("\n")
    temporary_manifest.replace(manifest_path)

    return row_count, unmatched_count, len(partitions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texts", type=Path, default=DATA_DIR / "trismegistos_texts.tsv")
    parser.add_argument("--places", type=Path, default=DATA_DIR / "trismegistos.tsv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATA_DIR / "trismegistos_texts_combined_parts",
    )
    parser.add_argument("--rows-per-partition", type=int, default=10_000)
    args = parser.parse_args()

    row_count, unmatched_count, partition_count = combine(
        args.texts,
        args.places,
        args.output_dir,
        args.rows_per_partition,
    )
    print(f"Wrote {row_count:,} text rows in {partition_count:,} partitions to {args.output_dir}")
    print(f"Rows without a matching place: {unmatched_count:,}")


if __name__ == "__main__":
    main()
