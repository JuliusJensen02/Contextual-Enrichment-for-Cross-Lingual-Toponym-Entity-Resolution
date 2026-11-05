"""Linguistically motivated blocking, reimplemented after the MEHDIE description.

A block is all records with a name containing a letter of one class of similar-sounding
consonants. Only the B/P/F example comes from the task description. The other classes
are our own, grouped by articulation, and have not been checked against Sagi et al.
(2025), whose text could not be retrieved.
"""

from __future__ import annotations

import numpy as np
from rapidfuzz.distance import Jaro
from rapidfuzz.process import cdist

from candidate_generation.data.schema import NameTable
from candidate_generation.generators.base import Generator, StringGroups, group_max

# Consonant classes over the shared IPA form.
IPA_CLASSES: dict[str, tuple[str, ...]] = {
    "labial": ("p", "b", "f", "v", "β", "ɸ"),  # the B/P/F class
    "nasal": ("m", "n", "ŋ"),
    "dental": ("t", "d", "θ", "ð"),
    "sibilant": ("s", "z", "ʃ", "ʒ", "dʒ", "tʃ", "ts"),
    "velar": ("k", "g", "q", "x", "ɣ", "χ"),
    "guttural": ("ʔ", "h", "ħ", "ʕ"),
    "liquid": ("l", "r"),
    "glide": ("w", "j"),
}
CLASS_BIT = {name: 1 << i for i, name in enumerate(IPA_CLASSES)}
_AFFRICATES = tuple(
    s for members in IPA_CLASSES.values() for s in members if len(s) > 1
)
_SEGMENT_BITS = {
    seg: CLASS_BIT[name] for name, members in IPA_CLASSES.items() for seg in members
}

# Fallback for names with no IPA form.
LETTER_CLASSES: dict[str, str] = {
    **dict.fromkeys("בפףו", "labial"),
    **dict.fromkeys("מםנן", "nasal"),
    **dict.fromkeys("דטת", "dental"),
    **dict.fromkeys("זסצץש", "sibilant"),
    **dict.fromkeys("גכךק", "velar"),
    **dict.fromkeys("אהחע", "guttural"),
    **dict.fromkeys("לר", "liquid"),
    "י": "glide",
    **dict.fromkeys("بفپڤ", "labial"),
    **dict.fromkeys("من", "nasal"),
    **dict.fromkeys("تطدضثذظ", "dental"),
    **dict.fromkeys("سصزشجژچ", "sibilant"),
    **dict.fromkeys("كقخغگ", "velar"),
    **dict.fromkeys("ءأإآهحع", "guttural"),
    **dict.fromkeys("لر", "liquid"),
    **dict.fromkeys("وي", "glide"),
    **dict.fromkeys("bpfv", "labial"),
    **dict.fromkeys("mn", "nasal"),
    **dict.fromkeys("td", "dental"),
    **dict.fromkeys("szc", "sibilant"),
    **dict.fromkeys("kgqx", "velar"),
    "h": "guttural",
    **dict.fromkeys("lr", "liquid"),
    **dict.fromkeys("wjy", "glide"),
}

_POPCOUNT = np.array([i.bit_count() for i in range(1 << 16)], dtype=np.uint8)
# Jaro only breaks ties between candidates sharing the same number of blocks.
_JARO_WEIGHT = 0.999


def blocks_of_ipa(ipa: str) -> int:
    """Return the class bitmask of one IPA string."""
    mask = 0
    i = 0
    while i < len(ipa):
        pair = ipa[i : i + 2]
        if pair in _AFFRICATES:
            mask |= _SEGMENT_BITS[pair]
            i += 2
            continue
        mask |= _SEGMENT_BITS.get(ipa[i], 0)
        i += 1
    return mask


def blocks_of_letters(name: str) -> int:
    """Fallback bitmask over Hebrew, Arabic and Latin letters."""
    mask = 0
    for char in name.lower():
        block = LETTER_CLASSES.get(char)
        if block:
            mask |= CLASS_BIT[block]
    return mask


def record_blocks(names: tuple[str, ...], ipa: tuple[str, ...]) -> int:
    """Union the blocks of all of a record's names, using letters where IPA is missing."""
    mask = 0
    for name, form in zip(names, ipa):
        mask |= blocks_of_ipa(form) if form else blocks_of_letters(name)
    return mask


class MehdieBpf(Generator):
    """Set-based blocking. Ranked by shared block count, then Jaro similarity."""

    name = "mehdie_bpf"
    input_fields = frozenset({"name", "name_variants", "ipa"})

    def __init__(self, representation: str = "ipa"):
        self.representation = representation

    def _prepare(self, query: NameTable, target: NameTable) -> None:
        self.query_masks = np.array(
            [record_blocks(n, i) for n, i in zip(query.names, query.ipa)],
            dtype=np.uint16,
        )
        self.target_masks = np.array(
            [record_blocks(n, i) for n, i in zip(target.names, target.ipa)],
            dtype=np.uint16,
        )
        self.query_strings = StringGroups(query.representation(self.representation))
        self.target_strings = StringGroups(target.representation(self.representation))

    def score(self, query_indices: np.ndarray) -> np.ndarray:
        shared = _POPCOUNT[
            np.bitwise_and.outer(self.query_masks[query_indices], self.target_masks)
        ]
        positions, offsets = self.query_strings.chunk(query_indices)
        strings = [self.query_strings.flat[p] for p in positions]
        jaro = cdist(
            strings,
            self.target_strings.flat,
            scorer=Jaro.similarity,
            workers=1,
            dtype=np.float32,
        )
        jaro = group_max(jaro, offsets, self.target_strings.offsets[:-1])
        scores = shared.astype(np.float32) + _JARO_WEIGHT * jaro
        scores[shared == 0] = np.nan
        return scores

    def metadata(self) -> dict:
        return {
            **super().metadata(),
            "classes": {k: list(v) for k, v in IPA_CLASSES.items()},
        }
