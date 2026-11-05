"""Build, write and hash the frozen candidate sets.

The output depends on names, the configuration and the seeds. No function here can
see which attributes an LLM prompt will use, so the files cannot vary with the prompt.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

GENERATOR = "union_rrf"
ORACLE_GENERATOR = "oracle"
COLUMNS = (
    "query_id",
    "candidate_id",
    "generator",
    "rank",
    "score",
    "k",
    "is_ground_truth",
    "oracle_injected",
    "shuffle_position",
)


def seeded_rng(seed: int, *key: object) -> np.random.Generator:
    """A generator that depends only on the seed and the key, not on call order."""
    text = "|".join(map(str, (seed, *key)))
    return np.random.default_rng(
        int.from_bytes(hashlib.sha256(text.encode()).digest()[:16], "big")
    )


def _rows_for_query(
    query_id, candidates, ranks, scores, generators, injected, shuffle, k, truth
):
    return {
        "query_id": [query_id] * len(candidates),
        "candidate_id": list(candidates),
        "generator": generators,
        "rank": ranks,
        "score": scores,
        "k": [k] * len(candidates),
        "is_ground_truth": [c in truth for c in candidates],
        "oracle_injected": injected,
        "shuffle_position": shuffle,
    }


def build_real(
    query_ids: Sequence[str],
    candidates: Sequence[Sequence[str]],
    scores: Sequence[Sequence[float]],
    ground_truth: Mapping[str, set[str]],
    k: int,
    seed: int,
    key: str,
) -> list[dict]:
    """One entry per query: exactly what the generator returned, in rank order."""
    out = []
    for query_id, query_candidates, query_scores in zip(query_ids, candidates, scores):
        count = len(query_candidates)
        shuffle = (
            seeded_rng(seed, key, "shuffle", query_id).permutation(count) + 1
        ).tolist()
        out.append(
            _rows_for_query(
                query_id,
                query_candidates,
                list(range(1, count + 1)),
                [float(s) for s in query_scores],
                [GENERATOR] * count,
                [False] * count,
                shuffle,
                k,
                ground_truth.get(query_id, set()),
            )
        )
    return out


def build_oracle(
    query_ids: Sequence[str],
    real: Sequence[dict],
    ground_truth: Mapping[str, set[str]],
    k: int,
    seed: int,
    key: str,
) -> list[dict]:
    """The real set, plus any missing true match at a seeded random position.

    Both the rank and the shuffle position are random. Existing candidates keep their
    relative order in both, so a real/oracle comparison differs only by the injection.
    `query_ids` is explicit because a query with no candidates has empty columns and
    still needs its true match injected.
    """
    out = []
    for query_id, row in zip(query_ids, real):
        truth = ground_truth.get(query_id, set())
        missing = sorted(truth - set(row["candidate_id"]))
        if not missing:
            out.append(row)
            continue
        rng = seeded_rng(seed, key, "oracle", query_id)
        rank_order = list(range(len(row["candidate_id"])))
        shuffle_order = sorted(rank_order, key=row["shuffle_position"].__getitem__)
        candidates = list(row["candidate_id"])
        scores = list(row["score"])
        generators = list(row["generator"])
        injected = list(row["oracle_injected"])
        for match in missing:
            index = len(candidates)
            candidates.append(match)
            scores.append(float("nan"))
            generators.append(ORACLE_GENERATOR)
            injected.append(True)
            rank_order.insert(int(rng.integers(0, len(rank_order) + 1)), index)
            shuffle_order.insert(int(rng.integers(0, len(shuffle_order) + 1)), index)
        shuffle = [0] * len(candidates)
        for position, index in enumerate(shuffle_order, start=1):
            shuffle[index] = position
        out.append(
            _rows_for_query(
                query_id,
                [candidates[i] for i in rank_order],
                list(range(1, len(candidates) + 1)),
                [scores[i] for i in rank_order],
                [generators[i] for i in rank_order],
                [injected[i] for i in rank_order],
                [shuffle[i] for i in rank_order],
                k,
                truth,
            )
        )
    return out


SCHEMA = pa.schema(
    [
        ("query_id", pa.string()),
        ("candidate_id", pa.string()),
        ("generator", pa.string()),
        ("rank", pa.int32()),
        ("score", pa.float64()),
        ("k", pa.int32()),
        ("is_ground_truth", pa.bool_()),
        ("oracle_injected", pa.bool_()),
        ("shuffle_position", pa.int32()),
    ]
)


def to_table(rows: Sequence[dict]) -> pa.Table:
    arrays = {column: [] for column in COLUMNS}
    for row in rows:
        for column in COLUMNS:
            arrays[column].extend(row[column])
    score = np.asarray(arrays["score"], dtype=np.float64)
    columns = {
        column: pa.array(arrays[column], SCHEMA.field(column).type)
        for column in COLUMNS
        if column != "score"
    }
    columns["score"] = pa.array(score, pa.float64(), mask=np.isnan(score))
    return pa.table({column: columns[column] for column in COLUMNS}, schema=SCHEMA)


class FrozenWriter:
    """Streams batches to one parquet file with fixed settings."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.writer = pq.ParquetWriter(
            path, SCHEMA, compression="zstd", use_dictionary=True
        )
        self.rows = 0

    def write(self, rows: Sequence[dict]) -> None:
        table = to_table(rows)
        self.rows += table.num_rows
        self.writer.write_table(table)

    def close(self) -> str:
        self.writer.close()
        return sha256_file(self.path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
