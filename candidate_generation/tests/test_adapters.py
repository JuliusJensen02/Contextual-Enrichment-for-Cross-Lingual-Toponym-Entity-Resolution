"""Name cleaning, phonetics and adapter behaviour on the traps found in the data."""

from pathlib import Path

import pytest
import yaml

from candidate_generation.data import ADAPTERS
from candidate_generation.data.name_cleaning import (
    clean_egyptian_name,
    clean_pleiades_name,
    clean_tm_name,
)
from candidate_generation.data.phonetics import detect_script, phonetic_forms

ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load((ROOT / "candidate_generation/config.yaml").read_text())


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Aethusa (island)", ["Aethusa"]),
        ("Aegyptus (Roman imperial province)", ["Aegyptus"]),
        ("Ap(p)enninus M.", ["Appenninus M", "Apenninus M"]),
        ("Anatis/Asana (river)", ["Anatis", "Asana"]),
        ("Keraia?", ["Keraia"]),
        ("[Iutae]", ["Iutae"]),
        ("Insvla Taproba[n]e", ["Insvla Taprobane"]),
        ("[ - - ]o", []),
        ("T.", []),
        ("Untitled", []),
        ("Unnamed villa", []),
    ],
)
def test_pleiades_names_lose_type_qualifiers(raw, expected):
    assert clean_pleiades_name(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Tmoupho.[ ]", ["Tmoupho"]),
        ("Akousilaou Kleros [Tebtynis]", ["Akousilaou Kleros"]),
        ("Apollo( ) Topos", ["Apollo Topos"]),
    ],
)
def test_tm_names_lose_lacunae_and_location_brackets(raw, expected):
    assert clean_tm_name(raw) == expected


def test_egyptian_lists_split_into_clean_forms():
    assert clean_egyptian_name("Smn (Sw-mn)") == ["Smn", "Sw-mn"]
    assert clean_egyptian_name("Pr-wʿb (Pr-iw") == ["Pr-wʿb", "Pr-iw"]
    assert clean_egyptian_name("*Pȝ-ȝḥ") == ["Pȝ-ȝḥ"]


def test_hebrew_and_arabic_share_a_form():
    assert phonetic_forms("בלנסיה")[1] == phonetic_forms("بلنسية")[1]
    assert phonetic_forms("חלב")[1] == phonetic_forms("حلب")[1]


def test_scholarly_h_is_not_read_as_latin_x():
    assert phonetic_forms("Bāḫtaŧ")[1] == "baxta"


@pytest.mark.parametrize(
    "name, script",
    [
        ("קורדובה", "Hebr"),
        ("قرطبة", "Arab"),
        ("Ἀλεξάνδρεια", "Grek"),
        ("Roma", "Latn"),
        ("ⲧⲙⲟⲩⲫⲟ", "Copt"),
    ],
)
def test_script_detection(name, script):
    assert detect_script(name) == script


@pytest.fixture(scope="module")
def mehdie():
    settings = CONFIG["datasets"]["mehdie"]
    return ADAPTERS[settings["adapter"]](settings, ROOT)


def test_mehdie_places_are_unique_after_collapsing(mehdie):
    kima = mehdie.gazetteers["kima"]
    assert len(kima) == 6211 == len({r.record_id for r in kima})
    assert len(mehdie.gazetteers["thurayya"]) == 2241


def test_mehdie_conflicting_pairs_are_not_ground_truth(mehdie):
    assert mehdie.notes["same_as_place_pairs"] == 105
    assert sum(len(t.pairs) for t in mehdie.tasks) == 97


def test_mehdie_ground_truth_resolves(mehdie):
    ids = {s: {r.record_id for r in rows} for s, rows in mehdie.gazetteers.items()}
    for task in mehdie.tasks:
        assert all(
            a in ids[task.source] and b in ids[task.target] for a, b in task.pairs
        )


def test_thurayya_packed_variants_are_split(mehdie):
    record = next(
        r for r in mehdie.gazetteers["thurayya"] if r.record_id == "DINAWAR_474E346N_S"
    )
    assert not any(":" in n for n in record.all_names)
    assert "Dinawar" in record.all_names


def test_pleiades_trismegistos_names_keep_no_editorial_marks():
    settings = CONFIG["datasets"]["pleiades_trismegistos"]
    dataset = ADAPTERS[settings["adapter"]](settings, ROOT)
    for records in dataset.gazetteers.values():
        assert not any(set("()[]*") & set(n) for r in records for n in r.all_names)
    assert len(dataset.tasks[0].pairs) == 13890
