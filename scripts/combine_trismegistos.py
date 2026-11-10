#!/usr/bin/env python3
"""Join Trismegistos text rows to their place attributes by Trismegistos ID.

Usage: python scripts/combine_trismegistos.py [--texts PATH] [--places PATH]
                                               [--output PATH]
By default, the inputs are read from final_datasets/Pleades_Trismegistos/ and
the combined TSV is written there as trismegistos_texts_combined.tsv.
"""

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "final_datasets" / "Pleades_Trismegistos"
ID_COLUMN = "trismegistos_id"

csv.field_size_limit(10**9)


def combine(texts_path: Path, places_path: Path, output_path: Path) -> tuple[int, int]:
    """Write a left join of text rows to place columns; return (rows, unmatched)."""
    paths = {path.resolve() for path in (texts_path, places_path)}
    if output_path.resolve() in paths:
        raise ValueError("Output path must not overwrite either input file")

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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    empty_place = dict.fromkeys(added_fields, "")
    row_count = 0
    unmatched_count = 0
    with texts_path.open(encoding="utf-8", newline="") as texts_file:
        texts_reader = csv.DictReader(texts_file, delimiter="\t")
        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=text_fields + added_fields,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            for row in texts_reader:
                place = places.get(row[ID_COLUMN])
                if place is None:
                    unmatched_count += 1
                    place = empty_place
                row.update(place)
                writer.writerow(row)
                row_count += 1

    return row_count, unmatched_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texts", type=Path, default=DATA_DIR / "trismegistos_texts.tsv")
    parser.add_argument("--places", type=Path, default=DATA_DIR / "trismegistos.tsv")
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "trismegistos_texts_combined.tsv",
    )
    args = parser.parse_args()

    row_count, unmatched_count = combine(args.texts, args.places, args.output)
    print(f"Wrote {row_count:,} text rows to {args.output}")
    print(f"Rows without a matching place: {unmatched_count:,}")


if __name__ == "__main__":
    main()
