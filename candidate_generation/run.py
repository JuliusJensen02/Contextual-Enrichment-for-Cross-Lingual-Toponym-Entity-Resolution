"""Run the benchmark: python -m candidate_generation.run --dataset mehdie|pleiades_trismegistos|all"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import logging
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from candidate_generation import __version__
from candidate_generation.data import ADAPTERS, Dataset, Record
from candidate_generation.data.schema import name_table, records_by_id
from candidate_generation.engine import DirectionResult, run_direction
from candidate_generation.frozen import (
    FrozenWriter,
    build_oracle,
    build_real,
    seeded_rng,
    sha256_file,
)
from candidate_generation.generators import (
    Dense,
    EmbeddingStore,
    MehdieBpf,
    TfidfChar,
    load_backend,
)
from candidate_generation.generators.union_rrf import UNRANKED, set_union_rank
from candidate_generation.metrics import (
    choose_k,
    mean_reciprocal_rank,
    pair_completeness,
    pair_quality,
    recall_at_k,
    reduction_ratio,
    wilson_interval,
)

log = logging.getLogger("candidate_generation")
ROOT = Path(__file__).resolve().parent.parent
FUSED = "union_rrf"
FUSED_BLOCKING = "union_rrf_bpf"
UNION = "union_set"
BLOCKS = "mehdie_bpf_blocks"
PACKAGES = (
    "numpy",
    "scipy",
    "scikit-learn",
    "rapidfuzz",
    "epitran",
    "anyascii",
    "torch",
    "sentence-transformers",
    "transformers",
    "pyarrow",
)


def hash_inputs(path: Path) -> dict[str, str]:
    """SHA256 of every file of a dataset folder. Used to prove the data was not changed."""
    return {
        str(p.relative_to(ROOT)): sha256_file(p)
        for p in sorted(path.rglob("*"))
        if p.is_file() and ".cache" not in p.parts
    }


def split_queries(query_ids, truth_query, n_queries, fraction, seed, key) -> np.ndarray:
    """Return a boolean dev mask, stratified on having a ground truth match."""
    has_truth = np.zeros(n_queries, dtype=bool)
    has_truth[truth_query] = True
    is_dev = np.zeros(n_queries, dtype=bool)
    order = np.argsort(np.asarray(query_ids, dtype=object), kind="stable")
    for stratum in (True, False):
        members = order[has_truth[order] == stratum]
        permuted = seeded_rng(seed, key, "split", stratum).permutation(members)
        is_dev[permuted[: round(fraction * len(members))]] = True
    return is_dev


def prepare_target_order(records: list[Record], seed: int, key: str) -> list[Record]:
    """Shuffle targets once. Ties break by this order, which is unrelated to any id."""
    ordered = sorted(records, key=lambda r: r.record_id)
    return [
        ordered[i] for i in seeded_rng(seed, key, "targets").permutation(len(ordered))
    ]


def union_sizes(result: DirectionResult, inputs: list[str], k: int) -> np.ndarray:
    """Per-query size of the set union of the inputs' top-k lists."""
    stacked = np.concatenate([result.top[name][:, :k] for name in inputs], axis=1)
    stacked = np.sort(stacked, axis=1)
    distinct = (stacked[:, 1:] != stacked[:, :-1]) & (stacked[:, 1:] >= 0)
    return distinct.sum(axis=1) + (stacked[:, 0] >= 0)


def metric_row(results, masks, generator, k, ks, union_inputs) -> dict:
    """Metrics over a set of queries, pooled across results."""
    found = truths = candidates = cross = n_queries = n_no_truth = 0
    all_ranks, all_ids = [], []
    for offset, (result, mask) in enumerate(zip(results, masks)):
        in_split = mask[result.truth_query]
        if generator == UNION:
            ranks = set_union_rank(
                [result.ranks[name][in_split] for name in union_inputs]
            )
            per_query = union_sizes(result, union_inputs, k)
        elif generator == BLOCKS:
            ranks = result.ranks["mehdie_bpf"][in_split]
            per_query = result.retrieved["mehdie_bpf"]
        else:
            ranks = result.ranks[generator][in_split]
            per_query = np.minimum(result.retrieved[generator], k)
        found += int(
            (ranks != UNRANKED).sum() if generator == BLOCKS else (ranks <= k).sum()
        )
        truths += len(ranks)
        candidates += int(per_query[mask].sum())
        cross += int(mask.sum()) * len(result.target_ids)
        n_queries += int(mask.sum())
        matched = np.zeros(len(mask), dtype=bool)
        matched[result.truth_query] = True
        n_no_truth += int((mask & ~matched).sum())
        all_ranks.append(ranks)
        all_ids.extend((offset, q) for q in result.truth_query[in_split])
    ranks = np.concatenate(all_ranks)
    query_keys = [f"{a}:{b}" for a, b in all_ids]
    low, high = wilson_interval(found, truths)
    row = {
        "generator": generator,
        "k": "blocks" if generator == BLOCKS else k,
        "n_queries": n_queries,
        "n_queries_no_ground_truth": n_no_truth,
        "n_ground_truth_pairs": truths,
        "pair_completeness": pair_completeness(found, truths),
        "pc_ci_low": low,
        "pc_ci_high": high,
        "pair_quality": pair_quality(found, candidates),
        "reduction_ratio": reduction_ratio(candidates, cross),
        "mean_candidates": candidates / n_queries if n_queries else float("nan"),
        "total_candidates": candidates,
        "mrr": float("nan")
        if generator == UNION
        else mean_reciprocal_rank(ranks, query_keys),
    }
    row.update({f"recall@{x}": recall_at_k(ranks, x) for x in ks})
    return row


def _share(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def field_coverage(dataset: Dataset) -> list[dict]:
    rows = []
    for source, records in dataset.gazetteers.items():
        count = len(records)
        scripts: dict[str, int] = {}
        for record in records:
            scripts[record.script] = scripts.get(record.script, 0) + 1
        rows.append(
            {
                "dataset": dataset.name,
                "source": source,
                "records": count,
                "name": _share(sum(bool(r.name) for r in records), count),
                "name_variants": _share(
                    sum(bool(r.name_variants) for r in records), count
                ),
                "mean_names_per_record": round(
                    sum(len(r.all_names) for r in records) / max(count, 1), 2
                ),
                "transliteration_in_dataset": _share(
                    sum(r.transliteration_source == "dataset" for r in records), count
                ),
                "transliteration_derived": _share(
                    sum(r.transliteration_source == "derived" for r in records), count
                ),
                "ipa_in_dataset": 0.0,
                "ipa_derived_any": _share(sum(any(r.ipa) for r in records), count),
                "ipa_primary_epitran": _share(
                    sum(r.ipa_source == "epitran" for r in records), count
                ),
                "ipa_primary_rules": _share(
                    sum(r.ipa_source == "rules" for r in records), count
                ),
                "ipa_primary_anyascii": _share(
                    sum(r.ipa_source == "anyascii" for r in records), count
                ),
                "coordinates": _share(
                    sum(r.lat is not None and r.lon is not None for r in records), count
                ),
                "feature_type": _share(
                    sum(bool(r.feature_type) for r in records), count
                ),
                "scripts": json.dumps(
                    dict(sorted(scripts.items(), key=lambda kv: -kv[1]))
                ),
            }
        )
    return rows


def exact_name_overlap(dataset: Dataset) -> list[dict]:
    """How many ground truth pairs already share a string, needing no cross-script match."""
    rows = []
    for task in dataset.tasks:
        source = records_by_id(dataset.gazetteers[task.source])
        target = records_by_id(dataset.gazetteers[task.target])
        shared_name = shared_ipa = 0
        for source_id, target_id in task.pairs:
            left, right = source[source_id], target[target_id]
            shared_name += bool(set(left.all_names) & set(right.all_names))
            shared_ipa += bool(set(left.ipa) & set(right.ipa) - {""})
        rows.append(
            {
                "dataset": dataset.name,
                "task": task.name,
                "ground_truth_pairs": len(task.pairs),
                "pairs_sharing_an_exact_name": shared_name,
                "pairs_sharing_an_ipa_form": shared_ipa,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(field for row in rows for field in row))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_generators(config: dict, cache: Path | None) -> tuple[list, dict]:
    settings = config["generators"]
    backend, spec, failures = load_backend(settings["dense"]["candidates"])
    store = EmbeddingStore(backend, spec, cache)
    models = {
        "dense": {
            "repo": spec["repo"],
            "revision": spec["revision"],
            "failed": failures,
        }
    }
    factories = [
        lambda: MehdieBpf(settings["representation"]),
        lambda: TfidfChar(
            settings["representation"], settings["tfidf_char"]["ngram_range"]
        ),
        lambda: Dense("dense", store),
    ]
    second = settings["dense"]["second_model"]
    if second.get("enabled"):
        try:
            second_backend, second_spec, _ = load_backend([second])
            second_store = EmbeddingStore(second_backend, second_spec, cache)
            factories.append(lambda: Dense(second["name"], second_store))
            models[second["name"]] = {
                "repo": second_spec["repo"],
                "revision": second_spec["revision"],
            }
        except RuntimeError as error:
            log.warning("skipping second dense model: %s", error)
            models[second["name"]] = {
                "repo": second["repo"],
                "failed": str(error)[:300],
            }
    return factories, models


def score_dataset(
    dataset: Dataset, config: dict, factories: list
) -> dict[str, list[DirectionResult]]:
    settings = config["generators"]["union_rrf"]
    runtime = config["runtime"]
    fusions = {
        FUSED: settings["inputs"],
        FUSED_BLOCKING: settings["with_blocking_inputs"],
    }
    out: dict[str, list[DirectionResult]] = {}
    for direction in dataset.directions:
        out[direction] = []
        for task in dataset.tasks:
            forward = direction == "forward"
            query_source, target_source = (
                (task.source, task.target) if forward else (task.target, task.source)
            )
            key = f"{dataset.name}/{task.name}/{direction}"
            queries = sorted(
                dataset.gazetteers[query_source], key=lambda r: r.record_id
            )
            targets = prepare_target_order(
                dataset.gazetteers[target_source], config["seed"], key
            )
            pairs = sorted(task.pairs if forward else [(t, s) for s, t in task.pairs])
            log.info(
                "%s: %d x %d, %d ground truth pairs",
                key,
                len(queries),
                len(targets),
                len(pairs),
            )
            out[direction].append(
                run_direction(
                    task.name,
                    direction,
                    name_table(queries),
                    name_table(targets),
                    pairs,
                    [factory() for factory in factories],
                    fusions,
                    settings["constant"],
                    config["evaluation"]["max_k"],
                    runtime["chunk_size"],
                    runtime["workers"],
                )
            )
    return out


def plot_recall(
    path: Path, curves: dict, chosen: dict, generators: list[str], title: str
) -> None:
    """One panel per direction, with every generator on it."""
    colours = dict(
        zip(
            generators,
            (
                "#2a78d6",
                "#eb6834",
                "#1baf7a",
                "#eda100",
                "#e87ba4",
                "#008300",
                "#6250d6",
            ),
        )
    )
    directions = list(curves)
    figure, axes = plt.subplots(
        1,
        len(directions),
        figsize=(6.2 * len(directions), 4.6),
        sharey=True,
        squeeze=False,
        facecolor="#fcfcfb",
    )
    for axis, direction in zip(axes[0], directions):
        axis.set_facecolor("#fcfcfb")
        for generator in generators:
            ks, values = curves[direction][generator]
            axis.plot(
                ks,
                values,
                color=colours[generator],
                linewidth=2,
                marker="o",
                markersize=4,
                markeredgecolor="#fcfcfb",
                markeredgewidth=0.8,
                label=generator,
                solid_capstyle="round",
            )
        axis.axvline(chosen[direction], color="#52514e", linewidth=1)
        axis.annotate(
            f"chosen k = {chosen[direction]}",
            (chosen[direction], 0.02),
            xytext=(-5, 0),
            textcoords="offset points",
            ha="right",
            color="#52514e",
            fontsize=9,
        )
        axis.set_xscale("log")
        axis.set_xticks(ks, [str(x) for x in ks], fontsize=8)
        axis.minorticks_off()
        axis.set_ylim(0, 1.02)
        axis.set_xlabel("k")
        axis.set_title(direction, loc="left", color="#0b0b0b", fontsize=11)
        axis.grid(True, color="#e5e4e0", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
        axis.spines[["left", "bottom"]].set_color("#c3c2b7")
    axes[0][0].set_ylabel("Recall@k (test queries)")
    figure.suptitle(title, x=0.01, ha="left", color="#0b0b0b", fontsize=12)
    handles, labels = axes[0][0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        ncol=len(generators),
        frameon=False,
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.07, 1, 0.97))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, metadata={"Software": None})
    plt.close(figure)


def write_frozen(dataset, result, is_dev, k, config, output_dir, version_tag) -> dict:
    seed = config["seed"]
    key = f"{dataset.name}/{result.task}/{result.direction}"
    truth: dict[str, set[str]] = {}
    for q, t in zip(result.truth_query, result.truth_target):
        truth.setdefault(result.query_ids[q], set()).add(result.target_ids[t])
    stem = f"{result.task}.{result.direction}"
    real = FrozenWriter(output_dir / f"{stem}.real.{version_tag}.parquet")
    oracle = FrozenWriter(output_dir / f"{stem}.oracle.{version_tag}.parquet")
    size = config["runtime"]["frozen_batch"]
    targets = result.target_ids
    top = result.top[FUSED][:, :k]
    scores = result.top_scores[FUSED][:, :k]
    injected = 0
    for start in range(0, len(result.query_ids), size):
        ids = result.query_ids[start : start + size]
        candidates = [
            [targets[t] for t in row if t >= 0] for row in top[start : start + size]
        ]
        kept = [s[: len(c)] for s, c in zip(scores[start : start + size], candidates)]
        real_rows = build_real(ids, candidates, kept, truth, k, seed, key)
        oracle_rows = build_oracle(ids, real_rows, truth, k, seed, key)
        injected += sum(sum(row["oracle_injected"]) for row in oracle_rows)
        real.write(real_rows)
        oracle.write(oracle_rows)
    split_path = output_dir / f"{stem}.splits.{version_tag}.parquet"
    pq.write_table(
        pa.table(
            {
                "query_id": pa.array(result.query_ids, pa.string()),
                "split": pa.array(
                    ["dev" if d else "test" for d in is_dev], pa.string()
                ),
                "has_ground_truth": pa.array(
                    [q in truth for q in result.query_ids], pa.bool_()
                ),
            }
        ),
        split_path,
        compression="zstd",
    )
    files = {
        real.path: real.close(),
        oracle.path: oracle.close(),
        split_path: sha256_file(split_path),
    }
    return {
        "files": {p.name: h for p, h in files.items()},
        "rows": {"real": real.rows, "oracle": oracle.rows},
        "oracle_injected_pairs": injected,
    }


def run_dataset(name: str, config: dict, factories: list, models: dict) -> list[dict]:
    settings = config["datasets"][name]
    input_path = ROOT / settings["path"]
    inputs_before = hash_inputs(input_path)
    dataset = ADAPTERS[settings["adapter"]](settings, ROOT)
    log.info("%s notes: %s", name, json.dumps(dataset.notes, ensure_ascii=False)[:1000])
    results_dir = ROOT / config["results_dir"] / name
    output_dir = ROOT / config["output_dir"] / name
    evaluation = config["evaluation"]
    seed = config["seed"]
    write_csv(results_dir / "field_coverage.csv", field_coverage(dataset))
    write_csv(results_dir / "exact_name_overlap.csv", exact_name_overlap(dataset))
    scored = score_dataset(dataset, config, factories)

    union_inputs = config["generators"]["union_rrf"]["inputs"]
    ranked = [factory().name for factory in factories] + [FUSED, FUSED_BLOCKING, UNION]
    metric_rows, chosen, curves, frozen, overlap_counts, overlap_rows = (
        [],
        {},
        {},
        {},
        [],
        [],
    )
    misses: dict[str, list[dict]] = {g: [] for g in ranked}
    records = {s: records_by_id(r) for s, r in dataset.gazetteers.items()}
    tasks = {t.name: t for t in dataset.tasks}

    for direction, results in scored.items():
        masks_dev = []
        for result in results:
            key = f"{name}/{result.task}/{direction}"
            masks_dev.append(
                split_queries(
                    result.query_ids,
                    result.truth_query,
                    len(result.query_ids),
                    evaluation["dev_fraction"],
                    seed,
                    key,
                )
            )
        masks_test = [~m for m in masks_dev]
        dev_ranks = np.concatenate(
            [r.ranks[FUSED][m[r.truth_query]] for r, m in zip(results, masks_dev)]
        )
        k, reached, dev_recall = choose_k(
            dev_ranks, evaluation["target_recall"], evaluation["max_k"]
        )
        chosen[direction] = {
            "k": k,
            "target_reached_on_dev": reached,
            "dev_recall": dev_recall,
            "n_dev_ground_truth_pairs": int(dev_ranks.size),
            "target": evaluation["target_recall"],
        }
        log.info(
            "%s %s: k=%d reached=%s dev recall=%.4f on %d pairs",
            name,
            direction,
            k,
            reached,
            dev_recall,
            dev_ranks.size,
        )
        generators = ranked + [BLOCKS]
        for generator in generators:
            for scope, group, masks in (
                ("ALL", results, masks_test),
                *((r.task, [r], [m]) for r, m in zip(results, masks_test)),
            ):
                metric_rows.append(
                    {
                        "dataset": name,
                        "task": scope,
                        "direction": direction,
                        "split": "test",
                        **metric_row(
                            group, masks, generator, k, evaluation["ks"], union_inputs
                        ),
                    }
                )
        curves[direction] = {}
        for generator in ranked:
            ks = [x for x in evaluation["plot_ks"] if x <= max(evaluation["plot_ks"])]
            test_ranks = []
            for result, mask in zip(results, masks_test):
                in_split = mask[result.truth_query]
                test_ranks.append(
                    set_union_rank([result.ranks[g][in_split] for g in union_inputs])
                    if generator == UNION
                    else result.ranks[generator][in_split]
                )
            joined = np.concatenate(test_ranks)
            curves[direction][generator] = (ks, [recall_at_k(joined, x) for x in ks])

        signatures: dict[str, int] = {}
        for result, is_dev, mask_test in zip(results, masks_dev, masks_test):
            task = tasks[result.task]
            forward = direction == "forward"
            q_source, t_source = (
                (task.source, task.target) if forward else (task.target, task.source)
            )
            union_rank = set_union_rank([result.ranks[g] for g in union_inputs])
            for pair, (q, t) in enumerate(zip(result.truth_query, result.truth_target)):
                split = "dev" if is_dev[q] else "test"
                query_record = records[q_source][result.query_ids[q]]
                target_record = records[t_source][result.target_ids[t]]
                hits = []
                for generator in ranked:
                    rank = (
                        union_rank[pair]
                        if generator == UNION
                        else result.ranks[generator][pair]
                    )
                    if rank <= k:
                        hits.append(generator)
                        continue
                    misses[generator].append(
                        {
                            "dataset": name,
                            "task": result.task,
                            "direction": direction,
                            "split": split,
                            "k": k,
                            "query_id": query_record.record_id,
                            "query_name": query_record.name,
                            "query_variants": " | ".join(query_record.name_variants),
                            "query_ipa": query_record.ipa[0]
                            if query_record.ipa
                            else "",
                            "target_id": target_record.record_id,
                            "target_name": target_record.name,
                            "target_variants": " | ".join(target_record.name_variants),
                            "target_ipa": target_record.ipa[0]
                            if target_record.ipa
                            else "",
                            "rank": "" if rank == UNRANKED else int(rank),
                        }
                    )
                signature = "+".join(hits) or "none"
                overlap_rows.append(
                    {
                        "dataset": name,
                        "task": result.task,
                        "direction": direction,
                        "split": split,
                        "query_id": query_record.record_id,
                        "target_id": target_record.record_id,
                        "k": k,
                        "retrieved_by": signature,
                    }
                )
                if split == "test":
                    signatures[signature] = signatures.get(signature, 0) + 1
            frozen[f"{result.task}.{direction}"] = write_frozen(
                dataset, result, is_dev, k, config, output_dir, f"v{config['version']}"
            )
        overlap_counts.extend(
            {
                "dataset": name,
                "direction": direction,
                "split": "test",
                "retrieved_by": s,
                "pairs": n,
            }
            for s, n in sorted(signatures.items(), key=lambda kv: -kv[1])
        )

    write_csv(results_dir / "metrics.csv", metric_rows)
    write_csv(results_dir / "overlap_pairs.csv", overlap_rows)
    write_csv(results_dir / "overlap_counts.csv", overlap_counts)
    for generator, rows in misses.items():
        write_csv(
            results_dir / "misses" / f"{generator}.csv", rows or [{"note": "no misses"}]
        )
    plot_recall(
        results_dir / "recall_at_k.png",
        curves,
        {d: c["k"] for d, c in chosen.items()},
        [g for g in ranked if g != FUSED_BLOCKING],
        f"{name}: Recall@k",
    )

    inputs_after = hash_inputs(input_path)
    if inputs_before != inputs_after:
        changed = [p for p in inputs_before if inputs_before[p] != inputs_after.get(p)]
        raise RuntimeError(f"dataset files changed during the run: {changed}")

    manifest = {
        "benchmark_version": __version__,
        "output_version": config["version"],
        "dataset": name,
        "timestamp": datetime.now(UTC).isoformat(),
        "seed": seed,
        "config": config,
        "models": models,
        "chosen_k": chosen,
        "dataset_notes": dataset.notes,
        "frozen_outputs": frozen,
        "input_files_sha256": inputs_after,
        "packages": {p: version(p) for p in PACKAGES},
        "python": platform.python_version(),
    }
    (output_dir).mkdir(parents=True, exist_ok=True)
    with open(
        output_dir / f"manifest.v{config['version']}.json", "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False, default=str)
    return metric_rows


def output_digest(config: dict, names: list[str]) -> str:
    """A hash over every frozen file. It excludes the manifest, which holds a timestamp."""
    digest = hashlib.sha256()
    for name in names:
        for path in sorted((ROOT / config["output_dir"] / name).glob("*.parquet")):
            digest.update(path.name.encode())
            digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="all")
    parser.add_argument(
        "--config", default=str(Path(__file__).with_name("config.yaml"))
    )
    parser.add_argument("--no-cache", action="store_true", help="recompute embeddings")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    with open(args.config, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    names = list(config["datasets"]) if args.dataset == "all" else [args.dataset]
    unknown = set(names) - set(config["datasets"])
    if unknown:
        parser.error(
            f"unknown dataset: {sorted(unknown)}; choose from {sorted(config['datasets'])} or all"
        )
    cache = None if args.no_cache else ROOT / config["cache_dir"] / "embeddings"
    factories, models = build_generators(copy.deepcopy(config), cache)
    for name in names:
        rows = run_dataset(name, config, factories, models)
        for row in rows:
            if row["task"] == "ALL" and row["generator"] == FUSED:
                log.info(
                    "%s %s k=%s PC=%.4f PQ=%.5f RR=%.5f MRR=%.4f",
                    name,
                    row["direction"],
                    row["k"],
                    row["pair_completeness"],
                    row["pair_quality"],
                    row["reduction_ratio"],
                    row["mrr"],
                )
    print("output digest:", output_digest(config, names))


if __name__ == "__main__":
    main()
