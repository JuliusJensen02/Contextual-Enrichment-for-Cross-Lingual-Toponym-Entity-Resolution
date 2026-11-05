"""Dense name embeddings with exact cosine search.

Symphonym is a custom BiLSTM, not a sentence-transformers model, so it has its own
backend. Its `inference.py` is imported from a pinned Hugging Face revision.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
from pathlib import Path

import numpy as np

from candidate_generation.data.schema import NameTable
from candidate_generation.generators.base import Generator, StringGroups, group_max

log = logging.getLogger(__name__)


class SymphonymBackend:
    """Character-level phonetic encoder (Gadd 2026)."""

    def __init__(self, spec: dict):
        from huggingface_hub import snapshot_download

        self.spec = spec
        directory = Path(
            snapshot_download(
                spec["repo"],
                revision=spec["revision"],
                allow_patterns=[
                    "config.json",
                    "inference.py",
                    "model.safetensors",
                    "vocab/*",
                ],
            )
        )
        module_spec = importlib.util.spec_from_file_location(
            "symphonym_inference", directory / "inference.py"
        )
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        self.model = module.SymphonymModel(directory)
        self.lang = spec.get("lang", "und")

    def encode(self, strings: list[str]) -> np.ndarray:
        size = self.spec.get("batch_size", 512)
        batches = [
            self.model.batch_embed([(s, self.lang) for s in strings[i : i + size]])
            for i in range(0, len(strings), size)
        ]
        return np.vstack(batches).astype(np.float32)


class SentenceTransformerBackend:
    def __init__(self, spec: dict):
        from sentence_transformers import SentenceTransformer

        self.spec = spec
        self.model = SentenceTransformer(
            spec["repo"], revision=spec["revision"], device="cpu"
        )
        self.prefix = spec.get("prefix", "")

    def encode(self, strings: list[str]) -> np.ndarray:
        return self.model.encode(
            [self.prefix + s for s in strings],
            batch_size=self.spec.get("batch_size", 64),
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)


BACKENDS = {
    "symphonym": SymphonymBackend,
    "sentence_transformers": SentenceTransformerBackend,
}


def load_backend(candidates: list[dict]) -> tuple[object, dict, list[dict]]:
    """Return the first loadable backend, its spec, and the ones that failed."""
    failures = []
    for spec in candidates:
        try:
            return BACKENDS[spec["backend"]](spec), spec, failures
        except Exception as error:  # noqa: BLE001 - any load failure means "try the next model"
            log.warning("could not load %s: %s", spec["repo"], error)
            failures.append({"repo": spec["repo"], "error": repr(error)[:300]})
    raise RuntimeError(f"no dense model could be loaded: {failures}")


class EmbeddingStore:
    """Embeds unique strings once and caches them on disk."""

    def __init__(self, backend: object, spec: dict, cache_dir: Path | None):
        self.backend = backend
        self.spec = spec
        self.cache_dir = cache_dir

    def embed(self, strings: list[str]) -> dict[str, np.ndarray]:
        # Length order keeps padding short; sorting also fixes the batch composition,
        # so the same strings always land in the same batches.
        unique = sorted(set(strings) - {""}, key=lambda s: (len(s), s))
        digest = hashlib.sha256(
            json.dumps(
                [
                    self.spec["repo"],
                    self.spec["revision"],
                    self.spec.get("prefix", ""),
                    unique,
                ]
            ).encode()
        ).hexdigest()[:24]
        cache_path = self.cache_dir / f"{digest}.npy" if self.cache_dir else None
        if cache_path and cache_path.exists():
            matrix = np.load(cache_path)
        else:
            log.info("embedding %d strings with %s", len(unique), self.spec["repo"])
            matrix = self.backend.encode(unique)
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                np.save(cache_path, matrix)
        return dict(zip(unique, matrix))


class Dense(Generator):
    """Scores a pair by the best cosine over both records' original-script names."""

    input_fields = frozenset({"name", "name_variants"})

    def __init__(self, name: str, store: EmbeddingStore):
        self.name = name
        self.store = store

    def _matrix(
        self, groups: StringGroups, vectors: dict[str, np.ndarray], size: int
    ) -> np.ndarray:
        zero = np.zeros(size, dtype=np.float32)
        return np.stack([vectors.get(s, zero) for s in groups.flat])

    def _prepare(self, query: NameTable, target: NameTable) -> None:
        self.query_strings = StringGroups(query.names)
        self.target_strings = StringGroups(target.names)
        vectors = self.store.embed(self.query_strings.flat + self.target_strings.flat)
        size = len(next(iter(vectors.values())))
        self.query_vectors = self._matrix(self.query_strings, vectors, size)
        self.target_vectors = self._matrix(self.target_strings, vectors, size)

    def score(self, query_indices: np.ndarray) -> np.ndarray:
        positions, offsets = self.query_strings.chunk(query_indices)
        cosine = self.query_vectors[positions] @ self.target_vectors.T
        scores = group_max(cosine, offsets, self.target_strings.offsets[:-1])
        scores[~self.query_strings.has_string[query_indices], :] = np.nan
        scores[:, ~self.target_strings.has_string] = np.nan
        return scores

    def metadata(self) -> dict:
        return {
            **super().metadata(),
            "repo": self.store.spec["repo"],
            "revision": self.store.spec["revision"],
            "prefix": self.store.spec.get("prefix", ""),
        }
