
import csv
import tempfile
from pathlib import Path

from load_trismegistos_partitions import load_partitions

TRISMEGISTOS_PARTITION_DIR = (
    Path(__file__).resolve().parents[2]
    / "datasets"
    / "Pleades_Trismegistos"
    / "trismegistos_texts_combined_parts"
)
PLEIDAS_PATH_DIR = r"C:\Users\jensg\Desktop\Contextual-Enrichment-for-Cross-Lingual-Toponym-Entity-Resolution\datasets\Pleades_Trismegistos\pleiades.tsv"

def count_greek_names_in_trismegistos(name_col):
    """Count rows with Greek names and distinct IDs on those rows."""
    output_path = Path(tempfile.mktemp(suffix=".tsv"))
    try:
        rows, partitions = load_partitions(TRISMEGISTOS_PARTITION_DIR, output_path)
        greek_name_count = 0
        unique_greek_name_ids = set()
        with output_path.open(encoding="utf-8", newline="") as output_file:
            reader = csv.DictReader(output_file, delimiter="\t")
            for row in reader:
                if row.get(name_col, "").strip():
                    greek_name_count += 1
                    trismegistos_id = row.get("trismegistos_id", "").strip()
                    if trismegistos_id:
                        unique_greek_name_ids.add(trismegistos_id)
        return greek_name_count, len(unique_greek_name_ids)
    finally:
        if output_path.exists():
            output_path.unlink()  # Clean up the temporary file

def count_greek_names_in_pleidas(name_col):
    """Count rows with Greek names and distinct IDs on those rows."""
    pleiades_path = Path(PLEIDAS_PATH_DIR)
    greek_name_count = 0
    unique_greek_name_ids = set()
    with pleiades_path.open(encoding="utf-8", newline="") as pleiades_file:
        reader = csv.DictReader(pleiades_file, delimiter="\t")
        for row in reader:
            if row.get(name_col, "").strip():
                greek_name_count += 1
                pleiades_id = row.get("pleiades_id", "").strip()
                if pleiades_id:
                    unique_greek_name_ids.add(pleiades_id)
    return greek_name_count, len(unique_greek_name_ids)

def read_ids_with_names(path, id_column, name_column):
    with path.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        required_fields = {id_column, name_column}
        missing_fields = required_fields.difference(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing_fields))}"
            )
        return {
            row[id_column].strip()
            for row in reader
            if row[id_column].strip() and row[name_column].strip()
        }

def count_greek_name_coverage_in_matches():
    """Count matched pairs with Greek names on each side and on both sides."""
    data_dir = (
        Path(__file__).resolve().parents[2]
        / "datasets"
        / "Pleades_Trismegistos"
    )
    pleiades_ids = read_ids_with_names(
        data_dir / "pleiades.tsv", "pleiades_id", "names_greek"
    )
    trismegistos_ids = read_ids_with_names(
        data_dir / "trismegistos.tsv", "trismegistos_id", "names_greek"
    )
    counts = {
        "total_pairs": 0,
        "pleiades_only": 0,
        "trismegistos_only": 0,
        "both": 0,
        "neither": 0,
    }

    with (data_dir / "em.tsv").open(encoding="utf-8", newline="") as matches_file:
        reader = csv.DictReader(matches_file, delimiter="\t")
        required_fields = {"pleiades_id", "trismegistos_id"}
        missing_fields = required_fields.difference(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(
                f"{data_dir / 'em.tsv'} is missing required columns: "
                f"{', '.join(sorted(missing_fields))}"
            )
        for row in reader:
            pleiades_id = row["pleiades_id"].strip()
            trismegistos_id = row["trismegistos_id"].strip()
            if not pleiades_id or not trismegistos_id:
                raise ValueError("em.tsv contains a match with an empty place ID")
            has_pleiades_greek = pleiades_id in pleiades_ids
            has_trismegistos_greek = trismegistos_id in trismegistos_ids
            counts["total_pairs"] += 1
            if has_pleiades_greek and has_trismegistos_greek:
                counts["both"] += 1
            elif has_pleiades_greek:
                counts["pleiades_only"] += 1
            elif has_trismegistos_greek:
                counts["trismegistos_only"] += 1
            else:
                counts["neither"] += 1
    return counts

def count_cross_script_name_coverage_in_matches():
    """Count gold matches with Latin names on one side and Greek on the other."""
    data_dir = (
        Path(__file__).resolve().parents[2]
        / "datasets"
        / "Pleades_Trismegistos"
    )
    pleiades_latin_ids = read_ids_with_names(
        data_dir / "pleiades.tsv", "pleiades_id", "names_latin"
    )
    pleiades_greek_ids = read_ids_with_names(
        data_dir / "pleiades.tsv", "pleiades_id", "names_greek"
    )
    trismegistos_latin_ids = read_ids_with_names(
        data_dir / "trismegistos.tsv", "trismegistos_id", "names_latin"
    )
    trismegistos_greek_ids = read_ids_with_names(
        data_dir / "trismegistos.tsv", "trismegistos_id", "names_greek"
    )
    counts = {
        "total_pairs": 0,
        "pleiades_latin_tm_greek": 0,
        "pleiades_greek_tm_latin": 0,
        "either_direction": 0,
        "both_directions": 0,
    }

    with (data_dir / "em.tsv").open(encoding="utf-8", newline="") as matches_file:
        reader = csv.DictReader(matches_file, delimiter="\t")
        required_fields = {"pleiades_id", "trismegistos_id"}
        missing_fields = required_fields.difference(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(
                f"{data_dir / 'em.tsv'} is missing required columns: "
                f"{', '.join(sorted(missing_fields))}"
            )
        for row in reader:
            pleiades_id = row["pleiades_id"].strip()
            trismegistos_id = row["trismegistos_id"].strip()
            if not pleiades_id or not trismegistos_id:
                raise ValueError("em.tsv contains a match with an empty place ID")
            pleiades_latin_tm_greek = (
                pleiades_id in pleiades_latin_ids
                and trismegistos_id in trismegistos_greek_ids
            )
            pleiades_greek_tm_latin = (
                pleiades_id in pleiades_greek_ids
                and trismegistos_id in trismegistos_latin_ids
            )
            counts["total_pairs"] += 1
            counts["pleiades_latin_tm_greek"] += pleiades_latin_tm_greek
            counts["pleiades_greek_tm_latin"] += pleiades_greek_tm_latin
            counts["either_direction"] += (
                pleiades_latin_tm_greek or pleiades_greek_tm_latin
            )
            counts["both_directions"] += (
                pleiades_latin_tm_greek and pleiades_greek_tm_latin
            )
    return counts

if __name__ == "__main__":
    greek_name_count, unique_greek_name_id_count = count_greek_names_in_trismegistos("names_greek")
    pleiades_greek_name_count, unique_pleiades_greek_name_id_count = (
        count_greek_names_in_pleidas("names_greek")
    )
    latin_name_count, unique_latin_name_id_count = count_greek_names_in_trismegistos("names_latin")
    pleiades_latin_name_count, unique_pleiades_latin_name_id_count = (
        count_greek_names_in_pleidas("names_latin")
    )


    print(f"Number of Trismegistos rows with non-empty Greek names: {greek_name_count}")
    print(
        "Number of unique Trismegistos IDs with non-empty Greek names: "
        f"{unique_greek_name_id_count}"
    )
    print(
        "Number of Pleiades rows with non-empty Greek names: "
        f"{pleiades_greek_name_count}"
    )
    print(
        "Number of unique Pleiades IDs with non-empty Greek names: "
        f"{unique_pleiades_greek_name_id_count}"
    )
    print(
        "Number of Trismegistos rows with non-empty Latin names: "
        f"{latin_name_count}"
    )
    print(
        "Number of unique Trismegistos IDs with non-empty Latin names: "
        f"{unique_latin_name_id_count}"
    )
    print(
        "Number of Pleiades rows with non-empty Latin names: "
        f"{pleiades_latin_name_count}"
    )
    print(
        "Number of unique Pleiades IDs with non-empty Latin names: "
        f"{unique_pleiades_latin_name_id_count}"
    )
    match_counts = count_greek_name_coverage_in_matches()
    total_pairs = match_counts["total_pairs"]

    def format_coverage(count):
        percentage = 100 * count / total_pairs if total_pairs else 0
        return f"{count:,} ({percentage:.1f}%)"

    print(f"Greek-name coverage in em.tsv ({total_pairs:,} matched pairs):")
    print(
        "  Pleiades: "
        + format_coverage(match_counts["pleiades_only"] + match_counts["both"])
    )
    print(
        "  Trismegistos: "
        + format_coverage(match_counts["trismegistos_only"] + match_counts["both"])
    )
    print(f"  Both sides: {format_coverage(match_counts['both'])}")
    print(f"  Neither side: {format_coverage(match_counts['neither'])}")
    cross_script_counts = count_cross_script_name_coverage_in_matches()
    cross_script_total = cross_script_counts["total_pairs"]

    def format_cross_script_coverage(count):
        percentage = 100 * count / cross_script_total if cross_script_total else 0
        return f"{count:,} ({percentage:.1f}%)"

    print(f"Cross-script Latin/Greek coverage in em.tsv ({cross_script_total:,} matched pairs):")
    print(
        "  Pleiades Latin + Trismegistos Greek: "
        + format_cross_script_coverage(
            cross_script_counts["pleiades_latin_tm_greek"]
        )
    )
    print(
        "  Pleiades Greek + Trismegistos Latin: "
        + format_cross_script_coverage(
            cross_script_counts["pleiades_greek_tm_latin"]
        )
    )
    print(
        "  Either direction (unique pairs): "
        + format_cross_script_coverage(cross_script_counts["either_direction"])
    )
    print(
        "  Both directions: "
        + format_cross_script_coverage(cross_script_counts["both_directions"])
    )