"""Generate minimized TSV files from the project's seven source datasets."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets"
OUTPUT_DIR = DATASETS / "minimzed datasets"
VALUE_SEPARATOR = " | "

SOURCES = {
    "minimized_pleiades.tsv": DATASETS / "Pleades_Trismegistos" / "pleiades.tsv",
    "minimized_trismegistos.tsv": DATASETS
    / "Pleades_Trismegistos"
    / "trismegistos.tsv",
    "minimized_mehdie_db_yaqut_flat.tsv": DATASETS
    / "MEHDIE"
    / "flattened"
    / "mehdie_db_yaqut_flat.tsv",
    "minimized_mehdie_db_kima_flat.tsv": DATASETS
    / "MEHDIE"
    / "flattened"
    / "mehdie_db_kima_flat.tsv",
    "minimized_mehdie_db_thurayya_flat.tsv": DATASETS
    / "MEHDIE"
    / "flattened"
    / "mehdie_db_thurayya_flat.tsv",
    "minimized_wikidata_ru.tsv": DATASETS / "Wikidata-zh-ru" / "wikidata_ru.tsv",
    "minimized_wikidata_zh.tsv": DATASETS / "Wikidata-zh-ru" / "wikidata_zh.tsv",
}

OUTPUT_FIELDS = {
    "minimized_pleiades.tsv": [
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
    "minimized_trismegistos.tsv": [
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
    "minimized_mehdie_db_yaqut_flat.tsv": [
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
    "minimized_mehdie_db_kima_flat.tsv": [
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
    "minimized_mehdie_db_thurayya_flat.tsv": [
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
    "minimized_wikidata_ru.tsv": [
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
    "minimized_wikidata_zh.tsv": [
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
        "title": row.get("title", ""),
        "title_ipa": row.get("title_ipa", ""),
        "lat": row.get("lat", ""),
        "lon": row.get("lon", ""),
    }

    if filename == "minimized_pleiades.tsv":
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
    elif filename == "minimized_trismegistos.tsv":
        result.update(
            title=row.get("name_standard", ""),
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
    elif filename.startswith("minimized_mehdie_db_"):
        result.update(
            name_variants=row.get("name_variants", ""),
            country=combine(row, ["ccodes", "relation"]),
            begin_date=row.get("begin_date", ""),
            end_date=row.get("end_date", ""),
            types=row.get("types", ""),
            description=row.get("description", ""),
        )
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
    for filename, source_path in SOURCES.items():
        if not source_path.is_file():
            raise FileNotFoundError(f"Source TSV not found: {source_path}")
        row_count = generate_file(filename, source_path, OUTPUT_DIR)
        print(f"Wrote {OUTPUT_DIR / filename} ({row_count:,} rows)")


if __name__ == "__main__":
    main()
