#!/usr/bin/env python3
"""Build a cross-lingual toponym benchmark from hipe2020 (HIPE-2022).

Same two-file shape as the AJMC builder, but hipe2020 (historical newspapers,
de/en/fr) carries fine-grained location types, so each entity also gets a
loc_type. People co-mentioned in the toponym's sentence(s) are included too.

File 1 (entities): id, toponym, language, loc_type, people_mentioned, sentences
File 2 (matches) : entity1, entity2, entity1_name, entity2_name
                   - positive pairs only, where both share a real Wikidata QID.
                     NIL (unlinkable) is NOT a QID: two NILs never match.

Names/text are extracted as-is in their own language; nothing is translated.
Coordinates are NOT available in hipe2020 text (would require external lookup).

Usage: python build_hipe2020_pairs.py [hipe2020_dir] [out_dir]
"""
import sys
import csv
import glob
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_hipe_toponyms import parse_documents, entities, surface as join_surface, TOKEN, MISC

LANGS = ("de", "en", "fr")
SEP = "|"

# readable labels for hipe2020 fine location types
TYPE_MAP = {
    "loc.adm.town": "town", "loc.adm.nat": "country", "loc.adm.reg": "region",
    "loc.adm.sup": "supranational", "loc.phys.hydro": "water",
    "loc.phys.geo": "geographical", "loc.oro": "mountain", "loc.fac": "facility",
    "loc.phys.astro": "astronomical", "loc.unk": "unknown",
    "loc.add.phys": "other-physical", "loc.add.elec": "other",
}


def loc_type(fine):
    if fine in TYPE_MAP:
        return TYPE_MAP[fine]
    if fine.startswith("loc."):
        return fine[4:]
    return ""  # bare "loc" / empty -> unspecified


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
                    persons = [p[0] for p in entities(srows, {"pers"})]
                    text = join_surface([(r[TOKEN], r[MISC]) for r in srows]).strip()
                    for surf, fine, qid in locs:
                        qid = qid if qid.startswith("Q") else ""  # drop NIL/_
                        key = (surf, lg, qid)
                        e = entmap.get(key)
                        if e is None:
                            e = {"surface": surf, "lang": lg, "qid": qid,
                                 "types": Counter(), "persons": [], "sentences": []}
                            entmap[key] = e
                            order.append(e)
                        t = loc_type(fine)
                        if t:
                            e["types"][t] += 1
                        if text and text not in e["sentences"]:
                            e["sentences"].append(text)
                        for p in persons:
                            if p not in e["persons"]:
                                e["persons"].append(p)
    for i, e in enumerate(order, start=1):
        e["id"] = i
        # most frequent type across this entity's mentions
        e["loc_type"] = e["types"].most_common(1)[0][0] if e["types"] else ""
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
        out_dir / "hipe2020_entities.tsv",
        ["id", "toponym", "language", "loc_type", "people_mentioned", "sentences"],
        [[e["id"], e["surface"], e["lang"], e["loc_type"],
          SEP.join(e["persons"]), SEP.join(e["sentences"])] for e in ents],
    )
    matches = build_matches(ents)
    write_tsv(out_dir / "hipe2020_matches.tsv",
              ["entity1", "entity2", "entity1_name", "entity2_name"], matches)

    linked = sum(1 for e in ents if e["qid"])
    xling = sum(1 for m in matches
                if ents[m[0] - 1]["lang"] != ents[m[1] - 1]["lang"])
    print(f"entities : {len(ents)} ({linked} with QID, {len(ents)-linked} without)")
    print(f"matches  : {len(matches)} pairs ({xling} cross-lingual)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "datasets/HIPE-2022/hipe2020"
    out = sys.argv[2] if len(sys.argv) > 2 else src
    main(src, out)
