"""Derive a shared phonetic form and a Latin transliteration for any name.

None of the datasets provides IPA, so every IPA string here is derived:

- Arabic uses Epitran's `ara-Arab` map, then a small cleanup for what it leaves raw.
- Epitran has no Hebrew, Greek or Coptic map in the installed version, so those use
  the hand-written tables below. Latin uses a table too, because the names are
  scholarly transliterations (ḥ, ṣ, ǧ, ŧ) and Latinised Greek, not a modern language.
- Any other script (Syriac, Cyrillic, ...) goes through AnyAscii, then the Latin table.

The output is broad IPA built for cross-script comparison, not narrow transcription.
`shared_form` removes length and pharyngealisation, because vocalised Latin and
unvocalised Semitic spellings do not mark them consistently. Unvocalised scripts stay
unvocalised: the G2P cannot restore vowels the spelling omits.
"""

from __future__ import annotations

import re
import unicodedata
from functools import cache, lru_cache

from anyascii import anyascii

SCRIPT_RANGES = [
    ("Hebr", (0x0590, 0x05FF), (0xFB1D, 0xFB4F)),
    (
        "Arab",
        (0x0600, 0x06FF),
        (0x0750, 0x077F),
        (0x08A0, 0x08FF),
        (0xFB50, 0xFDFF),
        (0xFE70, 0xFEFF),
    ),
    ("Grek", (0x0370, 0x03FF), (0x1F00, 0x1FFF)),
    ("Copt", (0x2C80, 0x2CFF)),
    ("Syrc", (0x0700, 0x074F)),
    ("Cyrl", (0x0400, 0x052F)),
    ("Armn", (0x0530, 0x058F)),
    ("Geor", (0x10A0, 0x10FF)),
    ("Xsux", (0x12000, 0x123FF)),
]
# Coptic's own letters sit inside the Greek and Coptic block.
COPTIC_IN_GREEK_BLOCK = range(0x03E2, 0x03F0)


def detect_script(text: str) -> str:
    """Return the ISO 15924 code of the most frequent script among the letters."""
    counts: dict[str, int] = {}
    for char in text:
        if not (char.isalpha() or unicodedata.category(char) == "Mn"):
            continue
        cp = ord(char)
        script = (
            "Latn"
            if cp < 0x0370 or 0x1E00 <= cp <= 0x1EFF or 0xA720 <= cp <= 0xA7FF
            else "Zzzz"
        )
        if cp in COPTIC_IN_GREEK_BLOCK:
            script = "Copt"
        else:
            for code, *ranges in SCRIPT_RANGES:
                if any(lo <= cp <= hi for lo, hi in ranges):
                    script = code
                    break
        if unicodedata.category(char) != "Mn":
            counts[script] = counts.get(script, 0) + 1
    return max(sorted(counts), key=counts.__getitem__) if counts else "Zzzz"


def _apply_rules(text: str, rules: dict[str, str]) -> str:
    pattern = _compiled(tuple(sorted(rules, key=len, reverse=True)))
    return pattern.sub(lambda m: rules[m.group(0)], text)


@cache
def _compiled(keys: tuple[str, ...]) -> re.Pattern:
    return re.compile("|".join(re.escape(k) for k in keys))


HEBREW_NIQQUD = re.compile("[֑-ׇ]")
GERESH = "'׳’"
HEBREW_FINALS = str.maketrans("ךםןףץ", "כמנפצ")
HEBREW_GERESH = {
    "ג": "dʒ",
    "ז": "ʒ",
    "צ": "tʃ",
    "ד": "ð",
    "ת": "θ",
    "ח": "x",
    "ט": "ðˤ",
    "ע": "ɣ",
    "ר": "ɣ",
    "צ׳": "tʃ",
}
HEBREW_LETTERS = {
    "א": "a",
    "ב": "b",
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ז": "z",
    "ח": "ħ",
    "ט": "tˤ",
    "כ": "k",
    "ל": "l",
    "מ": "m",
    "נ": "n",
    "ס": "s",
    "ע": "ʕ",
    "פ": "f",
    "צ": "sˤ",
    "ק": "q",
    "ר": "r",
    "ש": "ʃ",
    "ת": "t",
}


def hebrew_to_ipa(text: str) -> str:
    text = HEBREW_NIQQUD.sub("", text.replace("׳", "'")).translate(HEBREW_FINALS)
    words = []
    for word in text.split():
        out: list[str] = []
        i = 0
        letters = word
        while i < len(letters):
            char = letters[i]
            following = letters[i + 1] if i + 1 < len(letters) else ""
            is_initial = not out
            if char in GERESH:
                i += 1
                continue
            if following and following in GERESH and char in HEBREW_GERESH:
                out.append(HEBREW_GERESH[char])
                i += 2
                continue
            if char == "ו":
                double = following == "ו"
                out.append("w" if is_initial or double else "u")
                i += 2 if double else 1
                continue
            if char == "י":
                double = following == "י"
                out.append("j" if is_initial or double else "i")
                i += 2 if double else 1
                continue
            if char == "ה" and i == len(letters) - 1 and not is_initial:
                out.append("a")
            elif char == "א" and is_initial:
                out.append("ʔa")
            else:
                out.append(HEBREW_LETTERS.get(char, ""))
            i += 1
        words.append("".join(out))
    return " ".join(w for w in words if w)


ARABIC_DIACRITICS = re.compile("[ً-ْٰـ]")
ARABIC_PRE = str.maketrans({"ک": "ك", "ی": "ي", "ى": "ا", "ئ": "ء", "ؤ": "ء", "ء": "ء"})
ARABIC_LEFTOVERS = {
    "ة": "a",
    "ء": "ʔ",
    "پ": "p",
    "چ": "tʃ",
    "ژ": "ʒ",
    "گ": "g",
    "ڤ": "v",
    "ھ": "h",
    "ہ": "h",
}


@lru_cache(maxsize=1)
def _epitran_arabic():
    import epitran

    return epitran.Epitran("ara-Arab")


def arabic_to_ipa(text: str) -> str:
    text = ARABIC_DIACRITICS.sub("", text.translate(ARABIC_PRE))
    words = []
    for word in text.split():
        ipa = _epitran_arabic().transliterate(word)
        ipa = _apply_rules(ipa, ARABIC_LEFTOVERS)
        # Epitran maps و and ي to long vowels. Word-initially they are consonants.
        if ipa.startswith("uː"):
            ipa = "w" + ipa[2:]
        elif ipa.startswith("iː"):
            ipa = "j" + ipa[2:]
        words.append(ipa)
    return " ".join(w for w in words if w)


GREEK_DIGRAPHS = {
    "ου": "u",
    "αι": "e",
    "ει": "i",
    "οι": "i",
    "υι": "i",
    "αυ": "av",
    "ευ": "ev",
    "ηυ": "iv",
    "γγ": "ng",
    "γκ": "nk",
    "γχ": "nx",
    "γξ": "nks",
}
GREEK_LETTERS = {
    "α": "a",
    "β": "b",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "e",
    "θ": "θ",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "ks",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "ς": "s",
    "ϲ": "s",
    "τ": "t",
    "υ": "i",
    "φ": "f",
    "χ": "x",
    "ψ": "ps",
    "ω": "o",
    "ϝ": "w",
}
ROUGH_BREATHING = "̔"
COPTIC_LETTERS = {
    **GREEK_LETTERS,
    "ϣ": "ʃ",
    "ϥ": "f",
    "ϧ": "x",
    "ϩ": "h",
    "ϫ": "dʒ",
    "ϭ": "tʃ",
    "ϯ": "ti",
    "ϧ̀": "x",
}


def greek_to_ipa(text: str) -> str:
    words = []
    for word in unicodedata.normalize("NFD", text.lower()).split():
        rough = word[:3].find(ROUGH_BREATHING) >= 0 and not word.startswith("ρ")
        letters = "".join(c for c in word if unicodedata.category(c) != "Mn")
        ipa = _apply_rules(letters, {**GREEK_DIGRAPHS, **GREEK_LETTERS})
        words.append(("h" if rough else "") + ipa)
    return " ".join(w for w in words if w)


def coptic_to_ipa(text: str) -> str:
    folded = text.translate(COPTIC_FOLD)
    letters = "".join(
        c
        for c in unicodedata.normalize("NFD", folded.lower())
        if unicodedata.category(c) != "Mn"
    )
    return _apply_rules(letters, {**GREEK_DIGRAPHS, **COPTIC_LETTERS})


# Coptic letters that share a shape and a sound with Greek ones.
COPTIC_FOLD = str.maketrans(
    {chr(0x2C81 + 2 * i): g for i, g in enumerate("αβγδε")}
    | {
        "ⲋ": "",
        "ⲍ": "ζ",
        "ⲏ": "η",
        "ⲑ": "θ",
        "ⲓ": "ι",
        "ⲕ": "κ",
        "ⲗ": "λ",
        "ⲙ": "μ",
        "ⲛ": "ν",
        "ⲝ": "ξ",
        "ⲟ": "ο",
        "ⲡ": "π",
        "ⲣ": "ρ",
        "ⲥ": "σ",
        "ⲧ": "τ",
        "ⲩ": "υ",
        "ⲫ": "φ",
        "ⲭ": "χ",
        "ⲯ": "ψ",
        "ⲱ": "ω",
        "ϣ": "ϣ",
        "ϥ": "ϥ",
        "ϧ": "ϧ",
        "ϩ": "ϩ",
        "ϫ": "ϫ",
        "ϭ": "ϭ",
        "ϯ": "ϯ",
    }
)

# Scholarly transliteration marks. Keys are matched before accents are stripped. The
# Greek chi is a placeholder for /x/: a plain "x" would be re-read as Latin /ks/ later.
LATIN_SPECIAL = {
    "ḫ": "χ",
    "ẖ": "χ",
    "ḥ": "ħ",
    "ṣ": "sˤ",
    "ṭ": "tˤ",
    "ḍ": "dˤ",
    "ẓ": "ðˤ",
    "ḏ": "ð",
    "ṯ": "θ",
    "š": "ʃ",
    "ş": "ʃ",
    "ǧ": "dʒ",
    "ğ": "ɣ",
    "ġ": "ɣ",
    "ḡ": "ɣ",
    "ž": "ʒ",
    "č": "tʃ",
    "ç": "tʃ",
    "ŧ": "",
    "ʿ": "ʕ",
    "ʕ": "ʕ",
    "ʾ": "ʔ",
    "ʼ": "ʔ",
    "ꜥ": "ʕ",
    "ꜣ": "a",
    "ı": "i",
    "ß": "s",
    "ø": "o",
    "æ": "e",
    "œ": "e",
    "þ": "θ",
    "ð": "ð",
}
LATIN_DIGRAPHS = {
    "kh": "x",
    "sh": "ʃ",
    "ch": "x",
    "th": "θ",
    "ph": "f",
    "gh": "ɣ",
    "dh": "ð",
    "qu": "kw",
    "ae": "e",
    "oe": "e",
    "ou": "u",
    "tsh": "tʃ",
    "dj": "dʒ",
    "gu": "gu",
    "tz": "ts",
    "χ": "x",
}
LATIN_LETTERS = {
    "a": "a",
    "b": "b",
    "c": "k",
    "d": "d",
    "e": "e",
    "f": "f",
    "g": "g",
    "h": "h",
    "i": "i",
    "j": "dʒ",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "o": "o",
    "p": "p",
    "q": "q",
    "r": "r",
    "s": "s",
    "t": "t",
    "u": "u",
    "v": "v",
    "w": "w",
    "x": "ks",
    "y": "i",
    "z": "z",
}
LATIN_RULES = {**LATIN_DIGRAPHS, **LATIN_LETTERS}
APOSTROPHES = re.compile("['‘’`´]")
NON_LATIN_LETTER = re.compile(r"[^a-z ]")


def latin_to_ipa(text: str) -> str:
    lowered = unicodedata.normalize("NFC", text).lower()
    marked = _apply_rules(lowered, LATIN_SPECIAL)
    plain = "".join(
        c
        for c in unicodedata.normalize("NFD", marked)
        if unicodedata.category(c) != "Mn"
    )
    plain = APOSTROPHES.sub("", plain).replace("-", " ")
    return _apply_rules(plain, LATIN_RULES)


SHARED_DROP = re.compile("[ːˤ͡ʲ.]")
NOT_IPA = re.compile(r"[^a-zʔʕħθðʃʒɣŋ ]")
MULTI_SPACE = re.compile(r"\s+")


def shared_form(ipa: str) -> str:
    """Reduce IPA to the form every script can agree on."""
    stripped = SHARED_DROP.sub("", ipa.lower())
    return MULTI_SPACE.sub(" ", NOT_IPA.sub("", stripped)).strip()


def to_ipa(name: str, script: str | None = None) -> tuple[str, str]:
    """Return (shared IPA form, method used)."""
    script = script or detect_script(name)
    if script == "Arab":
        return shared_form(arabic_to_ipa(name)), "epitran"
    if script == "Hebr":
        return shared_form(hebrew_to_ipa(name)), "rules"
    if script == "Grek":
        return shared_form(greek_to_ipa(name)), "rules"
    if script == "Copt":
        return shared_form(coptic_to_ipa(name)), "rules"
    if script == "Latn":
        return shared_form(latin_to_ipa(name)), "rules"
    return shared_form(latin_to_ipa(anyascii(name))), "anyascii"


@cache
def phonetic_forms(name: str) -> tuple[str, str, str, str]:
    """Return (script, ipa, ipa_method, transliteration) for one name."""
    script = detect_script(name)
    ipa, method = to_ipa(name, script)
    translit = NON_LATIN_LETTER.sub("", anyascii(name).lower().replace("-", " "))
    return script, ipa, method, MULTI_SPACE.sub(" ", translit).strip()
