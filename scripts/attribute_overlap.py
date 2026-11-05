"""Attribute overlap in gold matched pairs.

For each gold match, reports how many comparable attributes are populated on
*both* sides of the pair -- i.e. the attribute signal actually usable by a
matcher. Prints markdown tables to stdout for the two final_datasets.
"""
import csv
import sys
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
ROOT = Path(__file__).resolve().parent.parent
PT = ROOT / "final_datasets" / "Pleades_Trismegistos"
MD = ROOT / "final_datasets" / "MEHDIE"

EMPTY_CONTAINERS = {"", "{}", "[]", "[[]]", '""', "null", "none"}


def nonempty(v):
    if v is None:
        return False
    return v.strip().lower() not in EMPTY_CONTAINERS


def load(path, sep, key):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=sep))
    return {r[key]: r for r in rows}, rows


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "0.0%"


def overlap_table(pairs, left, right, groups, lkey, rkey):
    """groups: list of (label, [left_cols], [right_cols])."""
    total = len(pairs)
    out = []
    for label, lcols, rcols in groups:
        both = lonly = ronly = neither = 0
        for p in pairs:
            lr = left.get(p[lkey])
            rr = right.get(p[rkey])
            lhas = bool(lr) and any(nonempty(lr.get(c)) for c in lcols)
            rhas = bool(rr) and any(nonempty(rr.get(c)) for c in rcols)
            if lhas and rhas:
                both += 1
            elif lhas:
                lonly += 1
            elif rhas:
                ronly += 1
            else:
                neither += 1
        out.append((label, both, lonly, ronly, neither))
    return total, out


def print_md(title, left_name, right_name, total, rows):
    print(f"\n### {title}  (n = {total:,} matched pairs)\n")
    print(f"| Comparable attribute | Both sides | {left_name} only | "
          f"{right_name} only | Neither |")
    print("|---|---:|---:|---:|---:|")
    for label, both, lo, ro, ne in rows:
        print(f"| {label} | {both:,} ({pct(both, total)}) | "
              f"{lo:,} ({pct(lo, total)}) | {ro:,} ({pct(ro, total)}) | "
              f"{ne:,} ({pct(ne, total)}) |")


# ---------------------------------------------------------------- Pleiades–TM
pl, _ = load(PT / "pleiades.tsv", "\t", "pleiades_id")
tm, _ = load(PT / "trismegistos.tsv", "\t", "trismegistos_id")
with open(PT / "em.tsv", encoding="utf-8", newline="") as f:
    em = list(csv.DictReader(f, delimiter="\t"))

pt_groups = [
    ("Any name / title", ["title"], ["name_standard"]),
    ("Greek-script name", ["names_greek"], ["names_greek"]),
    ("Latin name", ["names_latin"], ["names_latin"]),
    ("Coordinates (lat/lon)", ["lat", "lon"], ["lat", "lon"]),
    ("Time span", ["year_from", "year_to"], ["begin_date", "end_date"]),
    ("Place type / status", ["place_types"], ["status"]),
    ("Free-text context", ["description", "details"],
     ["location", "text_snippets"]),
]
total, rows = overlap_table(em, pl, tm, pt_groups, "pleiades_id",
                            "trismegistos_id")
print("## Pleiades–Trismegistos")
print_md("Attribute co-presence in `em.tsv` matches", "Pleiades", "TM",
         total, rows)

# -------------------------------------------------------------------- MEHDIE
kima, _ = load(MD / "mehdie_db_kima_extract.csv", ",", "id")
yaqut, _ = load(MD / "mehdie_db_yaqut_extract.csv", ",", "id")
thur, _ = load(MD / "mehdie_db_thurayya_extract.csv", ",", "id")
allplaces = {**kima, **yaqut, **thur}

with open(MD / "internal_links_kima_yaqut_thurayya.csv", encoding="utf-8",
          newline="") as f:
    links = list(csv.DictReader(f))
same_as = [l for l in links if l["link_type"] == "same_as"]

md_groups = [
    ("Title", ["title"], ["title"]),
    ("Name variants", ["names"], ["names"]),
    ("Coordinates (geoms)", ["geoms"], ["geoms"]),
    ("Country codes", ["ccodes"], ["ccodes"]),
    ("Descriptions", ["descriptions"], ["descriptions"]),
    ("Place types", ["types"], ["types"]),
    ("Parent / related", ["related"], ["related"]),
]
total, rows = overlap_table(same_as, allplaces, allplaces, md_groups,
                            "source_place_id", "target_place_id")
print("\n\n## MEHDIE DB extract")
print_md("Attribute co-presence in `same_as` internal links", "source",
         "target", total, rows)
