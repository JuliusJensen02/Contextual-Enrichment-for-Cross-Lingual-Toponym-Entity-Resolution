#!/usr/bin/env python3
"""Load manifest-listed Trismegistos TSV partitions into one TSV file.

Usage: python scripts/load_trismegistos_partitions.py PARTITION_DIR OUTPUT.tsv
"""

import argparse
import csv
import json
import tempfile
from pathlib import Path

csv.field_size_limit(10**9)


def load_partitions(partition_dir: Path, output_path: Path) -> tuple[int, int]:
    """Combine the partitions listed by the manifest; return (rows, partitions)."""
    manifest_path = partition_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Partition manifest not found: {manifest_path}")
    if output_path.resolve() == manifest_path.resolve():
        raise ValueError("Output path must not overwrite the partition manifest")

    with manifest_path.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    if manifest.get("format_version") != 1:
        raise ValueError(f"Unsupported partition manifest format: {manifest.get('format_version')!r}")

    fieldnames = manifest.get("fieldnames")
    partitions = manifest.get("partitions")
    if (
        not isinstance(fieldnames, list)
        or not fieldnames
        or any(not isinstance(field, str) for field in fieldnames)
        or len(set(fieldnames)) != len(fieldnames)
    ):
        raise ValueError(f"{manifest_path} has no valid fieldnames")
    if not isinstance(partitions, list):
        raise ValueError(f"{manifest_path} has no valid partitions list")

    partition_paths = []
    partition_names = set()
    for entry in partitions:
        if not isinstance(entry, dict):
            raise ValueError(f"{manifest_path} contains an invalid partition entry")
        name = entry.get("file")
        expected_rows = entry.get("rows")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or not name.startswith("part-")
            or not name.endswith(".tsv")
        ):
            raise ValueError(f"{manifest_path} contains an invalid partition filename: {name!r}")
        if name in partition_names:
            raise ValueError(f"{manifest_path} lists partition {name!r} more than once")
        partition_names.add(name)
        if not isinstance(expected_rows, int) or expected_rows < 0:
            raise ValueError(f"{manifest_path} contains an invalid row count for {name!r}")
        path = partition_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Partition listed in manifest is missing: {path}")
        if path.resolve() == output_path.resolve():
            raise ValueError("Output path must not overwrite an input partition")
        partition_paths.append((path, expected_rows))

    declared_row_count = manifest.get("row_count")
    if (
        not isinstance(declared_row_count, int)
        or declared_row_count < 0
        or sum(rows for _, rows in partition_paths) != declared_row_count
    ):
        raise ValueError(f"{manifest_path} has an invalid total row count")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    row_count = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output_file:
            temporary_path = Path(output_file.name)
            writer = csv.writer(output_file, delimiter="\t", lineterminator="\n")
            writer.writerow(fieldnames)

            for path, expected_rows in partition_paths:
                partition_row_count = 0
                with path.open(encoding="utf-8", newline="") as partition_file:
                    reader = csv.reader(partition_file, delimiter="\t")
                    header = next(reader, None)
                    if header != fieldnames:
                        raise ValueError(f"{path} header does not match {manifest_path}")
                    for row in reader:
                        if len(row) != len(fieldnames):
                            raise ValueError(f"{path} contains a row with an unexpected number of columns")
                        writer.writerow(row)
                        partition_row_count += 1
                if partition_row_count != expected_rows:
                    raise ValueError(
                        f"{path} has {partition_row_count} rows; manifest declares {expected_rows}"
                    )
                row_count += partition_row_count

        if row_count != declared_row_count:
            raise ValueError(
                f"Loaded {row_count} rows; manifest declares {declared_row_count!r}"
            )
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return row_count, len(partition_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    row_count, partition_count = load_partitions(args.partition_dir, args.output)
    print(f"Loaded {row_count:,} rows from {partition_count:,} partitions into {args.output}")


if __name__ == "__main__":
    main()
