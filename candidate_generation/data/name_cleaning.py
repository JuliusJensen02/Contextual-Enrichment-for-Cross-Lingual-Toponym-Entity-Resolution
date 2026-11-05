"""Turn source name fields into clean name strings.

The important job here is keeping attributes out of names. Pleiades titles embed
feature types ("Aethusa (island)") and locations ("Temple X (Rome)"). If those reach
a generator, blocking uses feature type through the back door, which is exactly what
the ablation design forbids. Names that only exist as a placeholder ("Untitled",
"Unnamed villa") are dropped for the same reason: their text is a type label.
"""

from __future__ import annotations

import re
import unicodedata

PLACEHOLDER = re.compile(r"^\s*(untitled|unnamed)\b", re.IGNORECASE)
PAREN = re.compile(r"\(([^()]*)\)")
ORTHOGRAPHIC_MAX_LEN = 4
LACUNA_BRACKET = re.compile(r"\[[^\]]*\]")
EMPTY_PAREN = re.compile(r"\(\s*\)")
MULTI_SPACE = re.compile(r"\s+")
LETTER = re.compile(r"[^\W\d_]")
# Editorial marks: restored letters are part of the name, the brackets are not.
EDITORIAL_MARKS = re.compile(r"[\[\]()*]")
# A single surviving letter is an abbreviation or a fragment, not a name.
MIN_LETTERS = 2


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").strip()


def tidy(text: str) -> str:
    """Collapse whitespace and drop the uncertainty marks and stray edge punctuation."""
    text = EDITORIAL_MARKS.sub("", nfc(text).replace("?", " "))
    text = MULTI_SPACE.sub(" ", text).strip(" .,;:-|/")
    return text if len(LETTER.findall(text)) >= MIN_LETTERS else ""


def uniq(items) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        if item:
            seen.setdefault(item, None)
    return list(seen)


def expand_parentheses(text: str) -> list[str]:
    """Resolve parentheses in one name, returning its surviving forms.

    Parentheses attached to a word are spelling alternatives: `Ap(p)enninus` gives
    both spellings, and so does `Ida(ion) M.`. A free-standing parenthesis is a
    comment on the place, usually its type or region, so it is removed whatever it
    says. That loses a few alternative names, which is the safe direction here.
    """
    forms = [text]
    for _ in range(4):
        expanded: list[str] = []
        changed = False
        for form in forms:
            match = PAREN.search(form)
            if not match:
                expanded.append(form)
                continue
            changed = True
            inner = match.group(1)
            before = form[: match.start()]
            after = form[match.end() :]
            attached = (
                before[-1:].isalpha() or after[:1].isalpha()
            ) and inner.isalpha()
            if attached and len(inner) <= ORTHOGRAPHIC_MAX_LEN:
                expanded.append(before + inner + after)
            expanded.append(before + after)
        forms = expanded
        if not changed:
            break
    return uniq(tidy(PAREN.sub(" ", form)) for form in forms)


def clean_pleiades_name(raw: str) -> list[str]:
    """Clean one Pleiades title or name. Returns [] for placeholders."""
    if PLACEHOLDER.search(raw or ""):
        return []
    forms: list[str] = []
    for part in nfc(raw).split("/"):
        forms.extend(expand_parentheses(part))
    return uniq(forms)


def clean_tm_name(raw: str) -> list[str]:
    """Clean one Trismegistos name: drop lacunae and bracketed location qualifiers."""
    text = LACUNA_BRACKET.sub(" ", nfc(raw))
    text = EMPTY_PAREN.sub(" ", text)
    forms: list[str] = []
    for part in text.split("/"):
        forms.extend(expand_parentheses(part))
    return uniq(forms)


def clean_egyptian_name(raw: str) -> list[str]:
    """Egyptological forms write alternatives in parentheses: `Smn (Sw-mn)`.

    One entry can also hold a list inside parentheses, `A (B | C)`, which the caller's
    split on " | " leaves as the unbalanced fragments `A (B` and `C)`.
    """
    return uniq(tidy(part) for part in re.split(r"[()]", nfc(raw)))


def split_multi(raw: str, separator: str = " | ") -> list[str]:
    return [part.strip() for part in (raw or "").split(separator) if part.strip()]


def split_variants(raw: str, separators: str) -> list[str]:
    """Split a variant list on any of the given single-character separators."""
    return uniq(
        tidy(part) for part in re.split(f"[{re.escape(separators)}]", raw or "")
    )
