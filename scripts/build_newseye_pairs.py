#!/usr/bin/env python3
"""Build a cross-lingual toponym benchmark from newseye (HIPE-2022).

newseye = historical newspapers in de/fi/fr/sv, uppercase labels (LOC/PER/ORG).
Unlike hipe2020 it has NO fine location types, so no loc_type column. It does
tag people (PER) and organizations (ORG) co-mentioned in the text.

File 1 (entities): id, toponym, language, people_mentioned, orgs_mentioned, sentences
File 2 (matches) : entity1, entity2, entity1_name, entity2_name
                   - positive pairs only, where both share a real Wikidata QID.
                     NIL (unlinkable) is NOT a QID: two NILs never match.

Names/text are extracted as-is in their own language; nothing is translated.
No coordinates and no source metadata (kept to in-text evidence only).

Usage: python build_newseye_pairs.py [newseye_dir] [out_dir]
"""
import sys
import csv
import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_hipe_toponyms import parse_documents, entities, surface as join_surface, TOKEN, MISC

LANGS = ("de", "fi", "fr", "sv")
SEP = "|"


def split_sentences(rows):
    sents, cur = [], []
    for r in rows:
        cur.append(r)
        if "EndOfSentence" in (r[MISC] or ""):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    return sents


def collect(src_dir):
    entmap, order = {}, []
    for lang in LANGS:
        for f in sorted(glob.glob(str(Path(src_dir) / lang / "*.tsv"))):
            if "entities" in f or "matches" in f:
                continue
            for meta, rows in parse_documents(f):
                lg = meta.get("hipe2022:language", lang)
                for srows in split_sentences(rows):
                    locs = list(entities(srows, {"loc"}))
                    if not locs:
                        continue
                    persons = [p[0] for p in entities(srows, {"per"})]
                    orgs = [o[0] for o in entities(srows, {"org"})]
                    text = join_surface([(r[TOKEN], r[MISC]) for r in srows]).strip()
                    for surf, _fine, qid in locs:
                        qid = qid if qid.startswith("Q") else ""  # drop NIL/_
                        key = (surf, lg, qid)
                        e = entmap.get(key)
                        if e is None:
                            e = {"surface": surf, "lang": lg, "qid": qid,
                                 "persons": [], "orgs": [], "sentences": []}
                            entmap[key] = e
                            order.append(e)
                        if text and text not in e["sentences"]:
                            e["sentences"].append(text)
                        for p in persons:
                            if p not in e["persons"]:
                                e["persons"].append(p)
                        for o in orgs:
                            if o not in e["orgs"]:
                                e["orgs"].append(o)
    for i, e in enumerate(order, start=1):
        e["id"] = i
    return order


def build_matches(ents):
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


def main(src_dir, out_dir):
    out_dir = Path(out_dir)
    ents = collect(src_dir)
    write_tsv(
        out_dir / "newseye_entities.tsv",
        ["id", "toponym", "language", "people_mentioned", "orgs_mentioned", "sentences"],
        [[e["id"], e["surface"], e["lang"],
          SEP.join(e["persons"]), SEP.join(e["orgs"]), SEP.join(e["sentences"])]
         for e in ents],
    )
    matches = build_matches(ents)
    write_tsv(out_dir / "newseye_matches.tsv",
              ["entity1", "entity2", "entity1_name", "entity2_name"], matches)

    linked = sum(1 for e in ents if e["qid"])
    xling = sum(1 for m in matches
                if ents[m[0] - 1]["lang"] != ents[m[1] - 1]["lang"])
    from collections import Counter
    print(f"entities : {len(ents)} ({linked} with QID, {len(ents)-linked} without)")
    print(f"  by lang: {dict(Counter(e['lang'] for e in ents))}")
    print(f"matches  : {len(matches)} pairs ({xling} cross-lingual)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "datasets/HIPE-2022/newseye"
    out = sys.argv[2] if len(sys.argv) > 2 else src
    main(src, out)
