"""Phonetic encodings for the SAMPLED test-set records (a stand-in until the project's own
phonetic encoding of all toponyms is ready).

Encoding: a cross-script consonant skeleton. Hebrew and Arabic are usually written without
vowels, so vowels (and the glides y/w) are dropped in every script, and each consonant is mapped
to one of eight broad sound classes shared by all scripts:

  b  labials        b p f v              ב פ   ب ف   б п ф в   β π φ
  m  m                                   מ     م     м         μ
  n  n, ng                               נ     ن     н         ν
  l  liquids        l r                  ל ר   ل ر   л р       λ ρ
  t  dentals        t d th dh            ד ט ת  ت ث د ذ ض ط ظ   т д   τ δ θ
  k  velars         k g q c              ג כ ק  ق ك   к г       κ γ
  h  h-like         h kh                 ה ח   ه ح خ  х         χ
  s  sibilants      s z sh zh ch j ts    ז ס צ ש  ج ز س ش ص  с з ш щ ж ц ч   σ ζ

Chinese characters go through pinyin first (pypinyin), with pinyin's own rules: j q x z c s zh
ch sh r are sibilants (as in Russian Palladius transcription), h is "h", y/w are glides.
Articles (Arabic al-, Latin al-/el-) and word-final Hebrew he / Arabic ta marbuta are dropped,
repeated classes are collapsed ("Missisa" -> "mss" -> "ms"), and words are joined.
Examples: Antakya -> ntk, Baghdad / בגדד / بغداد -> bt / bkt / bt, 晋 / Цзинь -> sn / sn.

  python make_phonetic_samples.py      # writes phonetic_samples/<testset>.tsv (name -> phonetic)
"""
import random
import re
import sys
import unicodedata
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "phonetic_samples"

# ---------------------------------------------------------------- per-script letter -> class
HEBREW = {**dict.fromkeys("בפף", "b"), **dict.fromkeys("מם", "m"), **dict.fromkeys("נן", "n"),
          **dict.fromkeys("לר", "l"), **dict.fromkeys("דטת", "t"), **dict.fromkeys("גכךק", "k"),
          **dict.fromkeys("הח", "h"), **dict.fromkeys("זסצץש", "s"), **dict.fromkeys("אעוי", "")}
ARABIC = {**dict.fromkeys("بفپڤ", "b"), "م": "m", "ن": "n", **dict.fromkeys("لر", "l"),
          **dict.fromkeys("تثدذضطظ", "t"), **dict.fromkeys("قكگ", "k"), **dict.fromkeys("هحخ", "h"),
          **dict.fromkeys("جزسشصچ", "s"), **dict.fromkeys("اأإآءؤئىعغةوي", "")}
CYRILLIC = {**dict.fromkeys("бпфв", "b"), "м": "m", "н": "n", **dict.fromkeys("лр", "l"),
            **dict.fromkeys("тд", "t"), **dict.fromkeys("кг", "k"), "х": "h",
            **dict.fromkeys("сзшщжцч", "s"), **dict.fromkeys("аеёиоуыэюяйьъ", "")}
GREEK = {**dict.fromkeys("βπφ", "b"), "μ": "m", "ν": "n", **dict.fromkeys("λρ", "l"),
         **dict.fromkeys("τδθ", "t"), **dict.fromkeys("κγ", "k"), "χ": "h", "ξ": "ks", "ψ": "bs",
         **dict.fromkeys("σςζ", "s"), **dict.fromkeys("αεηιουω", "")}
LATIN = {**dict.fromkeys("bpfv", "b"), "m": "m", "n": "n", **dict.fromkeys("lr", "l"),
         **dict.fromkeys("td", "t"), **dict.fromkeys("kgqc", "k"), "h": "h", "x": "ks",
         **dict.fromkeys("szj", "s"), **dict.fromkeys("aeiouyw", "")}
LATIN_DIGRAPHS = [("sch", "s"), ("ph", "b"), ("th", "t"), ("dh", "t"), ("kh", "h"), ("gh", ""),
                  ("ch", "s"), ("sh", "s"), ("zh", "s"), ("ts", "s"), ("tz", "s"), ("dj", "s"), ("ck", "k")]
LATIN_SPECIAL = {"š": "sh", "ž": "zh", "č": "ch", "ǧ": "j", "ğ": "", "ḏ": "dh", "ṯ": "th", "ḫ": "kh",
                 "ç": "s", "ş": "sh", "ß": "s", "ŧ": "", "ʿ": "", "ʾ": "", "'": "", "’": "", "ʻ": ""}

PINYIN_INITIALS = [("zh", "s"), ("ch", "s"), ("sh", "s"), ("b", "b"), ("p", "b"), ("f", "b"),
                   ("m", "m"), ("n", "n"), ("l", "l"), ("d", "t"), ("t", "t"), ("g", "k"), ("k", "k"),
                   ("h", "h"), ("j", "s"), ("q", "s"), ("x", "s"), ("z", "s"), ("c", "s"), ("s", "s"),
                   ("r", "s"), ("y", ""), ("w", "")]


def _pinyin_syllable(syl: str) -> str:
    if syl == "er":  # 尔 transcribes a foreign r/l (阿尔泰 = Altai)
        return "l"
    code = ""
    for initial, cls in PINYIN_INITIALS:
        if syl.startswith(initial):
            code, syl = cls, syl[len(initial):]
            break
    return code + ("n" if syl.endswith(("n", "ng")) else "")  # finals: only -n / -ng are consonants


def _script(ch: str) -> str:
    name = unicodedata.name(ch, "")
    for script in ("CJK", "HEBREW", "ARABIC", "CYRILLIC", "GREEK", "LATIN"):
        if name.startswith(script):
            return script
    return ""


def encode_word(word: str) -> str:
    if any(_script(c) == "CJK" for c in word):
        from pypinyin import lazy_pinyin
        out = []
        for s in lazy_pinyin(word):
            if s.isascii() and s.isalpha():
                out.append(_pinyin_syllable(s))
            elif not any(_script(c) == "CJK" for c in s):  # non-Chinese text mixed in
                out.append(encode_word(s))
            # else: a character pypinyin has no reading for -> skipped
        return "".join(out)
    word = re.sub(r"^(ال|al-|el-)", "", word) if len(word) > 3 else word  # articles
    word = re.sub(r"[הةه]$", "", word) if len(word) > 2 else word         # final he / ta marbuta
    word = re.sub("ג['׳]", "ז", word)  # Hebrew ג׳ = j (a sibilant); other geresh letters keep their class
    for src, dst in LATIN_SPECIAL.items():
        word = word.replace(src, dst)
    word = "".join(c for c in unicodedata.normalize("NFD", word) if not unicodedata.combining(c))  # accents
    for src, dst in LATIN_DIGRAPHS:
        word = word.replace(src, dst)
    tables = {"HEBREW": HEBREW, "ARABIC": ARABIC, "CYRILLIC": CYRILLIC, "GREEK": GREEK, "LATIN": LATIN}
    return "".join(tables.get(_script(c), {}).get(c, "") for c in word)


def encode(name: str) -> str:
    """Phonetic encoding of one toponym name (see module docstring)."""
    words = re.split(r"[\s\-‐־_/,.;:()]+", unicodedata.normalize("NFKC", str(name)).casefold())
    words = [w for w in words if w not in ("al", "el")]  # stand-alone articles
    code = "".join(encode_word(w) for w in words if w)
    return re.sub(r"(.)\1+", r"\1", code)  # collapse repeated classes


# ---------------------------------------------------------------- sample files
def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_candidate_generation import TESTSETS, sample  # same sampling as the run file

    n_gold = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    n_distractors = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 13
    OUT_DIR.mkdir(exist_ok=True)
    for testset, load in TESTSETS.items():
        datasets, gold = sample(*load(), n_gold, n_distractors, random.Random(seed))
        names = sorted({n for recs in datasets.values() for r in recs.values() for n in [r["name"], *r["alt"]] if n})
        path = OUT_DIR / f"{testset}.tsv"
        with open(path, "w", encoding="utf8") as f:
            f.write("name\tphonetic\n")
            for n in names:
                f.write(f"{n.replace(chr(9), ' ')}\t{encode(n)}\n")
        print(f"{testset}: {len(names)} names -> {path}")


if __name__ == "__main__":
    main()
