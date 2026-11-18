"""scripts/minimize_datasets.py: mapping the source datasets to the minimized schema."""
import csv

import pytest

from scripts.minimize_datasets import OUTPUT_DIR, OUTPUT_FIELDS, SOURCES, combine, generate_file, transform


def test_mehdie_multi_values_use_the_minimized_separator():
    row = {
        "id": "42",
        "title": "Place",
        "title_ipa": "place",
        "name_variants": "First; Second",
        "lat": "10; 11",
        "lon": "20; 21",
        "ccodes": "AA; BB",
        "relation": "Country A; Country B",
        "begin_date": "",
        "end_date": "",
        "types": "City; Town",
        "description": "Description one; Description two",
    }

    result = transform("kima.tsv", row)

    assert result["name_variants"] == "First | Second"
    assert result["lat"] == "10 | 11"
    assert result["lon"] == "20 | 21"
    assert result["country"] == "AA | BB | Country A | Country B"
    assert result["types"] == "City | Town"
    assert result["description"] == "Description one | Description two"
    assert result["id"] == "42"
    assert result["title"] == "Place"


def test_combine_joins_non_empty_values_once():
    row = {"a": " Rome ", "b": "", "c": "Roma", "d": "Rome", "e": None}

    assert combine(row, ["a", "b", "c", "d", "e", "not_a_column"]) == "Rome | Roma"
    assert combine({}, ["a"]) == ""


def test_pleiades_row_uses_the_pleiades_id_and_combines_the_name_columns():
    row = {
        "pleiades_id": "423025", "id": "ignored", "title": "Roma", "title_ipa": "roma",
        "lat": "41.89", "lon": "12.48",
        "names_by_language": "Ῥώμη@grc", "names_romanized": "Rhome", "names_greek": "Ῥώμη", "names_latin": "Roma",
        "year_from": "-750", "year_to": "640", "place_types": "settlement",
        "details": "capital", "description": "An ancient city",
    }

    result = transform("pleiades.tsv", row)

    assert set(result) == set(OUTPUT_FIELDS["pleiades.tsv"])
    assert result["id"] == "423025"
    assert result["name_variants"] == "Ῥώμη@grc | Rhome | Ῥώμη | Roma"
    assert (result["begin_date"], result["end_date"]) == ("-750", "640")
    assert result["types"] == "settlement"
    assert result["country"] == ""


def test_trismegistos_row_keeps_the_greek_title_and_prefers_the_greek_ipa():
    row = {
        "trismegistos_id": "1344", "name_standard": "Memphis", "title": "Μέμφις",
        "names_greek": "Μέμφις", "names_latin": "Memphis", "names_egyptian": "", "names_coptic": "ⲙⲉⲙϥⲓ",
        "modern_name": "Mit Rahina", "names_greek_ipa": "mempʰis", "names_latin_ipa": "mempis",
        "country": "Egypt", "region": "", "nomos_code": "L01", "provincia": "Aegyptus",
        "status": "city", "text_snippets": "snippet", "lat": "29.85", "lon": "31.25",
    }

    result = transform("trismegistos.tsv", row)

    assert set(result) == set(OUTPUT_FIELDS["trismegistos.tsv"])
    assert result["id"] == "1344"
    assert result["title"] == "Μέμφις"  # not the romanized name_standard
    assert result["title_ipa"] == "mempʰis"
    assert result["name_variants"] == "Memphis | Μέμφις | ⲙⲉⲙϥⲓ | Mit Rahina"  # "Memphis" only once
    assert result["country"] == "Egypt | L01 | Aegyptus"
    assert transform("trismegistos.tsv", row | {"names_greek_ipa": ""})["title_ipa"] == "mempis"


def test_wikidata_row_combines_variants_and_country():
    row = {
        "id": "Q649", "title": "Москва", "title_ipa": "moskva", "lat": "55.75", "lon": "37.61",
        "variants": "Moskva", "replaces": "", "replaced_by": "",
        "country": "Россия", "admin_unit": "ЦФО", "part_of": "Россия",
        "wiki_title": "Москва", "population": "13000000",
    }

    result = transform("wikidata_ru.tsv", row)

    assert set(result) == set(OUTPUT_FIELDS["wikidata_ru.tsv"])
    assert result["name_variants"] == "Moskva"
    assert result["country"] == "Россия | ЦФО"
    assert result["population"] == "13000000"
    assert result["capital"] == ""  # a column the source row does not have


@pytest.mark.parametrize("filename", list(OUTPUT_FIELDS))
def test_every_file_gets_exactly_its_output_fields_even_from_an_empty_row(filename):
    assert set(transform(filename, {})) == set(OUTPUT_FIELDS[filename])


def test_every_source_has_output_fields_starting_with_the_shared_columns():
    assert set(SOURCES) == set(OUTPUT_FIELDS)
    for fields in OUTPUT_FIELDS.values():
        assert fields[:6] == ["id", "title", "title_ipa", "name_variants", "lat", "lon"]


def test_generate_file_writes_a_tsv_with_the_output_header(tmp_path):
    source = tmp_path / "kima_source.tsv"
    source.write_text(
        "﻿id\ttitle\ttitle_ipa\tname_variants\tlat\tlon\tccodes\trelation\ttypes\tdescription\n"
        "1\tחלב\tħalab\tHalab; Aleppo\t36.2\t37.16\tSY\t\tcity\t\n"
        "2\tעכו\tako\t\t\t\t\t\t\t\n",
        encoding="utf-8",
    )

    count = generate_file("kima.tsv", source, tmp_path / "out")

    with (tmp_path / "out" / "kima.tsv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    assert count == 2
    assert list(rows[0]) == OUTPUT_FIELDS["kima.tsv"]
    assert rows[0]["id"] == "1"  # the BOM is not part of the first column name
    assert rows[0]["name_variants"] == "Halab | Aleppo"
    expected = {field: "" for field in OUTPUT_FIELDS["kima.tsv"]} | {"id": "2", "title": "עכו", "title_ipa": "ako"}
    assert rows[1] == expected


def test_generate_file_rejects_a_row_with_too_many_cells(tmp_path):
    source = tmp_path / "bad.tsv"
    source.write_text("id\ttitle\n1\tA\textra\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed TSV row"):
        generate_file("kima.tsv", source, tmp_path / "out")


def test_generate_file_rejects_an_empty_source(tmp_path):
    source = tmp_path / "empty.tsv"
    source.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="no header"):
        generate_file("kima.tsv", source, tmp_path / "out")


@pytest.mark.parametrize("filename", list(SOURCES))
def test_the_minimized_files_in_the_repo_are_up_to_date(filename, tmp_path):
    """The committed minimized file is what the script produces from its source today."""
    folder, source_path = SOURCES[filename]
    committed = OUTPUT_DIR / folder / filename
    if not source_path.is_file() or not committed.is_file():
        pytest.skip(f"{source_path.name} or its minimized file is not in this checkout")

    generate_file(filename, source_path, tmp_path)

    generated = (tmp_path / filename).read_bytes().replace(b"\r\n", b"\n")
    assert generated == committed.read_bytes().replace(b"\r\n", b"\n")
