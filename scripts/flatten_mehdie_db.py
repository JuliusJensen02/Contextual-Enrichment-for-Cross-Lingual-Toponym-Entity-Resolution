"""Flatten the JSON columns of the MEHDIE place extracts into TSV files.

Reads final_datasets/MEHDIE_DB_EXTRACT/mehdie_db_{kima,yaqut,thurayya}_extract.csv
(unchanged) and writes final_datasets/MEHDIE_DB_EXTRACT/flattened/mehdie_db_{name}_flat.tsv
with one row per place and the columns in OUT_COLS. Multi-valued fields are joined with "; ".
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "final_datasets" / "MEHDIE_DB_EXTRACT"
OUT_DIR = SRC_DIR / "flattened"
SOURCES = ["kima", "yaqut", "thurayya"]

# Not ",": Kima toponyms contain commas (e.g. "Karmel, Mount"); no field contains ";".
SEP = "; "

OUT_COLS = [
    "id", "title", "src_id", "ccodes", "begin_date", "end_date", "dataset",
    "description", "name_variants", "lat", "lon", "types", "relation",
]

csv.field_size_limit(10**9)


def load_json(raw: str) -> list:
    if not raw or not raw.strip():
        return []
    value = json.loads(raw)
    return value if isinstance(value, list) else [value]


def parse_pg_array(raw: str) -> list[str]:
    raw = (raw or "").strip().strip("{}")
    return [v.strip().strip('"') for v in raw.split(",") if v.strip()]


def unique(values) -> list[str]:
    seen: dict[str, None] = {}
    for v in values:
        v = " ".join(str(v).split())
        if v:
            seen.setdefault(v, None)
    return list(seen)


def dates(row: dict) -> tuple[str, str]:
    bounds = parse_pg_array(row["minmax"])
    if len(bounds) == 2:
        return bounds[0], bounds[1]
    spans = [s for s in load_json(row["timespans"]) if s]
    if spans:
        return str(min(s[0] for s in spans)), str(max(s[-1] for s in spans))
    return "", ""


def name_variants(row: dict, source: str) -> list[str]:
    toponyms = [n.get("toponym", "") for n in load_json(row["names"])]
    if source == "thurayya":
        # Al-Thurayya packs several variants into one toponym separated by ":".
        toponyms = [part for t in toponyms for part in t.split(":")]
    parts = load_json(row["name_parts"])
    return unique(toponyms + [p if isinstance(p, str) else json.dumps(p, ensure_ascii=False) for p in parts])


def type_label(item: dict) -> str:
    labels = ", ".join(unique([item.get("label", ""), item.get("sourceLabel", "")]))
    identifier = item.get("identifier", "")
    return f"{labels} ({identifier})" if labels and identifier else labels or identifier


def relation(item: dict) -> str:
    details = ", ".join(v for v in (item.get("relationType"), item.get("relationTo")) if v)
    label = item.get("label", "")
    return f"{label} ({details})" if details else label


def flatten_row(row: dict, source: str) -> dict:
    begin, end = dates(row)
    geoms = [g for g in load_json(row["geoms"]) if len(g.get("coordinates") or []) >= 2]

    # links are dropped: they are covered by the internal_links_* / external_links_* files.
    return {
        "id": row["id"],
        "title": row["title"],
        "src_id": row["src_id"],
        "ccodes": SEP.join(parse_pg_array(row["ccodes"])),
        "begin_date": begin,
        "end_date": end,
        "dataset": row["dataset"],
        "description": SEP.join(unique(d.get("value", "") for d in load_json(row["descriptions"]))),
        "name_variants": SEP.join(name_variants(row, source)),
        # GeoJSON order is [lon, lat].
        "lat": SEP.join(str(g["coordinates"][1]) for g in geoms),
        "lon": SEP.join(str(g["coordinates"][0]) for g in geoms),
        "types": SEP.join(unique(type_label(t) for t in load_json(row["types"]))),
        "relation": SEP.join(unique(relation(r) for r in load_json(row["related"]))),
    }


def flatten_file(source: str) -> None:
    src = SRC_DIR / f"mehdie_db_{source}_extract.csv"
    dst = OUT_DIR / f"mehdie_db_{source}_flat.tsv"

    with src.open(encoding="utf-8", newline="") as f:
        rows = [flatten_row(r, source) for r in csv.DictReader(f)]

    with dst.open("w", encoding="utf-8", newline="") as f:
        # Unquoted TSV; fails loudly if a field ever contains a tab or newline.
        writer = csv.DictWriter(f, fieldnames=OUT_COLS, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar=None, escapechar=None)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{src.name}: {len(rows)} rows -> {dst.relative_to(ROOT)}")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for source in SOURCES:
        flatten_file(source)


if __name__ == "__main__":
    main()
