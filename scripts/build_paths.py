#!/usr/bin/env python3
"""Build the PAThs places dataset from the project's Pelagios RDF (Turtle) export.

PAThs ("Tracking Papyrus and Parchment Paths: An Archaeological Atlas of Coptic Literature",
ERC, Sapienza University of Rome) publishes its gazetteer of Coptic-period sites in Egypt and
Nubia as Pelagios/LAWD RDF:
  https://docs.paths-erc.eu/raw-data/pelagios-rdf/paths.places.ttl   (CC BY-NC-SA 4.0)

Each lawd:Place carries an English label, name variants tagged egy/grc/cop/lat/arz/eng,
an optional WKT point, an optional date range (periodo:earliestYear/latestYear) and
skos:exactMatch links to Pleiades and Trismegistos (from the PAThs DB fields
paths__places.pleiades and paths__places.tmgeo).

Outputs (in datasets/PAThs/):
  paths.places.ttl    the raw download (kept for reproducibility)
  paths_places.tsv    one row per PAThs place (wide: names grouped per language)
  paths_names.tsv     one row per (place, name variant, language) (long)

Usage: python build_paths.py [--out DIR] [--refresh]
Only the standard library is used; the Turtle parser below covers the subset of Turtle
used in the export (prefixes, IRIs, prefixed names, literals with language tags or
datatypes, blank-node property lists, ',' and ';' lists).
"""
import argparse, csv, re, sys, urllib.request
from collections import defaultdict
from pathlib import Path

URL = 'https://docs.paths-erc.eu/raw-data/pelagios-rdf/paths.places.ttl'
UA = 'Mozilla/5.0 (X11; Linux x86_64) toponym-entity-resolution research script (stdlib urllib)'

# ---------------------------------------------------------------- minimal Turtle parser
TOKEN = re.compile(r'''
    (?P<ws>\s+|\#[^\n]*)
  | (?P<iri><[^>]*>)
  | (?P<lit>"""(?:[^"\\]|\\.|"(?!""))*"""|"(?:[^"\\\n]|\\.)*")
  | (?P<lang>@[a-zA-Z]+(?:-[a-zA-Z0-9]+)*)
  | (?P<dt>\^\^)
  | (?P<punct>[\[\],;.])
  | (?P<pname>[A-Za-z_][\w.-]*?:[\w.%-]*[\w%-]|[A-Za-z_][\w.-]*?:|:[\w.%-]*)
  | (?P<word>[A-Za-z]+|[-+]?\d+(?:\.\d+)?)
''', re.X)
ESC = {'t': '\t', 'n': '\n', 'r': '\r', 'b': '\b', 'f': '\f', '"': '"', "'": "'", '\\': '\\'}


def unescape(s):
    def rep(m):
        e = m.group(1)
        if e[0] in 'uU':
            return chr(int(e[1:], 16))
        return ESC.get(e, e)
    return re.sub(r'\\(u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)', rep, s)


def tokenize(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f'Turtle syntax error at offset {pos}: {text[pos:pos+60]!r}')
        pos = m.end()
        kind = m.lastgroup
        if kind != 'ws':
            out.append((kind, m.group()))
    return out


class Literal(str):
    """A literal value; .lang holds the language tag ('' if none)."""
    def __new__(cls, value, lang='', datatype=''):
        s = super().__new__(cls, value)
        s.lang, s.datatype = lang, datatype
        return s


def parse_turtle(text):
    """Return a list of (subject, predicate, object) triples. IRIs are plain str,
    blank nodes are '_:bN', literals are Literal instances."""
    toks, i = tokenize(text), 0
    prefixes, triples, bn = {}, [], [0]

    def peek():
        return toks[i] if i < len(toks) else (None, None)

    def take(expected=None):
        nonlocal i
        t = toks[i]
        if expected and t[1] != expected:
            raise ValueError(f'expected {expected!r}, got {t[1]!r}')
        i += 1
        return t

    def expand(pname):
        p, local = pname.split(':', 1)
        if p not in prefixes:
            raise ValueError(f'unknown prefix {p!r}')
        return prefixes[p] + local

    def new_bnode():
        bn[0] += 1
        return f'_:b{bn[0]}'

    def term():
        kind, val = take()
        if kind == 'iri':
            return val[1:-1]
        if kind == 'pname':
            return expand(val)
        if kind == 'word' and val == 'a':
            return 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
        if kind == 'word':
            return Literal(val)
        if kind == 'lit':
            raw = val[3:-3] if val.startswith('"""') else val[1:-1]
            lang = dt = ''
            if peek()[0] == 'lang':
                lang = take()[1][1:].lower()
            elif peek()[0] == 'dt':
                take()
                dt = term()
            return Literal(unescape(raw), lang, dt)
        if val == '[':
            node = new_bnode()
            if peek()[1] != ']':
                predicate_object_list(node)
            take(']')
            return node
        raise ValueError(f'unexpected token {val!r}')

    def predicate_object_list(subj):
        while True:
            pred = term()
            while True:
                triples.append((subj, pred, term()))
                if peek()[1] != ',':
                    break
                take(',')
            if peek()[1] != ';':
                return
            while peek()[1] == ';':
                take(';')
            if peek()[1] in ('.', ']', None):
                return

    while i < len(toks):
        kind, val = peek()
        if val in ('@prefix', 'PREFIX') or (kind == 'lang' and val == '@prefix'):
            take()
            p = take()[1].rstrip(':')
            prefixes[p] = take()[1][1:-1]
            if peek()[1] == '.':
                take('.')
            continue
        subj = term()
        if peek()[1] != '.':
            predicate_object_list(subj)
        take('.')
    return triples


# ---------------------------------------------------------------- build
NS = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'lawd': 'http://lawd.info/ontology/',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'geo': 'http://www.opengis.net/ont/geosparql#',
    'dc': 'http://purl.org/dc/terms/',
    'time': 'http://www.w3.org/2006/time#',
    'periodo': 'http://n2t.net/ark:/99152/p0v#',
}
# language tag in the export -> column suffix
LANGS = [('egy', 'egyptian'), ('grc', 'greek'), ('lat', 'latin'), ('cop', 'coptic'),
         ('arz', 'arabic'), ('eng', 'english')]
ARABIC_SCRIPT = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
SEP = ' | '


def clean(s):
    return re.sub(r'\s+', ' ', str(s)).strip()


def build(triples):
    by_s = defaultdict(lambda: defaultdict(list))
    for s, p, o in triples:
        by_s[s][p].append(o)

    places, names = [], []
    for s, props in by_s.items():
        if NS['lawd'] + 'Place' not in props.get(NS['rdf'] + 'type', []):
            continue
        pid = s.rstrip('/').rsplit('/', 1)[-1]
        one = lambda p: clean(props[p][0]) if props.get(p) else ''

        matches = props.get(NS['skos'] + 'exactMatch', [])
        pleiades = [m.rstrip('/').rsplit('/', 1)[-1] for m in matches if 'pleiades.stoa.org' in m]
        tm = [m.rstrip('/').rsplit('/', 1)[-1] for m in matches if 'trismegistos.org' in m]
        other = [m for m in matches if 'pleiades.stoa.org' not in m and 'trismegistos.org' not in m]

        lat = lon = ''
        for g in props.get(NS['geo'] + 'hasGeometry', []):
            for wkt in by_s.get(g, {}).get(NS['geo'] + 'asWKT', []):
                m = re.match(r'\s*POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)', str(wkt), re.I)
                if m:  # WKT is "POINT (lon lat)"
                    lon, lat = m.group(1), m.group(2)

        earliest = latest = ''
        for d in props.get(NS['time'] + 'hasDateTimeDescription', []):
            dp = by_s.get(d, {})
            earliest = clean(dp[NS['periodo'] + 'earliestYear'][0]) if dp.get(NS['periodo'] + 'earliestYear') else earliest
            latest = clean(dp[NS['periodo'] + 'latestYear'][0]) if dp.get(NS['periodo'] + 'latestYear') else latest

        per_lang = defaultdict(list)
        for n in props.get(NS['lawd'] + 'hasName', []):
            for v in by_s.get(n, {}).get(NS['lawd'] + 'variantForm', []):
                name, lang = clean(v), v.lang
                if not name:
                    continue
                if name not in per_lang[lang]:
                    per_lang[lang].append(name)
                script = 'arabic' if ARABIC_SCRIPT.search(name) else ''
                names.append({'paths_id': pid, 'lang': lang, 'name': name,
                              'arabic_script': '1' if script else ('0' if lang == 'arz' else '')})

        row = {
            'paths_id': pid, 'uri': s,
            'label': one(NS['rdfs'] + 'label'),
            'primary_form': one(NS['lawd'] + 'primaryForm'),
        }
        for tag, col in LANGS:
            row[f'names_{col}'] = SEP.join(per_lang.get(tag, []))
        known = {t for t, _ in LANGS}
        row['names_other'] = SEP.join(f'{n}@{l}' for l, ns in per_lang.items() if l not in known for n in ns)
        row.update({
            'n_names': sum(len(v) for v in per_lang.values()),
            'lat': lat, 'lon': lon,
            'earliest_year': earliest, 'latest_year': latest,
            'dc_temporal': one(NS['dc'] + 'temporal'),
            'pleiades_id': SEP.join(pleiades), 'tm_geo_id': SEP.join(tm),
            'other_matches': SEP.join(other),
        })
        places.append(row)

    places.sort(key=lambda r: int(r['paths_id']) if r['paths_id'].isdigit() else 10**9)
    order = {r['paths_id']: k for k, r in enumerate(places)}
    names.sort(key=lambda r: order[r['paths_id']])
    return places, names


def write_tsv(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent.parent / 'datasets' / 'PAThs'))
    ap.add_argument('--refresh', action='store_true', help='re-download the TTL even if present')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ttl = out / 'paths.places.ttl'
    if a.refresh or not ttl.exists():
        print(f'Downloading {URL}', file=sys.stderr)
        req = urllib.request.Request(URL, headers={'User-Agent': UA})
        ttl.write_bytes(urllib.request.urlopen(req, timeout=60).read())

    triples = parse_turtle(ttl.read_text(encoding='utf-8'))
    places, names = build(triples)
    write_tsv(out / 'paths_places.tsv', places)
    write_tsv(out / 'paths_names.tsv', names)
    print(f'{len(triples)} triples -> {len(places)} places, {len(names)} name variants', file=sys.stderr)
    print(f'  with Pleiades: {sum(1 for r in places if r["pleiades_id"])}, '
          f'with TM: {sum(1 for r in places if r["tm_geo_id"])}, '
          f'with both: {sum(1 for r in places if r["pleiades_id"] and r["tm_geo_id"])}', file=sys.stderr)


if __name__ == '__main__':
    main()
