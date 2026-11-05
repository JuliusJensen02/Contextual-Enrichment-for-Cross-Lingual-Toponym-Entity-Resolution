"""Adapter for the five benchmark testsets of Sagi et al. (2025) in datasets/MEHDIE.

These overlap the DB extract only partly and are the only source for Tudela and
DAMAST, so they run as a separate dataset rather than being merged into `mehdie`.
Each testset has its own small record pools, which is what makes results comparable
with the published numbers. The `id` and `matches` columns are never given to a
generator: Tudela's carry Kima and Wikidata identifiers.
"""

from __future__ import annotations

from pathlib import Path

from candidate_generation.data.build import make_record, parse_float, read_rows
from candidate_generation.data.name_cleaning import split_variants, tidy, uniq
from candidate_generation.data.schema import Dataset, Record, Task

KIMA_FEATURE_COLUMNS = ("types", "type")


def _load_file(path: Path, source: str, separators: str) -> list[Record]:
    records = []
    for row in read_rows(path, "\t"):
        names = uniq(
            [
                tidy(row.get("title", "")),
                *split_variants(row.get("variants", ""), separators),
            ]
        )
        feature = next((row[c] for c in KIMA_FEATURE_COLUMNS if row.get(c)), None)
        records.append(
            make_record(
                row["id"],
                source,
                names,
                parse_float(row.get("lat")),
                parse_float(row.get("lon")),
                feature,
            )
        )
    # A few source files repeat an id; keep the first row, as ground truth has one target.
    return list({r.record_id: r for r in records}.values())


def load_mehdie_testsets(config: dict, root: Path) -> Dataset:
    base = root / config["path"]
    gazetteers: dict[str, list[Record]] = {}
    tasks = []
    for task in config["tasks"]:
        folder = base / task["folder"]
        source = f"{task['name']}:{task['source']}"
        target = f"{task['name']}:{task['target']}"
        gazetteers[source] = _load_file(
            folder / task["source_file"], source, task.get("source_separators", ";")
        )
        gazetteers[target] = _load_file(
            folder / task["target_file"], target, task.get("target_separators", ";")
        )
        rows = read_rows(folder / "em.tsv", "\t")
        pairs = tuple(sorted({(r["id_1"], r["id_2"]) for r in rows}))
        tasks.append(Task(task["name"], source, target, pairs))
    return Dataset(
        name="mehdie_testsets",
        gazetteers=gazetteers,
        tasks=tasks,
        directions=config["directions"],
        notes={"testsets": len(tasks)},
    )
