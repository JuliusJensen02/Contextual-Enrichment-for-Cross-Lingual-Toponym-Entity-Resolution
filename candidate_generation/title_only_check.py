"""Sensitivity check: how much of the MEHDIE testset result comes from name variants?

Some gazetteers list the other side's exact string among their variants, so scoring
over all variants can bypass cross-script matching. This reruns the two main ranked
generators on primary names only, per testset. It writes results, not frozen sets.

    python -m candidate_generation.title_only_check
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from candidate_generation.data import ADAPTERS
from candidate_generation.data.schema import Record, name_table
from candidate_generation.generators import (
    Dense,
    EmbeddingStore,
    TfidfChar,
    load_backend,
)
from candidate_generation.generators.union_rrf import ranks_from_scores
from candidate_generation.metrics import mean_reciprocal_rank, recall_at_k
from candidate_generation.run import ROOT, write_csv


def primary_only(records: list[Record]) -> list[Record]:
    return [
        replace(
            r, name_variants=(), transliteration=r.transliteration[:1], ipa=r.ipa[:1]
        )
        for r in records
    ]


def evaluate(generator, query, target, pairs) -> dict[str, float]:
    query_index = {r.record_id: i for i, r in enumerate(query)}
    target_index = {r.record_id: i for i, r in enumerate(target)}
    generator.prepare(name_table(query), name_table(target))
    ranks = ranks_from_scores(np.round(generator.score(np.arange(len(query))), 6))
    pair_ranks = np.array([ranks[query_index[q], target_index[t]] for q, t in pairs])
    return {
        "recall@1": recall_at_k(pair_ranks, 1),
        "recall@10": recall_at_k(pair_ranks, 10),
        "mrr": mean_reciprocal_rank(pair_ranks, [q for q, _ in pairs]),
    }


def main() -> None:
    config = yaml.safe_load(
        Path(__file__).with_name("config.yaml").read_text(encoding="utf-8")
    )
    settings = config["datasets"]["mehdie_testsets"]
    dataset = ADAPTERS[settings["adapter"]](settings, ROOT)
    backend, spec, _ = load_backend(config["generators"]["dense"]["candidates"])
    store = EmbeddingStore(backend, spec, ROOT / config["cache_dir"] / "embeddings")
    rows = []
    for task in dataset.tasks:
        query = sorted(dataset.gazetteers[task.source], key=lambda r: r.record_id)
        target = sorted(dataset.gazetteers[task.target], key=lambda r: r.record_id)
        for names, transform in (
            ("all_variants", list),
            ("primary_only", primary_only),
        ):
            for generator in (TfidfChar(), Dense("dense", store)):
                result = evaluate(
                    generator, transform(query), transform(target), task.pairs
                )
                rows.append(
                    {
                        "task": task.name,
                        "names": names,
                        "generator": generator.name,
                        **result,
                    }
                )
    write_csv(
        ROOT / config["results_dir"] / "mehdie_testsets" / "title_only_check.csv", rows
    )


if __name__ == "__main__":
    main()
