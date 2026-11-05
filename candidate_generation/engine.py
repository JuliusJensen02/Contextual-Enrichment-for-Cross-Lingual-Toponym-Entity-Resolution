"""Score the full cross product of one task and direction, chunk by chunk.

Each chunk produces full score matrices, so ranks are exact over all targets. Only
the top `max_k` per query and the ranks of ground truth pairs are kept. Everything
runs single-threaded per chunk, so results do not depend on BLAS thread partitioning.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
from threadpoolctl import threadpool_limits

from candidate_generation.data.schema import NameTable
from candidate_generation.generators import Generator
from candidate_generation.generators.union_rrf import (
    UNRANKED,
    ranks_from_scores,
    reciprocal_rank_fusion,
)

log = logging.getLogger(__name__)
SCORE_DECIMALS = 6
RRF_DECIMALS = 9


@dataclass
class DirectionResult:
    task: str
    direction: str
    query_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    truth_query: np.ndarray  # query index of each ground truth pair
    truth_target: np.ndarray  # target index of each ground truth pair
    ranks: dict[str, np.ndarray]  # generator -> rank of each ground truth pair
    top: dict[
        str, np.ndarray
    ]  # generator -> (n_queries, depth) target indices, -1 = none
    top_scores: dict[str, np.ndarray]  # fused generator -> (n_queries, depth) scores
    retrieved: dict[str, np.ndarray]  # generator -> candidates retrieved per query


def top_targets(ranks: np.ndarray, depth: int) -> np.ndarray:
    """Return target indices ordered by rank, -1 where fewer than depth were retrieved."""
    depth = min(depth, ranks.shape[1])
    part = np.argpartition(ranks, depth - 1, axis=1)[:, :depth]
    values = np.take_along_axis(ranks, part, axis=1)
    order = np.argsort(values, axis=1, kind="stable")
    top = np.take_along_axis(part, order, axis=1)
    top[np.take_along_axis(values, order, axis=1) == UNRANKED] = -1
    return top.astype(np.int32)


def run_direction(
    task: str,
    direction: str,
    query: NameTable,
    target: NameTable,
    pairs: list[tuple[str, str]],
    generators: list[Generator],
    fusions: dict[str, list[str]],
    rrf_constant: int,
    max_k: int,
    chunk_size: int,
    workers: int,
) -> DirectionResult:
    for generator in generators:
        generator.prepare(query, target)
    query_index = {record_id: i for i, record_id in enumerate(query.record_ids)}
    target_index = {record_id: i for i, record_id in enumerate(target.record_ids)}
    truth_query = np.array([query_index[q] for q, _ in pairs], dtype=np.int64)
    truth_target = np.array([target_index[t] for _, t in pairs], dtype=np.int64)
    names = [g.name for g in generators] + list(fusions)
    depth = min(max_k, len(target))
    n_queries = len(query)
    ranks = {name: np.full(len(pairs), UNRANKED, dtype=np.int32) for name in names}
    top = {name: np.full((n_queries, depth), -1, dtype=np.int32) for name in names}
    top_scores = {name: np.full((n_queries, depth), np.nan) for name in fusions}
    retrieved = {name: np.zeros(n_queries, dtype=np.int64) for name in names}
    pair_order = np.argsort(truth_query, kind="stable")
    sorted_queries = truth_query[pair_order]

    def process(indices: np.ndarray) -> None:
        chunk_ranks: dict[str, np.ndarray] = {}
        for generator in generators:
            scores = np.round(generator.score(indices), SCORE_DECIMALS)
            chunk_ranks[generator.name] = ranks_from_scores(scores)
            retrieved[generator.name][indices] = (~np.isnan(scores)).sum(axis=1)
        chunk_scores = {}
        for name, inputs in fusions.items():
            fused = np.round(
                reciprocal_rank_fusion([chunk_ranks[i] for i in inputs], rrf_constant),
                RRF_DECIMALS,
            )
            chunk_ranks[name] = ranks_from_scores(fused)
            chunk_scores[name] = fused
            retrieved[name][indices] = (~np.isnan(fused)).sum(axis=1)
        first = np.searchsorted(sorted_queries, indices[0], side="left")
        last = np.searchsorted(sorted_queries, indices[-1], side="right")
        chunk_pairs = pair_order[first:last]
        rows = truth_query[chunk_pairs] - indices[0]
        columns = truth_target[chunk_pairs]
        for name, matrix in chunk_ranks.items():
            ranks[name][chunk_pairs] = matrix[rows, columns]
            top[name][indices] = top_targets(matrix, depth)
        for name, fused in chunk_scores.items():
            present = top[name][indices] >= 0
            values = np.take_along_axis(
                fused, np.maximum(top[name][indices], 0), axis=1
            )
            top_scores[name][indices] = np.where(present, values, np.nan)

    chunks = [
        np.arange(s, min(s + chunk_size, n_queries))
        for s in range(0, n_queries, chunk_size)
    ]
    with threadpool_limits(limits=1), ThreadPoolExecutor(workers) as pool:
        for done, _ in enumerate(pool.map(process, chunks), start=1):
            if done % 200 == 0:
                log.info("%s %s: %d/%d chunks", task, direction, done, len(chunks))
    return DirectionResult(
        task,
        direction,
        query.record_ids,
        target.record_ids,
        truth_query,
        truth_target,
        ranks,
        top,
        top_scores,
        retrieved,
    )
