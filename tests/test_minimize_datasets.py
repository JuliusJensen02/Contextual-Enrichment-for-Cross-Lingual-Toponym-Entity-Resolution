from scripts.minimize_datasets import transform


def test_mehdie_multi_values_use_the_minimized_separator():
    row = {
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

    result = transform("minimized_mehdie_db_kima_flat.tsv", row)

    assert result["name_variants"] == "First | Second"
    assert result["lat"] == "10 | 11"
    assert result["lon"] == "20 | 21"
    assert result["country"] == "AA | BB | Country A | Country B"
    assert result["types"] == "City | Town"
    assert result["description"] == "Description one | Description two"
    assert result["title"] == "Place"
