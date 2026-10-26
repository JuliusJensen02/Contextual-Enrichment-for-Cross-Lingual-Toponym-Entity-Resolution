#!/usr/bin/env python3
"""Extract toponyms + per-document context from a HIPE-2022 CoNLL/TSV file.

HIPE files are one-token-per-line with IOB tags in the NE columns. This walks
each document, reconstructs entity surface forms (respecting NoSpaceAfter), and
emits one row per toponym (loc) mention, grouped into the project's data
categories: name, geography(link), time/source, text context.

Context (related persons/works) is collected at document scope - an AJMC
document is a single commentary page, a natural context unit. Everything is
extracted as-is in the document's own language; nothing is translated.

Usage: python extract_hipe_toponyms.py <input.tsv> [output.tsv]
"""
import sys
import csv
from pathlib import Path

# HIPE column indices
TOKEN, COARSE, _METO, FINE, _FM, _FC, _NEST, NEL, _NM, MISC = range(10)


def parse_documents(path):
    """Yield (meta: dict, rows: list[list[str]]) per document.

    Token rows always contain tabs; metadata/comment lines never do. A new
    document begins when a metadata key reappears (datasets differ on whether
    the first key is document_id or original_source), so this is dataset-
    agnostic. Tokens whose text starts with '#' (OCR noise like '###') are kept.
    """
    meta, rows = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if "\t" not in line:  # metadata or comment (never a token row)
                if line.startswith("#") and " = " in line:
                    key, val = line[1:].split(" = ", 1)
                    key = key.strip()
                    if rows and key in meta:  # repeated key => new document block
                        yield meta, rows
                        meta, rows = {}, []
                    meta[key] = val.strip()
                continue
            if line.startswith("TOKEN\t"):  # header
                continue
            rows.append(line.split("\t"))
    if rows:
        yield meta, rows


def surface(tokens_misc):
    """Join (token, misc) pairs, respecting NoSpaceAfter."""
    out = ""
    for i, (tok, misc) in enumerate(tokens_misc):
        out += tok
        nospace = "NoSpaceAfter" in (misc or "")
        if i < len(tokens_misc) - 1 and not nospace:
            out += " "
    return out


def entities(rows, want_coarse):
    """Yield (surface, fine_type, qid) for every entity whose coarse label
    (lowercased, minus BIO prefix) is in want_coarse."""
    cur = None  # (coarse, fine, qid, [(tok,misc)])
    for r in rows:
        tag = r[COARSE]
        base = tag[2:].lower() if tag[:2] in ("B-", "I-") else ""
        if tag.startswith("B-") and base in want_coarse:
            if cur:
                yield _flush(cur)
            fine = r[FINE][2:] if r[FINE][:2] in ("B-", "I-") else r[FINE]
            qid = r[NEL] if r[NEL] not in ("_", "O", "") else ""
            cur = (base, fine, qid, [(r[TOKEN], r[MISC])])
        elif tag.startswith("I-") and cur and base == cur[0]:
            cur[3].append((r[TOKEN], r[MISC]))
        else:
            if cur:
                yield _flush(cur)
                cur = None
    if cur:
        yield _flush(cur)


def _flush(cur):
    base, fine, qid, toks = cur
    return surface(toks), fine, qid


def extract(input_path, output_path):
    cols = [
        # name
        "toponym", "lang", "loc_fine_type", "toponym_qid",
        # text context (document scope)
        "related_persons", "related_person_qids", "related_works",
        # time / source
        "document_id", "date", "author", "title", "publication_place", "page",
    ]
    out_rows = []
    for meta, rows in parse_documents(input_path):
        lang = meta.get("hipe2022:language", "")
        # collect document-scope context once
        persons = list(entities(rows, {"pers"}))
        works = list(entities(rows, {"work"}))
        person_names = _dedup([p[0] for p in persons])
        person_qids = _dedup([p[2] for p in persons if p[2]])
        work_names = _dedup([w[0] for w in works])

        for topo, fine, qid in entities(rows, {"loc"}):
            out_rows.append([
                topo, lang, fine, qid,
                ", ".join(person_names),
                ", ".join(person_qids),
                ", ".join(work_names),
                meta.get("hipe2022:document_id", ""),
                meta.get("hipe2022:date", ""),
                meta.get("ajmc:author", ""),
                meta.get("ajmc:title", ""),
                meta.get("ajmc:publication_place", ""),
                meta.get("ajmc:page", ""),
            ])

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        w.writerows(out_rows)
    return len(out_rows)


def _dedup(seq):
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp.with_name(inp.stem + "_toponyms.tsv")
    n = extract(inp, out)
    print(f"{n} toponym rows -> {out}")
