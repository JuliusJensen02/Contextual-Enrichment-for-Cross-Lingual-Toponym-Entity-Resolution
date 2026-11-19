#!/usr/bin/env python3
"""Build a language-selected Pleiades–Trismegistos matching dataset.

The script joins Trismegistos text rows to place records, aggregates text
attributes to one row per place, selects the requested name language on each
side, replaces ``title`` with that name, and filters the gold links.

By default it builds Greek Pleiades vs Latin Trismegistos. To reverse the
languages, pass ``--pleiades-language latin --trismegistos-language greek``.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets" / "Pleades_Trismegistos"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from candidate_generation.data.phonetics import phonetic_forms

PLEIADES_ID = "pleiades_id"
TRISMEGISTOS_ID = "trismegistos_id"
LANGUAGE_COLUMNS = {"greek": "names_greek", "latin": "names_latin"}
SEPARATOR = " | "
TEXT_FIELDS = (
    "tm_text_id",
    "relation",
    "title",
    "material",
    "text_lang",
    "year_from",
    "year_to",
    "keywords",
    "mentions_name",
    "snippet",
    "edition_text",
    "translation_en",
)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def require_columns(
    path: Path,
    fields: list[str] | None,
    required: set[str],
) -> list[str]:
    if not fields:
        raise ValueError(f"{path} has no header row")
    missing = required.difference(fields)
    if missing:
        raise ValueError(
            f"{path} is missing required columns: {', '.join(sorted(missing))}"
        )
    if len(fields) != len(set(fields)):
        raise ValueError(f"{path} has duplicate column names")
    return fields


def validate_row(row: dict[str, str], reader: csv.DictReader, path: Path) -> None:
    if None in row or any(value is None for value in row.values()):
        raise ValueError(f"{path} has a malformed row at line {reader.line_num}")


def detect_line_terminator(path: Path) -> str:
    if path.is_file():
        with path.open("rb") as file:
            first_line = file.readline()
        if first_line.endswith(b"\r\n"):
            return "\r\n"
    return "\n"


def add_ipa_columns(fields: list[str], source_columns: tuple[str, ...]) -> list[str]:
    result = list(fields)
    for column in source_columns:
        ipa_column = f"{column}_ipa"
        if ipa_column in result:
            result.remove(ipa_column)
    for column in source_columns:
        result.insert(result.index(column) + 1, f"{column}_ipa")
    return result


def encode_value(value: str) -> str:
    if not value or not value.strip():
        return ""
    return SEPARATOR.join(
        phonetic_forms(part.strip())[1]
        for part in value.split("|")
        if part.strip()
    )


def build_pleiades(
    source: Path,
    output: Path,
    language: str,
    line_ending: str,
) -> set[str]:
    """Write places with the requested name language and return their IDs."""
    name_column = LANGUAGE_COLUMNS[language]
    other_name_column = LANGUAGE_COLUMNS["latin" if language == "greek" else "greek"]
    ids = set()

    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(
            source,
            reader.fieldnames,
            {PLEIADES_ID, "title", name_column, other_name_column},
        )
        output_fields = [field for field in fields if field != other_name_column]
        output_fields = [
            field for field in output_fields if field != f"{other_name_column}_ipa"
        ]
        output_fields = add_ipa_columns(output_fields, ("title",))
        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fields,
                delimiter="\t",
                lineterminator=line_ending,
            )
            writer.writeheader()
            for row in reader:
                validate_row(row, reader, source)
                place_id = row[PLEIADES_ID]
                if not place_id.strip():
                    raise ValueError(
                        f"{source} contains a row with an empty {PLEIADES_ID}"
                    )
                if not row[name_column].strip():
                    continue
                if place_id in ids:
                    raise ValueError(
                        f"{source} contains duplicate {PLEIADES_ID} {place_id!r}"
                    )
                ids.add(place_id)
                row["title"] = row[name_column]
                row["title_ipa"] = encode_value(row["title"])
                writer.writerow({field: row[field] for field in output_fields})

    return ids


def load_trismegistos_places(
    source: Path,
    text_fields: list[str],
) -> tuple[list[str], dict[str, dict[str, str]]]:
    name_columns = set(LANGUAGE_COLUMNS.values())
    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(
            source,
            reader.fieldnames,
            {
                TRISMEGISTOS_ID,
                *name_columns,
                "names_egyptian",
                "names_coptic",
                "modern_name",
            },
        )
        place_fields = [field for field in fields if field != TRISMEGISTOS_ID]
        overlaps = set(text_fields).intersection(place_fields)
        if overlaps:
            raise ValueError(
                "Text and place files have duplicate non-key column names: "
                + ", ".join(sorted(overlaps))
            )
        places = {}
        for row in reader:
            validate_row(row, reader, source)
            place_id = row[TRISMEGISTOS_ID]
            if not place_id.strip():
                raise ValueError(
                    f"{source} contains a row with an empty {TRISMEGISTOS_ID}"
                )
            if place_id in places:
                raise ValueError(
                    f"{source} contains duplicate {TRISMEGISTOS_ID} {place_id!r}"
                )
            places[place_id] = {field: row[field] for field in place_fields}

    return place_fields, places


def build_trismegistos(
    texts_source: Path,
    places_source: Path,
    output: Path,
    language: str,
    line_ending: str,
) -> tuple[set[str], int]:
    """Aggregate text rows per place, filter by name language, and return IDs/row count."""
    name_column = LANGUAGE_COLUMNS[language]
    other_name_column = LANGUAGE_COLUMNS["latin" if language == "greek" else "greek"]

    with texts_source.open(encoding="utf-8", newline="") as texts_file:
        text_reader = csv.DictReader(texts_file, delimiter="\t")
        text_fields = require_columns(
            texts_source,
            text_reader.fieldnames,
            {TRISMEGISTOS_ID, *TEXT_FIELDS},
        )

        place_fields, places = load_trismegistos_places(
            places_source,
            text_fields,
        )
        combined_fields = text_fields + place_fields
        output_fields = [
            field
            for field in combined_fields
            if field not in {other_name_column, f"{other_name_column}_ipa"}
        ]
        ipa_sources = tuple(
            dict.fromkeys(
                (name_column, "names_egyptian", "names_coptic", "modern_name")
            )
        )
        output_fields = add_ipa_columns(output_fields, ipa_sources)

        ids = set()
        text_row_count = 0
        closed_ids = set()
        current_id = None
        values = {}
        seen_values = {}
        mentions_name = False

        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fields,
                delimiter="\t",
                lineterminator=line_ending,
            )
            writer.writeheader()

            def flush_group() -> None:
                if current_id is None:
                    return
                place = places.get(current_id)
                if place is None or not place[name_column].strip():
                    return

                row = {field: SEPARATOR.join(values[field]) for field in values}
                row[TRISMEGISTOS_ID] = current_id
                row["mentions_name"] = "1" if mentions_name else "0"
                row.update(place)
                row["title"] = place[name_column]
                for field in ipa_sources:
                    row[f"{field}_ipa"] = encode_value(row[field])
                writer.writerow({field: row[field] for field in output_fields})
                ids.add(current_id)

            for text_row in text_reader:
                validate_row(text_row, text_reader, texts_source)
                place_id = text_row[TRISMEGISTOS_ID]
                if not place_id.strip():
                    raise ValueError(
                        f"{texts_source} contains a row with an empty "
                        f"{TRISMEGISTOS_ID}"
                    )

                if place_id != current_id:
                    flush_group()
                    if place_id in closed_ids:
                        raise ValueError(
                            f"{texts_source} has non-contiguous rows for "
                            f"{TRISMEGISTOS_ID} {place_id!r}"
                        )
                    if current_id is not None:
                        closed_ids.add(current_id)
                    current_id = place_id
                    values = {
                        field: []
                        for field in text_fields
                        if field not in {TRISMEGISTOS_ID, "mentions_name"}
                    }
                    seen_values = {field: set() for field in values}
                    mentions_name = False

                if text_row["mentions_name"].strip() == "1":
                    mentions_name = True
                for field in values:
                    value = text_row[field]
                    if value and value not in seen_values[field]:
                        seen_values[field].add(value)
                        values[field].append(value)
                text_row_count += 1

            flush_group()

    return ids, text_row_count


def build_em(
    source: Path,
    output: Path,
    pleiades_ids: set[str],
    trismegistos_ids: set[str],
    line_ending: str,
) -> int:
    with source.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        fields = require_columns(
            source,
            reader.fieldnames,
            {PLEIADES_ID, TRISMEGISTOS_ID},
        )
        count = 0
        with output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=fields,
                delimiter="\t",
                lineterminator=line_ending,
            )
            writer.writeheader()
            for row in reader:
                validate_row(row, reader, source)
                if (
                    row[PLEIADES_ID] in pleiades_ids
                    and row[TRISMEGISTOS_ID] in trismegistos_ids
                ):
                    writer.writerow(row)
                    count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pleiades-language", choices=LANGUAGE_COLUMNS, default="greek")
    parser.add_argument("--trismegistos-language", choices=LANGUAGE_COLUMNS, default="latin")
    parser.add_argument("--pleiades", type=Path, default=DATA_DIR / "pleiades.tsv")
    parser.add_argument("--trismegistos", type=Path, default=DATA_DIR / "trismegistos.tsv")
    parser.add_argument("--texts", type=Path, default=DATA_DIR / "trismegistos_texts.tsv")
    parser.add_argument("--em", type=Path, default=DATA_DIR / "em.tsv")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir or (
        DATA_DIR
        / f"pleiades_{args.pleiades_language}_trismegistos_{args.trismegistos_language}"
    )
    inputs = {
        path.resolve()
        for path in (args.pleiades, args.trismegistos, args.texts, args.em)
    }
    outputs = {
        (output_dir / name).resolve()
        for name in ("pleiades.tsv", "trismegistos.tsv", "em.tsv")
    }
    if inputs.intersection(outputs):
        raise ValueError("Output files must not overwrite any input file")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    line_endings = {
        name: detect_line_terminator(output_dir / name)
        for name in ("pleiades.tsv", "trismegistos.tsv", "em.tsv")
    }
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-build-",
        dir=output_dir.parent,
    ) as staging_dir:
        staging_dir = Path(staging_dir)
        pleiades_ids = build_pleiades(
            args.pleiades,
            staging_dir / "pleiades.tsv",
            args.pleiades_language,
            line_endings["pleiades.tsv"],
        )
        trismegistos_ids, text_row_count = build_trismegistos(
            args.texts,
            args.trismegistos,
            staging_dir / "trismegistos.tsv",
            args.trismegistos_language,
            line_endings["trismegistos.tsv"],
        )
        em_count = build_em(
            args.em,
            staging_dir / "em.tsv",
            pleiades_ids,
            trismegistos_ids,
            line_endings["em.tsv"],
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        for name in ("pleiades.tsv", "trismegistos.tsv", "em.tsv"):
            (staging_dir / name).replace(output_dir / name)

    print(f"Pleiades {args.pleiades_language}: {len(pleiades_ids):,} places")
    print(f"Trismegistos {args.trismegistos_language}: {len(trismegistos_ids):,} places")
    print(f"Processed {text_row_count:,} Trismegistos text rows")
    print(f"Gold links: {em_count:,} pairs")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
