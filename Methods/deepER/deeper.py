"""DeepER-style tuple representations and pairwise entity matching.

Text attributes use multilingual LaBSE vectors, pooled across a record's
aliases where needed. Pairwise attribute similarities are classified together,
as in DeepER's averaging-based representation pipeline.
"""

import math
import os
import re
from difflib import SequenceMatcher
from io import StringIO
from pathlib import Path
from typing import Optional

import numpy as np
from dotenv import dotenv_values

MODEL_NAME = "sentence-transformers/LaBSE"
TEXT_ATTRIBUTES = ("name", "relation", "classification", "description")
FEATURE_NAMES = (
    *(f"{attribute}_similarity" for attribute in TEXT_ATTRIBUTES),
    "phonetic_similarity",
    "geo_distance_km",
    "temporal_overlap",
    "temporal_gap_years",
)

_VALUE_SEPARATOR = re.compile(r"\s*[|;،]\s*")
_HF_TOKEN_LINE = re.compile(r"^\s*(?:export\s+)?HF_TOKEN\s*[:=]\s*(.*?)\s*$")
_default_extractor: Optional["DeepERFeatureExtractor"] = None


def _hugging_face_token() -> Optional[str]:
    """Read HF_TOKEN from the environment or the project .env file."""
    token = os.getenv("HF_TOKEN")
    if token:
        return token

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return None

    with env_path.open(encoding="utf-8-sig") as env_file:
        for line in env_file:
            match = _HF_TOKEN_LINE.match(line)
            if match:
                # Normalize both KEY=value and KEY: value for dotenv's value parser.
                token = dotenv_values(stream=StringIO(f"HF_TOKEN={match.group(1)}")).get("HF_TOKEN")
                if token:
                    return token
    return None


def _record_values(record) -> dict[str, list[str]]:
    """Map a project Record's data into aligned, cross-lingual attributes."""
    names = getattr(record, "names", None)
    if names is None:
        names = _split_values(
            getattr(record, "title", ""),
            getattr(record, "name_variants", ""),
            getattr(record, "wiki_title", ""),
        )
    else:
        names = _as_values(names)

    return {
        "name": names,
        "relation": _split_values(
            getattr(record, "country", ""),
            getattr(record, "capital", ""),
            getattr(record, "neighbours", ""),
            getattr(record, "population", ""),
        ),
        "classification": _split_values(
            getattr(record, "types", ""),
            getattr(record, "instance_of_label", ""),
        ),
        "description": _split_values(
            getattr(record, "details", ""),
            getattr(record, "described_by", ""),
            getattr(record, "description", ""),
            getattr(record, "text_snippets", ""),
        ),
    }


def _as_values(value) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in _VALUE_SEPARATOR.split(value) if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def _split_values(*values) -> list[str]:
    return [part for value in values for part in _as_values(value)]


def _phonetic_values(record) -> list[str]:
    return _split_values(getattr(record, "title_ipa", ""))


def _coordinates(record) -> list[tuple[float, float]]:
    latitudes = re.split(r"[;|]", str(getattr(record, "lat", "")))
    longitudes = re.split(r"[;|]", str(getattr(record, "lon", "")))
    coordinates = []
    for latitude, longitude in zip(latitudes, longitudes):
        try:
            lat, lon = float(latitude), float(longitude)
        except ValueError:
            continue
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            coordinates.append((lat, lon))
    return coordinates


def _temporal_range(record) -> Optional[tuple[float, float]]:
    for start_field, end_field in (("begin_date", "end_date"), ("inception", "dissolved")):
        try:
            start = float(getattr(record, start_field))
            end = float(getattr(record, end_field))
        except (AttributeError, TypeError, ValueError):
            continue
        if math.isfinite(start) and math.isfinite(end):
            return min(start, end), max(start, end)
    return None


class DeepERFeatureExtractor:
    """Build tuple representations and DeepER's per-attribute similarity vectors."""

    def __init__(self, model=None, batch_size: int = 256):
        if batch_size < 1:
            raise ValueError("batch_size must be a positive integer.")
        self._model = model
        self.batch_size = batch_size
        self._text_vectors: dict[tuple[str, ...], np.ndarray] = {}

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(MODEL_NAME, token=_hugging_face_token())
        return self._model

    def prepare_pairs(self, pairs) -> None:
        """Batch-encode unique attribute texts before feature generation."""
        keys_by_attribute: dict[str, set[tuple[str, ...]]] = {
            attribute: set() for attribute in TEXT_ATTRIBUTES
        }
        for pair in pairs:
            for record in (pair.query, *pair.candidates):
                values = _record_values(record)
                for attribute in TEXT_ATTRIBUTES:
                    key = tuple(values[attribute])
                    if key and key not in self._text_vectors:
                        keys_by_attribute[attribute].add(key)

        pending = {
            attribute: sorted(keys)
            for attribute, keys in keys_by_attribute.items()
            if keys
        }
        if not pending:
            return

        from tqdm.auto import tqdm

        model = self._get_model()
        for attribute, keys in pending.items():
            text_to_keys: dict[str, list[tuple[str, ...]]] = {}
            for key in keys:
                for text in key:
                    text_to_keys.setdefault(text, []).append(key)

            texts = list(text_to_keys)
            sums: dict[tuple[str, ...], np.ndarray] = {}
            for start in tqdm(
                range(0, len(texts), self.batch_size),
                desc=f"Encoding {attribute}",
                unit="batch",
            ):
                batch = texts[start:start + self.batch_size]
                embeddings = np.asarray(
                    model.encode(
                        batch,
                        normalize_embeddings=True,
                        convert_to_numpy=True,
                        show_progress_bar=False,
                        batch_size=self.batch_size,
                    ),
                    dtype=np.float32,
                )
                if embeddings.ndim == 1:
                    embeddings = embeddings.reshape(1, -1)
                for text, embedding in zip(batch, embeddings):
                    for key in text_to_keys[text]:
                        if key not in sums:
                            sums[key] = embedding.copy()
                        else:
                            sums[key] += embedding

            for key in keys:
                vector = sums[key] / len(key)
                norm = np.linalg.norm(vector)
                self._text_vectors[key] = vector / norm if norm else vector

    def _attribute_vector(self, values: list[str]) -> Optional[np.ndarray]:
        if not values:
            return None
        key = tuple(values)
        if key not in self._text_vectors:
            vectors = np.asarray(
                self._get_model().encode(
                    values,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                ),
                dtype=np.float32,
            )
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            vector = vectors.mean(axis=0)
            norm = np.linalg.norm(vector)
            self._text_vectors[key] = vector / norm if norm else vector
        return self._text_vectors[key]

    def encode_record(self, record) -> dict[str, object]:
        """Return one vector per populated text attribute plus domain values."""
        encoded: dict[str, object] = {}
        values = _record_values(record)
        for attribute in TEXT_ATTRIBUTES:
            vector = self._attribute_vector(values[attribute])
            if vector is not None:
                encoded[attribute] = vector

        phonetic = _phonetic_values(record)
        if phonetic:
            encoded["phonetic"] = phonetic

        coordinates = _coordinates(record)
        if coordinates:
            encoded["coordinates"] = coordinates

        temporal = _temporal_range(record)
        if temporal is not None:
            encoded["temporal"] = temporal
        return encoded

    def compare(self, record_a, record_b) -> list[float]:
        """Return aligned-attribute similarities and geographic/temporal features."""
        return compare_encoded(self.encode_record(record_a), self.encode_record(record_b))


def _haversine_km(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, point_a)
    lat2, lon2 = map(math.radians, point_b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(value)))


def _cosine(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if denominator == 0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denominator)


def _phonetic_similarity(values_a: list[str], values_b: list[str]) -> float:
    return max(
        (SequenceMatcher(None, value_a.casefold(), value_b.casefold()).ratio()
         for value_a in values_a for value_b in values_b),
        default=float("nan"),
    )


def compare_encoded(record_a: dict[str, object], record_b: dict[str, object]) -> list[float]:
    """Compare two encoded tuple representations using a fixed feature order."""
    features = [
        _cosine(record_a[attribute], record_b[attribute])
        if attribute in record_a and attribute in record_b
        else float("nan")
        for attribute in TEXT_ATTRIBUTES
    ]

    features.append(
        _phonetic_similarity(record_a.get("phonetic", []), record_b.get("phonetic", []))
    )

    coordinates_a = record_a.get("coordinates", [])
    coordinates_b = record_b.get("coordinates", [])
    features.append(
        min(
            (_haversine_km(point_a, point_b) for point_a in coordinates_a for point_b in coordinates_b),
            default=float("nan"),
        )
    )

    temporal_a = record_a.get("temporal")
    temporal_b = record_b.get("temporal")
    if temporal_a is not None and temporal_b is not None:
        low = max(temporal_a[0], temporal_b[0])
        high = min(temporal_a[1], temporal_b[1])
        features.extend((1.0 if low <= high else 0.0, max(0.0, low - high)))
    else:
        features.extend((float("nan"), float("nan")))
    return features


def compare_records(record_a, record_b, extractor: Optional[DeepERFeatureExtractor] = None) -> list[float]:
    """Create the DeepER pairwise similarity vector for project records."""
    return (extractor or get_default_extractor()).compare(record_a, record_b)


def get_default_extractor() -> DeepERFeatureExtractor:
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = DeepERFeatureExtractor()
    return _default_extractor


def training_data(pairs, extractor: Optional[DeepERFeatureExtractor] = None):
    """Flatten labelled project Pairs into classifier features and labels."""
    extractor = extractor or get_default_extractor()
    extractor.prepare_pairs(pairs)
    rows, labels = [], []
    for pair in pairs:
        if len(pair.candidates) != len(pair.labels):
            raise ValueError(
                f"Pair for query {pair.query.id!r} has {len(pair.candidates)} candidates "
                f"but {len(pair.labels)} labels."
            )
        for candidate, label in zip(pair.candidates, pair.labels):
            rows.append(extractor.compare(pair.query, candidate))
            labels.append(int(label))
    if not rows:
        raise ValueError("Training requires at least one labelled query-candidate pair.")
    return np.asarray(rows, dtype=np.float32), np.asarray(labels, dtype=np.int64)


def train_classifier(pairs, extractor: Optional[DeepERFeatureExtractor] = None, **parameters):
    """Train a balanced random-forest classifier from labeled training Pairs."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline

    features, labels = training_data(pairs, extractor)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("Training pairs must contain both match (1) and non-match (0) labels.")

    forest_parameters = {
        "n_estimators": 300,
        "min_samples_leaf": 2,
        "class_weight": "balanced_subsample",
        "random_state": 42,
        "n_jobs": -1,
        "verbose": 0,
    }
    forest_parameters.update(parameters)
    classifier = make_pipeline(
        SimpleImputer(
            strategy="constant",
            fill_value=0.0,
            add_indicator=True,
            keep_empty_features=True,
        ),
        RandomForestClassifier(**forest_parameters),
    )
    classifier.fit(features, labels)
    return classifier


def load_classifier(path):
    """Load a trained DeepER classifier and reject incompatible feature sets."""
    import joblib

    classifier = joblib.load(path)
    if getattr(classifier, "n_features_in_", None) != len(FEATURE_NAMES):
        raise ValueError(
            f"Classifier must expect {len(FEATURE_NAMES)} features in this order: "
            f"{', '.join(FEATURE_NAMES)}."
        )
    return classifier


def match_probability(classifier, record_a, record_b, extractor: Optional[DeepERFeatureExtractor] = None) -> float:
    """Return the trained model's probability that two project records match."""
    features = (extractor or get_default_extractor()).compare(record_a, record_b)
    return float(classifier.predict_proba(np.asarray([features], dtype=np.float32))[0, 1])


def is_match(classifier, record_a, record_b, threshold: float, extractor=None) -> dict:
    """Return a compatible match verdict and probability."""
    probability = match_probability(classifier, record_a, record_b, extractor)
    return {"match": probability >= threshold, "probability": probability}
