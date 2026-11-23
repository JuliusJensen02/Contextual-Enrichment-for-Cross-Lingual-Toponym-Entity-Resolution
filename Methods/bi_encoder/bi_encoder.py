"""
Bi-encoder baseline: LaBSE per-attribute encoding -> attribute-wise comparison -> XGBoost.
"""
import math

import numpy as np
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier

MODEL_NAME = "sentence-transformers/LaBSE"
_model = None


def get_model():
    """Load LaBSE the first time it is needed, not when this file is imported."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

# Attributes that get encoded with LaBSE. Coordinates and temporal are NOT encoded.
TEXT_ATTRIBUTES = ["name", "name_variants", "ipa", "relational_geography", "classification", "description"]

FEATURE_NAMES = [f"{a}_cos" for a in TEXT_ATTRIBUTES] + ["geo_km", "temporal_overlap", "temporal_gap_years"]


def is_missing(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def as_list(x):
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    if isinstance(x, (list, tuple)):
        return [s.strip() for s in x if isinstance(s, str) and s.strip()]
    return []  # None, NaN or any other non-text value


def encode_entity(e):
    """Return {attribute: encoding}. Missing attributes are simply left out."""
    enc = {}
    for attr in TEXT_ATTRIBUTES:
        texts = as_list(e.get(attr))
        if texts:
            enc[attr] = get_model().encode(texts, normalize_embeddings=True) 

    coords = e.get("coordinates")
    if isinstance(coords, dict) and not is_missing(coords.get("lat")) and not is_missing(coords.get("lon")):
        enc["coordinates"] = (float(coords["lat"]), float(coords["lon"]))

    t = e.get("temporal")
    if isinstance(t, dict) and not is_missing(t.get("start")) and not is_missing(t.get("end")):
        start, end = float(t["start"]), float(t["end"])
        enc["temporal"] = (min(start, end), max(start, end))
    return enc


_cache = {}

def encode_cached(entity):
    if entity["id"] not in _cache:
        _cache[entity["id"]] = encode_entity(entity)
    return _cache[entity["id"]]


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(a)))


def compare(a, b):
    """Feature vector for two encoded entities. NaN when an attribute is missing on either side."""
    features = []
    for attr in TEXT_ATTRIBUTES:
        if attr in a and attr in b:
            features.append(float((a[attr] @ b[attr].T).max()))  # NumPy matrix multiplication: best cosine over all string pairs
        else:
            features.append(np.nan)

    if "coordinates" in a and "coordinates" in b:
        features.append(haversine_km(*a["coordinates"], *b["coordinates"]))
    else:
        features.append(np.nan)

    if "temporal" in a and "temporal" in b:
        low = max(a["temporal"][0], b["temporal"][0])
        high = min(a["temporal"][1], b["temporal"][1])
        features.append(1.0 if low <= high else 0.0)
        features.append(max(0.0, low - high))
    else:
        features.extend([np.nan, np.nan])
    return features


def load_classifier(path):
    clf = XGBClassifier()
    clf.load_model(path)
    n_model = clf.get_booster().num_features()
    if n_model != len(FEATURE_NAMES):
        raise ValueError(
            f"Model expects {n_model} features but this file produces {len(FEATURE_NAMES)}. "
            "The model was trained with a different feature set."
        )
    return clf


def match_probability(clf, entity_a, entity_b):
    x = np.array([compare(encode_cached(entity_a), encode_cached(entity_b))], dtype=np.float32)
    return float(clf.predict_proba(x)[0, 1])


def is_match(clf, entity_a, entity_b, threshold):
    p = match_probability(clf, entity_a, entity_b)
    return {"match": p >= threshold, "probability": p}


def classify_pairs(clf, pairs, entities, threshold, cache=None):
    """Verdict for many pairs. pairs: [{"left_id", "right_id"}], entities: {id: entity dict}.
    Each entity is encoded once, however many pairs it appears in."""
    cache = {} if cache is None else cache
    rows = []
    for p in pairs:
        for eid in (p["left_id"], p["right_id"]):
            if eid not in cache:
                cache[eid] = encode_entity(entities[eid])
        rows.append(compare(cache[p["left_id"]], cache[p["right_id"]]))
    probs = clf.predict_proba(np.array(rows, dtype=np.float32))[:, 1]
    return [{"left_id": p["left_id"], "right_id": p["right_id"],
             "probability": float(pr), "match": bool(pr >= threshold)} for p, pr in zip(pairs, probs)]