#!/usr/bin/env python3
"""Build datasets/Pleiades/pleiades_connections.tsv: the "Connections" (related places) of Pleiades.

On the Pleiades website each place lists the places it is connected to (part of, near, at, on,
flows into, succeeds, ...). These are in connections.csv of the official GIS data package:
  https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip   (CC BY 3.0)

A connection is directed: it is recorded on the place it starts from (place_id) and points to
another place (connects_to). The JSON API calls the outgoing ones "connections" and lists all
connected places, both directions, under "connectsWith".

The zip is cached in datasets/Pleiades/.cache (git-ignored).

Usage: python build_pleiades_connections.py [--out DIR] [--refresh]
Only the standard library is used.
"""
import argparse, csv, io, sys, urllib.request, zipfile
from pathlib import Path

URL = 'https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip'
UA = 'Mozilla/5.0 (X11; Linux x86_64) toponym-entity-resolution research script (stdlib urllib)'


def read_csv(z, name):
    with z.open(f'data/gis/{name}') as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig')))


def pid(uri):
    return uri.rstrip('/').rsplit('/', 1)[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent.parent / 'datasets' / 'Pleiades'))
    ap.add_argument('--refresh', action='store_true', help='re-download the GIS package')
    a = ap.parse_args()
    out = Path(a.out)
    cache = out / '.cache'
    cache.mkdir(parents=True, exist_ok=True)
    (cache / '.gitignore').write_text('*\n')
    zpath = cache / 'pleiades_gis_data.zip'
    if a.refresh or not zpath.exists():
        print(f'Downloading {URL}', file=sys.stderr)
        req = urllib.request.Request(URL, headers={'User-Agent': UA})
        zpath.write_bytes(urllib.request.urlopen(req, timeout=600).read())

    with zipfile.ZipFile(zpath) as z:
        export_date = max(i.date_time for i in z.infolist() if i.filename.endswith('places.csv'))
        places = {r['id']: r['title'] for r in read_csv(z, 'places.csv')}
        terms = {r['key']: r['term'] for r in read_csv(z, 'connection_types.csv')}
        conns = read_csv(z, 'connections.csv')

    in_tsv = set()
    places_tsv = out / 'pleiades_places.tsv'
    if places_tsv.exists():
        with open(places_tsv, encoding='utf-8') as f:
            in_tsv = {r['pleiades_id'] for r in csv.DictReader(f, delimiter='\t')}

    rows = []
    for c in conns:
        to = pid(c['connects_to'])
        rows.append({
            'pleiades_id': c['place_id'],
            'title': places.get(c['place_id'], ''),
            'connection_type': c['connection_type'],
            'connection_term': terms.get(c['connection_type'], c['connection_type']),
            'connects_to_id': to,
            'connects_to_title': places.get(to, ''),
            'association_certainty': c['association_certainty'],
            'year_from': c['year_after_which'],
            'year_to': c['year_before_which'],
            'connection_id': c['id'],
            'connection_uri': c['uri'],
            'from_in_places_tsv': int(c['place_id'] in in_tsv) if in_tsv else '',
            'to_in_places_tsv': int(to in in_tsv) if in_tsv else '',
        })
    rows.sort(key=lambda r: (int(r['pleiades_id']) if r['pleiades_id'].isdigit() else 0, r['connects_to_id']))

    with open(out / 'pleiades_connections.tsv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'GIS export of {export_date[0]}-{export_date[1]:02}-{export_date[2]:02}: '
          f'{len(rows)} connections from {len({r["pleiades_id"] for r in rows})} places', file=sys.stderr)


if __name__ == '__main__':
    main()
