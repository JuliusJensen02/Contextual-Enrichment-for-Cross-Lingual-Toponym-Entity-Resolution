"""Generate minimized TSV files from the project's seven source datasets."""

import csv
import sys
from pathlib import Path


csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets"
OUTPUT_DIR = DATASETS / "02_minimized_datasets"
VALUE_SEPARATOR = " | "

CLEANED = DATASETS / "01_cleaned_datasets"
ORIGINAL = DATASETS / "00_original_datasets"

# Output filename -> (group folder under the output directory, source file)
SOURCES = {
    "pleiades.tsv": ("Pleades_Trismegistos", CLEANED / "Pleades_Trismegistos" / "pleiades.tsv"),
    "trismegistos.tsv": ("Pleades_Trismegistos", CLEANED / "Pleades_Trismegistos" / "trismegistos.tsv"),
    "yaqut.tsv": ("MEHDIE", CLEANED / "MEHDIE" / "yaqut.tsv"),
    "kima.tsv": ("MEHDIE", CLEANED / "MEHDIE" / "kima.tsv"),
    "thurayya.tsv": ("MEHDIE", CLEANED / "MEHDIE" / "thurayya.tsv"),
    "wikidata_ru.tsv": ("Wikidata-zh-ru", ORIGINAL / "Wikidata-zh-ru" / "wikidata_ru.tsv"),
    "wikidata_zh.tsv": ("Wikidata-zh-ru", ORIGINAL / "Wikidata-zh-ru" / "wikidata_zh.tsv"),
}

MEHDIE_FILES = ("yaqut.tsv", "kima.tsv", "thurayya.tsv")

# The source column holding the record id (the ground truth files in datasets/em refer to it).
ID_COLUMNS = {"pleiades.tsv": "pleiades_id", "trismegistos.tsv": "trismegistos_id"}

OUTPUT_FIELDS = {
    "pleiades.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "begin_date",
        "end_date",
        "types",
        "details",
        "description",
    ],
    "trismegistos.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "begin_date",
        "end_date",
        "types",
        "text_snippets",
    ],
    "yaqut.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "begin_date",
        "end_date",
        "types",
        "description",
    ],
    "kima.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "begin_date",
        "end_date",
        "types",
        "description",
    ],
    "thurayya.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "begin_date",
        "end_date",
        "types",
        "description",
    ],
    "wikidata_ru.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "wiki_title",
        "capital",
        "neighbours",
        "population",
        "inception",
        "dissolved",
        "instance_of_label",
        "described_by",
        "description",
    ],
    "wikidata_zh.tsv": [
        "id",
        "title",
        "title_ipa",
        "name_variants",
        "lat",
        "lon",
        "country",
        "wiki_title",
        "capital",
        "neighbours",
        "population",
        "inception",
        "dissolved",
        "instance_of_label",
        "described_by",
        "description",
    ],
}

MEHDIE_MULTI_VALUE_FIELDS = (
    "name_variants",
    "lat",
    "lon",
    "country",
    "types",
    "description",
)


def combine(row, fields):
    """Join non-empty source values, omitting exact duplicates."""
    values = []
    for field in fields:
        value = (row.get(field) or "").strip()
        if value and value not in values:
            values.append(value)
    return VALUE_SEPARATOR.join(values)


def transform(filename, row):
    """Map one source record to the minimized output schema."""
    result = {
        "id": row.get(ID_COLUMNS.get(filename, "id"), ""),
        "title": row.get("title", ""),
        "title_ipa": row.get("title_ipa", ""),
        "lat": row.get("lat", ""),
        "lon": row.get("lon", ""),
    }

    if filename == "pleiades.tsv":
        result.update(
            name_variants=combine(
                row,
                ["names_by_language", "names_romanized", "names_greek", "names_latin"],
            ),
            country="",
            begin_date=row.get("year_from", ""),
            end_date=row.get("year_to", ""),
            types=row.get("place_types", ""),
            details=row.get("details", ""),
            description=row.get("description", ""),
        )
    elif filename == "trismegistos.tsv":
        result.update(
            title=row.get("name_standard", ""),
            title_ipa=row.get("names_latin_ipa", ""),
            name_variants=combine(
                row,
                [
                    "name_standard",
                    "names_greek",
                    "names_latin",
                    "names_egyptian",
                    "names_coptic",
                    "modern_name",
                ],
            ),
            country=combine(row, ["country", "region", "nomos_code", "provincia"]),
            begin_date=row.get("begin_date", ""),
            end_date=row.get("end_date", ""),
            types=row.get("status", ""),
            text_snippets=row.get("text_snippets", ""),
        )
    elif filename in MEHDIE_FILES:
        result.update(
            name_variants=row.get("name_variants", ""),
            country=combine(row, ["ccodes", "relation"]),
            begin_date=row.get("begin_date", ""),
            end_date=row.get("end_date", ""),
            types=row.get("types", ""),
            description=row.get("description", ""),
        )
        for field in MEHDIE_MULTI_VALUE_FIELDS:
            result[field] = result[field].replace("; ", VALUE_SEPARATOR)
    else:
        result.update(
            name_variants=combine(row, ["variants", "replaces", "replaced_by"]),
            country=combine(row, ["country", "admin_unit", "part_of"]),
            wiki_title=row.get("wiki_title", ""),
            capital=row.get("capital", ""),
            neighbours=row.get("neighbours", ""),
            population=row.get("population", ""),
            inception=row.get("inception", ""),
            dissolved=row.get("dissolved", ""),
            instance_of_label=row.get("instance_of_label", ""),
            described_by=row.get("described_by", ""),
            description=row.get("description", ""),
        )
    return result


def generate_file(filename, source_path, output_dir):
    """Generate one minimized TSV and return its number of data rows."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    fields = OUTPUT_FIELDS[filename]

    with source_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Source TSV has no header: {source_path}")

        with output_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=fields,
                delimiter="\t",
                lineterminator="\n",
                extrasaction="raise",
            )
            writer.writeheader()
            row_count = 0
            for row in reader:
                if None in row:
                    raise ValueError(
                        f"Malformed TSV row {reader.line_num} in {source_path}"
                    )
                writer.writerow(transform(filename, row))
                row_count += 1

    return row_count


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, (folder, source_path) in SOURCES.items():
        if not source_path.is_file():
            raise FileNotFoundError(f"Source TSV not found: {source_path}")
        row_count = generate_file(filename, source_path, OUTPUT_DIR / folder)
        print(f"Wrote {OUTPUT_DIR / folder / filename} ({row_count:,} rows)")


if __name__ == "__main__":
    main()
