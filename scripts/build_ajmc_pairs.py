#!/usr/bin/env python3
"""Build a two-file cross-lingual toponym benchmark from AJMC (HIPE-2022).

File 1 (entities): id, toponym, language  - one row per unique (toponym,
language) toponym name across all AJMC de/en/fr files.

File 2 (matches): entity1, entity2, match - labeled pairs over the entities
that carry a Wikidata QID. match=true iff the two entities share a QID
(same real-world place). The QID is the ground-truth signal and is NOT written
to either output file.

Names are extracted as-is in their own language; nothing is translated.

Usage: python build_ajmc_pairs.py [ajmc_dir] [out_dir]
"""
import sys
import csv
import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_hipe_toponyms import parse_documents, entities, surface as join_surface, TOKEN, MISC

LANGS = ("de", "en", "fr")
SEP = "|"  # multi-value separator, matching the Syriaca/Pleiades convention


def split_sentences(rows):
    """Split a document's rows into sentences on the MISC EndOfSentence flag."""
    sents, cur = [], []
    for r in rows:
        cur.append(r)
        if "EndOfSentence" in (r[MISC] or ""):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    return sents


def collect(ajmc_dir):
    """Return list of entity dicts deduped by (surface, lang, qid), each
    enriched with the raw sentence(s) the toponym occurs in - the actual text
    a reader sees, the only evidence used for matching. No derived context, no
    source metadata.
    """
    entmap = {}
    order = []
    for lang in LANGS:
        for f in sorted(glob.glob(str(Path(ajmc_dir) / lang / "*.tsv"))):
            if "entities" in f or "matches" in f or "toponyms" in f:
                continue
            for meta, rows in parse_documents(f):
                lg = meta.get("hipe2022:language", lang)
                for srows in split_sentences(rows):
                    locs = list(entities(srows, {"loc"}))
                    if not locs:
                        continue
                    text = join_surface([(r[TOKEN], r[MISC]) for r in srows]).strip()
                    for surf, _fine, qid in locs:
                        qid = qid if qid.startswith("Q") else ""
                        key = (surf, lg, qid)
                        e = entmap.get(key)
                        if e is None:
                            e = {"surface": surf, "lang": lg, "qid": qid, "sentences": []}
                            entmap[key] = e
                            order.append(e)
                        if text and text not in e["sentences"]:
                            e["sentences"].append(text)
    for i, e in enumerate(order, start=1):
        e["id"] = i
    return order


def build_matches(ents):
    """Matching pairs only: every pair of QID-bearing entities that share a
    QID (same real-world place). Non-listed pairs are implicitly non-matches."""
    linked = [e for e in ents if e["qid"]]
    pairs = []
    for i in range(len(linked)):
        for j in range(i + 1, len(linked)):
            a, b = linked[i], linked[j]
            if a["qid"] == b["qid"]:
                pairs.append((a["id"], b["id"], a["surface"], b["surface"]))
    return pairs


def write_tsv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main(ajmc_dir, out_dir):
    out_dir = Path(out_dir)
    ents = collect(ajmc_dir)
    write_tsv(
        out_dir / "ajmc_entities.tsv",
        ["id", "toponym", "language", "sentences"],
        [[e["id"], e["surface"], e["lang"], SEP.join(e["sentences"])] for e in ents],
    )
    matches = build_matches(ents)
    write_tsv(out_dir / "ajmc_matches.tsv",
              ["entity1", "entity2", "entity1_name", "entity2_name"], matches)

    linked = sum(1 for e in ents if e["qid"])
    print(f"entities : {len(ents)} ({linked} with QID, {len(ents)-linked} without)")
    print(f"matches  : {len(matches)} matching pairs")


if __name__ == "__main__":
    ajmc = sys.argv[1] if len(sys.argv) > 1 else "datasets/HIPE-2022/ajmc"
    out = sys.argv[2] if len(sys.argv) > 2 else ajmc
    main(ajmc, out)
