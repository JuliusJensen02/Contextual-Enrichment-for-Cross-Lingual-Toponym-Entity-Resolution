import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def index_by(rows, key):
    return {row[key]: row for row in rows if row.get(key)}


def grouped_by(rows, key):
    result = defaultdict(list)
    for row in rows:
        if row.get(key):
            result[row[key]].append(row)
    return result


def json_cell(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(
        description="Build a one-row-per-place TGaz master CSV."
    )
    project_dir = Path(__file__).resolve().parent.parent
    default_input_dir = project_dir / "datasets" / "tgaz_csv"
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input_dir,
        help="Directory containing the TGaz CSV exports (default: ./datasets/tgaz_csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_input_dir / "placename_master.csv",
        help="Output CSV path (default: ./datasets/tgaz_csv/placename_master.csv).",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    places = read_csv(input_dir / "placename.csv")
    feature_types = index_by(read_csv(input_dir / "ftype.csv"), "id")
    scripts = index_by(read_csv(input_dir / "script.csv"), "id")
    transcription_systems = index_by(read_csv(input_dir / "trsys.csv"), "id")
    notes = index_by(read_csv(input_dir / "snote.csv"), "id")

    spellings = grouped_by(read_csv(input_dir / "spelling.csv"), "placename_id")
    locations = grouped_by(read_csv(input_dir / "present_loc.csv"), "placename_id")
    part_of = read_csv(input_dir / "part_of.csv")
    parent_links = grouped_by(part_of, "child_id")
    child_links = grouped_by(part_of, "parent_id")
    predecessors = grouped_by(read_csv(input_dir / "prec_by.csv"), "placename_id")

    preferred_names = {}
    all_names = {}
    for place_id, rows in spellings.items():
        names = [row["written_form"] for row in rows if row.get("written_form")]
        all_names[place_id] = names
        preferred = [
            row["written_form"]
            for row in rows
            if row.get("written_form") and row.get("default_per_type") in {"1", "Y", "y"}
        ]
        if preferred or names:
            preferred_names[place_id] = (preferred or names)[0]

    def place_name(place_id):
        return preferred_names.get(place_id, "")

    def relationship(link, related_id_key, include_dates=False):
        item = {
            "id": link.get(related_id_key, ""),
            "name": place_name(link.get(related_id_key, "")),
        }
        if include_dates:
            item["begin_year"] = link.get("begin_year", "")
            item["end_year"] = link.get("end_year", "")
        return item

    removed_fields = {
        "administrative_seats",
        "added_on",
        "alt_of_id",
        "begin_rule_name",
        "data_source_name",
        "end_rule_name",
        "obj_type",
        "parent_status",
        "xy_type",
    }
    output_fields = (
        [field for field in places[0].keys() if field not in removed_fields]
        if places
        else []
    )
    output_fields.extend(
        [
            "place_name",
            "all_names",
            "feature_type_name",
            "source_note_text",
            "spellings",
            "present_locations",
            "parents",
            "children",
            "predecessors",
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        for place in places:
            place_id = place.get("id", "")
            feature_type = feature_types.get(place.get("ftype_id", ""), {})
            note = notes.get(place.get("snote_id", ""), {})

            spelling_values = []
            for spelling in spellings.get(place_id, []):
                spelling_values.append(
                    {
                        "written_form": spelling.get("written_form", ""),
                        "script": scripts.get(spelling.get("script_id", ""), {}).get("name", ""),
                        "exonym_lang": spelling.get("exonym_lang", ""),
                        "transcription_system": transcription_systems.get(
                            spelling.get("trsys_id", ""), {}
                        ).get("name", ""),
                        "default_per_type": spelling.get("default_per_type", ""),
                        "attested_by": spelling.get("attested_by", ""),
                        "note": spelling.get("note", ""),
                    }
                )

            parent_values = [
                relationship(link, "parent_id", include_dates=True)
                for link in parent_links.get(place_id, [])
            ]
            child_values = [
                relationship(link, "child_id", include_dates=True)
                for link in child_links.get(place_id, [])
            ]
            predecessor_values = [
                {
                    "id": link.get("prec_id", ""),
                    "name": place_name(link.get("prec_id", "")),
                }
                for link in predecessors.get(place_id, [])
            ]
            result = dict(place)
            result.update(
                {
                    "place_name": place_name(place_id),
                    "all_names": json_cell(all_names.get(place_id, [])),
                    "feature_type_name": feature_type.get("name_en", ""),
                    "source_note_text": note.get("full_text", ""),
                    "spellings": json_cell(spelling_values),
                    "present_locations": json_cell(
                        [
                            {
                                "type": row.get("type", ""),
                                "country_code": row.get("country_code", ""),
                                "text_value": row.get("text_value", ""),
                                "source": row.get("source", ""),
                                "attestation": row.get("attestation", ""),
                                "source_uri": row.get("source_uri", ""),
                            }
                            for row in locations.get(place_id, [])
                        ]
                    ),
                    "parents": json_cell(parent_values),
                    "children": json_cell(child_values),
                    "predecessors": json_cell(predecessor_values),
                }
            )
            writer.writerow(result)

    print(f"Wrote {len(places)} places to {args.output.resolve()}")


if __name__ == "__main__":
    main()
