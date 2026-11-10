"""Shared helpers: text normalisation, record serialisation, block -> pairs, evaluation."""
import re
import unicodedata
from itertools import product


def normalize(s) -> str:
    """Casefold, strip diacritics / Hebrew niqqud / Arabic harakat / tatweel, drop punctuation."""
    s = unicodedata.normalize("NFKC", str(s)).casefold().replace("\u0640", "")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def flatten(value):
    """Yield every leaf value of a nested dict/list as a string (semi-structured -> flat)."""
    if value is None:
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from flatten(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from flatten(v)
    else:
        yield str(value)


def serialize(record: dict, attrs=None, with_names=False, norm=True) -> str:
    """Turn one record into one string.
    norm=True       -> normalised text (for the string-based blockers)
    with_names=True -> 'name: Konstantinopel ; country: Turkey' (nicer input for LM encoders)
    """
    keys = attrs or [k for k in record if k != "id"]
    parts = []
    for k in keys:
        vals = [normalize(v) if norm else v for v in flatten(record.get(k))]
        vals = [v for v in vals if v]
        if vals:
            parts.append(f"{k}: {' '.join(vals)}" if with_names else " ".join(vals))
    return " ; ".join(parts) if with_names else " ".join(parts)


def blocks_to_pairs(blocks) -> set:
    """blocks = {key: (ids_from_A, ids_from_B)} -> set of (id_a, id_b) candidate pairs."""
    pairs = set()
    for ids_a, ids_b in blocks.values():
        pairs.update(product(ids_a, ids_b))
    return pairs


def evaluate(candidates, gold, n_a, n_b) -> dict:
    """Pair Completeness (recall), Pairs Quality (precision), Reduction Ratio."""
    cand, gold = set(candidates), set(gold)
    tp = len(cand & gold)
    return {
        "PC": tp / len(gold) if gold else 0.0,
        "PQ": tp / len(cand) if cand else 0.0,
        "RR": 1 - len(cand) / (n_a * n_b) if n_a * n_b else 0.0,
        "candidates": len(cand),
    }


def explode_names(records, attrs) -> dict:
    """One entry per name VARIANT: {(record_id, n): normalised_variant}. Edit-distance and q-gram
    methods should compare variants one by one, not one long concatenated string per record."""
    out = {}
    for r in records:
        variants = [normalize(v) for k in attrs for v in flatten(r.get(k))]
        for n, v in enumerate(v for v in variants if v):
            out[(r["id"], n)] = v
    return out


def collapse(pairs) -> set:
    """Map variant-level pairs ((id_a, n), (id_b, m)) back to record-level pairs (id_a, id_b)."""
    return {(a[0], b[0]) for a, b in pairs}
