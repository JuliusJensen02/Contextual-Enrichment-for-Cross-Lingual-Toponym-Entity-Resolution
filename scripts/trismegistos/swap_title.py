"""Replace title values with language-specific name columns in the paired datasets."""

import csv
import sys
import tempfile
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets" / "Pleades_Trismegistos" / "pleiades_greek_trismegistos_latin"
TARGETS = (
    (DATA_DIR / "trismegistos.tsv", "names_latin"),
    (DATA_DIR / "pleiades.tsv", "names_greek"),
)


def replace_title(path: Path, source_column: str) -> tuple[int, int]:
    """Replace title with source_column; return (rows, blank replacement values)."""
    temporary_path = None
    row_count = 0
    blank_count = 0
    try:
        with path.open(encoding="utf-8", newline="") as source_file:
            reader = csv.DictReader(source_file, delimiter="\t")
            fields = reader.fieldnames
            if not fields:
                raise ValueError(f"{path} has no header row")
            if len(fields) != len(set(fields)):
                raise ValueError(f"{path} has duplicate column names")
            missing = {"title", source_column}.difference(fields)
            if missing:
                raise ValueError(
                    f"{path} is missing required columns: {', '.join(sorted(missing))}"
                )

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as output_file:
                temporary_path = Path(output_file.name)
                writer = csv.DictWriter(
                    output_file,
                    fieldnames=fields,
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writeheader()
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(
                            f"{path} has a malformed row at line {reader.line_num}"
                        )
                    title = row[source_column]
                    row["title"] = title
                    blank_count += not bool(title.strip())
                    writer.writerow(row)
                    row_count += 1

        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return row_count, blank_count


def main() -> None:
    for path, source_column in TARGETS:
        row_count, blank_count = replace_title(path, source_column)
        print(
            f"Updated {path.relative_to(ROOT)}: {row_count:,} rows; "
            f"{blank_count:,} blank {source_column} values copied to title"
        )


if __name__ == "__main__":
    main()