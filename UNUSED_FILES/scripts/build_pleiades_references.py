#!/usr/bin/env python3
"""Build datasets/Pleiades/pleiades_references.tsv from the Pleiades JSON dump.

The GIS package has no references. The JSON dump has, for every place, a "references" list:
  citesAsRelated   the same place in other gazetteers/databases (Trismegistos, Wikidata, GeoNames,
                   EDH, ToposText, Nomisma, PAThs, ...)  -> cross-dataset links
  citesAsEvidence  ancient sources mentioning the place (e.g. Herodotus via Perseus)
  seeAlso / seeFurther / ...  Wikipedia, encyclopedias, modern literature

Source: https://atlantides.org/downloads/pleiades/json/pleiades-places-latest.json.gz (CC BY 3.0),
cached in datasets/Pleiades/.cache (git-ignored).

Each row also gets `target` and `target_id` when the URL points to a known database, e.g.
target=trismegistos, target_id=1344 for https://www.trismegistos.org/place/1344.

Usage: python build_pleiades_references.py [--out DIR] [--refresh]
Only the standard library is used.
"""
import argparse, csv, gzip, json, re, sys, urllib.request
from pathlib import Path

URL = 'https://atlantides.org/downloads/pleiades/json/pleiades-places-latest.json.gz'
UA = 'Mozilla/5.0 (X11; Linux x86_64) toponym-entity-resolution research script (stdlib urllib)'

# (target name, regex on the URL with the ID in group 1)
TARGETS = [
    ('trismegistos', r'trismegistos\.org/+(?:place|geo)/(?:\?id=)?(\d+)'),
    ('trismegistos', r'trismegistos\.org/.*[?&](?:tm|id)=(\d+)'),
    ('trismegistos_text', r'trismegistos\.org/text/(\d+)'),
    ('wikidata', r'wikidata\.org/(?:wiki|entity)/(Q\d+)'),
    ('geonames', r'geonames\.org/(\d+)'),
    ('paths', r'paths(?:\.uniroma1\.it|-erc\.eu)/atlas/places/(\d+)'),
    ('syriaca', r'syriaca\.org/place/(\d+)'),
    ('topostext', r'topostext\.org/place/([\w]+)'),
    ('edh', r'edh(?:-www\.adw)?\.ub\.uni-heidelberg\.de/.*geographie/(G\d+)'),
    ('nomisma', r'nomisma\.org/id/([\w-]+)'),
    ('dare', r'imperium\.ahlfeldt\.se/places/(\d+)'),
    ('manto', r'manto\.unh\.edu/(\d+)'),
    ('wikipedia', r'(\w+\.wikipedia\.org/wiki/[^#?]+)'),
    ('perseus', r'(data\.perseus\.org/citations/[^\s]+)'),
]
TARGETS = [(n, re.compile(p, re.I)) for n, p in TARGETS]


TM_HOME = re.compile(r'^(?:https?://)?(?:www\.)?trismegistos\.org/?$', re.I)
TM_GEO_IN_CITATION = re.compile(r'^\s*(?:geo(?:\s*id)?\s*[:,]?\s*)?(\d+)\b(?!\s*=)', re.I)


def classify(url, citation=''):
    for name, rx in TARGETS:
        m = rx.search(url or '')
        if m:
            return name, m.group(1)
    # some TM references link only to the homepage and give the Geo ID in the citation
    m = TM_GEO_IN_CITATION.match(citation) if TM_HOME.match(url or '') else None
    if m:
        return 'trismegistos', m.group(1)
    return '', ''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent.parent / 'datasets' / 'Pleiades'))
    ap.add_argument('--refresh', action='store_true', help='re-download the JSON dump')
    a = ap.parse_args()
    out = Path(a.out)
    cache = out / '.cache'
    cache.mkdir(parents=True, exist_ok=True)
    (cache / '.gitignore').write_text('*\n')
    jpath = cache / 'pleiades-places-latest.json.gz'
    if a.refresh or not jpath.exists():
        print(f'Downloading {URL}', file=sys.stderr)
        req = urllib.request.Request(URL, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=900) as r, open(jpath, 'wb') as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)

    with gzip.open(jpath, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    places = data['@graph'] if isinstance(data, dict) and '@graph' in data else data

    rows = []
    for p in places:
        for ref in p.get('references') or []:
            url = (ref.get('accessURI') or '').strip()
            citation = re.sub(r'\s+', ' ', ref.get('citationDetail') or '').strip()
            target, tid = classify(url, citation)
            rows.append({
                'pleiades_id': str(p.get('id', '')),
                'title': p.get('title', ''),
                'ref_type': ref.get('type', ''),
                'short_title': re.sub(r'\s+', ' ', ref.get('shortTitle') or '').strip(),
                'citation': citation,
                'url': url,
                'target': target,
                'target_id': tid,
            })
    rows.sort(key=lambda r: (int(r['pleiades_id']) if r['pleiades_id'].isdigit() else 0, r['ref_type'], r['short_title']))

    with open(out / 'pleiades_references.tsv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    tm = [r for r in rows if r['target'] == 'trismegistos']
    print(f'{len(places)} places, {len(rows)} references; Trismegistos: {len(tm)} refs on '
          f'{len({r["pleiades_id"] for r in tm})} places', file=sys.stderr)


if __name__ == '__main__':
    main()
