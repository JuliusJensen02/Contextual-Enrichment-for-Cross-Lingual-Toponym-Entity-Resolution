#!/usr/bin/env python3
"""Build the Pleiades <-> Trismegistos matching set in datasets/Pleades_Trismegistos/.

Inputs (all already in the repo or its caches):
  datasets/Pleiades/.cache/pleiades-places-latest.json.gz   Pleiades JSON dump
      (run scripts/build_pleiades_references.py first to download it)
  datasets/Pleiades/.cache/pleiades_gis_data.zip            optional, only for connection-type labels
  datasets/Trismegistos/trismegistos_places.tsv              TM places
  datasets/PAThs/paths_places.tsv                            optional third source of links

Outputs:
  pleiades.tsv       one row per Pleiades place, matching features only (no IDs of other databases)
  trismegistos.tsv   one row per TM place (ghost names removed), matching features only
  em.tsv             all Pleiades <-> TM matches with the sources that assert them
  trismegistos_texts.tsv  papyri written/found at each TM place (from datasets/Trismegistos/), with a
                     snippet around the place name where the text mentions it

Match sources:
  pleiades      Pleiades references of type citesAsRelated (etc.) pointing to a TM place
  trismegistos  TM's own Pleiades links (pleiades_id = rel_Pleiades = close_matches "Pleiades=")
  paths         PAThs skos:exactMatch to both a Pleiades and a TM place

Usage: python build_pleiades_trismegistos.py
Only the standard library is used.
"""
import csv, gzip, html, io, json, re, sys, unicodedata, zipfile
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parent.parent / 'datasets'
OUT = ROOT / 'Pleades_Trismegistos'
SEP = ' | '

TM_URL = re.compile(r'trismegistos\.org/+(?:place|geo)/(?:\?id=)?(\d+)', re.I)
TM_HOME = re.compile(r'^(?:https?://)?(?:www\.)?trismegistos\.org/?$', re.I)
TM_GEO_IN_CITATION = re.compile(r'^\s*(?:geo(?:\s*id)?\s*[:,]?\s*)?(\d+)\b(?!\s*=)', re.I)
# any URL of a database / gazetteer: such references are links, not context
DB_URL = re.compile(r'trismegistos|wikidata|geonames|wikipedia|syriaca|paths|topostext|nomisma|'
                    r'ahlfeldt|uni-heidelberg|manto|darmc|vici\.org|dainst|tp-online|pelagios|'
                    r'whgazetteer|livius|cambridge\.org/us/talbert', re.I)
PERIOD_ORDER = ['archaic', 'classical', 'hellenistic-republican', 'roman', 'late-antique',
                'mediaeval-byzantine', 'modern']


def clean(s):
    s = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(s or '')))).strip()
    return '' if s == 'None' else s  # Pleiades stores a literal "None" in some fields


def uniq(xs):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return out


def write_tsv(path, rows, fields=None):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def read_tsv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def split_ids(s):
    return [x.strip().rstrip('/') for x in re.split(r'\s*\|\s*', s or '') if x.strip()]


# ---------------------------------------------------------------- Pleiades
def tm_ids_of_reference(ref):
    url = (ref.get('accessURI') or '').strip()
    m = TM_URL.search(url)
    if m:
        return m.group(1)
    if TM_HOME.match(url):
        m = TM_GEO_IN_CITATION.match(clean(ref.get('citationDetail')))
        if m:
            return m.group(1)
    return None


def build_pleiades():
    dump = ROOT / 'Pleiades' / '.cache' / 'pleiades-places-latest.json.gz'
    if not dump.exists():
        sys.exit(f'{dump} missing: run scripts/build_pleiades_references.py first')
    with gzip.open(dump, 'rt', encoding='utf-8') as f:
        places = json.load(f)['@graph']

    terms = {}
    gis = ROOT / 'Pleiades' / '.cache' / 'pleiades_gis_data.zip'
    if gis.exists():
        with zipfile.ZipFile(gis) as z, z.open('data/gis/connection_types.csv') as f:
            terms = {r['key']: r['term'] for r in csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig'))}
    title = {p['id']: clean(p.get('title')) for p in places}

    incoming = defaultdict(list)
    for p in places:
        for c in p.get('connections') or []:
            to = (c.get('connectsTo') or '').rstrip('/').rsplit('/', 1)[-1]
            ct = c.get('connectionType') or 'connection'
            incoming[to].append(f'{title.get(p["id"], "")} ({terms.get(ct, ct)})')

    rows, links = [], []
    for p in places:
        pid = p['id']
        names = p.get('names') or []
        rom, grc, lat, by_lang = [], [], [], []
        for n in names:
            forms = [x.strip() for x in (n.get('romanized') or '').split(',') if x.strip()]
            rom += forms
            att, lang = clean(n.get('attested')), (n.get('language') or '')
            base = lang.split('-')[0]
            # every name with a language: attested form if there is one, else the first romanized form
            if lang and (att or forms):
                by_lang.append(f'{att or forms[0]}@{lang}')
            if att and base == 'grc':
                grc.append(att)
            elif att and base == 'la':
                lat.append(att)

        years, periods = [], set()
        for x in names + (p.get('locations') or []):
            for k in ('start', 'end'):
                if isinstance(x.get(k), (int, float)):
                    years.append(int(x[k]))
            periods |= {a.get('timePeriod') for a in x.get('attestations') or [] if a.get('timePeriod')}
        periods = sorted(periods, key=lambda t: (PERIOD_ORDER.index(t) if t in PERIOD_ORDER else 99, t))

        out_conn = []
        for c in p.get('connections') or []:
            ct = c.get('connectionType') or 'connection'
            to = (c.get('connectsTo') or '').rstrip('/').rsplit('/', 1)[-1]
            out_conn.append(f'{terms.get(ct, ct)}: {title.get(to) or clean(c.get("title"))}')

        evidence = []
        for ref in p.get('references') or []:
            tid = tm_ids_of_reference(ref)
            if tid:
                links.append((pid, tid))
            if ref.get('type') == 'citesAsEvidence' and not DB_URL.search(ref.get('accessURI') or ''):
                evidence.append(' '.join(x for x in (clean(ref.get('shortTitle')), clean(ref.get('citationDetail'))) if x))

        lon_lat = p.get('reprPoint') or []
        rows.append({
            'pleiades_id': pid,
            'title': title[pid],
            'description': clean(p.get('description')),
            # URLs removed: they point to Wikipedia or other Pleiades places
            'details': re.sub(r'\s+', ' ', re.sub(r'https?://\S+', '', clean(p.get('details')))).strip(),
            'place_types': SEP.join(p.get('placeTypes') or []),
            'names_romanized': SEP.join(uniq(rom)),
            'names_greek': SEP.join(uniq(grc)),
            'names_latin': SEP.join(uniq(lat)),
            'names_by_language': SEP.join(uniq(by_lang)),
            'n_names': len(names),
            'lat': lon_lat[1] if len(lon_lat) == 2 else '',
            'lon': lon_lat[0] if len(lon_lat) == 2 else '',
            'year_from': min(years) if years else '',
            'year_to': max(years) if years else '',
            'time_periods': SEP.join(periods),
            'connections_out': SEP.join(uniq(out_conn)),
            'connections_in': SEP.join(uniq(incoming.get(pid, []))),
            'ancient_sources': SEP.join(uniq(evidence)),
        })
    rows.sort(key=lambda r: int(r['pleiades_id']))
    return rows, links


# ---------------------------------------------------------------- Trismegistos
def dash_list(s):
    """TM separates variants with ' - '; use ' | ' like the other files."""
    return SEP.join(uniq(x.strip() for x in re.split(r'\s+-\s+', s or '')))


def norm_map(s):
    """Lowercase, strip diacritics, final sigma -> sigma; return (normalized, index into s)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize('NFD', ch.lower()):
            if not unicodedata.combining(c):
                out.append('σ' if c == 'ς' else c)
                idx.append(i)
    return ''.join(out), idx


def name_stems(row):
    """Search stems for a place's Greek and Latin names: first word minus its ending, >= 4 letters."""
    stems = set()
    for n in (row['names_greek'] + SEP + row['names_latin'] + SEP + row['name_standard']).split(SEP):
        words = norm_map(re.sub(r'[\[\]().?]', '', n))[0].split()
        if words and len(words[0]) >= 4:
            stems.add(words[0][:max(4, len(words[0]) - 2)])
    return stems


def fmt_year(y):
    y = int(y)
    return f'{-y} BCE' if y < 0 else f'{y} CE'


def add_texts(tm_rows, n_snippets=5, width=80):
    """Attach papyri written/found at each place: returns rows for trismegistos_texts.tsv and
    fills n_texts / n_texts_mentioning_name / text_snippets on tm_rows."""
    links_f = ROOT / 'Trismegistos' / 'trismegistos_place_texts.tsv'
    texts_f = ROOT / 'Trismegistos' / 'trismegistos_texts.tsv'
    for r in tm_rows:
        r.update({'n_texts': 0, 'n_texts_mentioning_name': 0, 'text_snippets': ''})
    if not (links_f.exists() and texts_f.exists()):
        return []
    by_place = defaultdict(dict)  # geo_id -> tm_text_id -> set(provenance types)
    for l in read_tsv(links_f):
        if l['place_level'] == 'place':
            by_place[l['geo_id']].setdefault(l['tm_text_id'], set()).add(l['provenance_type'] or 'located')
    wanted = {t for g in by_place for t in by_place[g]}
    texts = {r['tm_text_id']: r for r in read_tsv(texts_f) if r['tm_text_id'] in wanted}

    out = []
    for r in tm_rows:
        g = r['trismegistos_id']
        if g not in by_place:
            continue
        stems = name_stems(r)
        snippets = []
        for tid in sorted(by_place[g], key=int):
            t = texts.get(tid)
            if not t:
                continue
            ed = t['edition_text']
            norm, idx = norm_map(ed)
            pos = min((norm.find(s) for s in stems if s in norm), default=-1)
            snippet = ''
            if pos >= 0:
                a, b = idx[pos], idx[min(pos + 1, len(idx) - 1)]
                snippet = ('…' if a > width else '') + ed[max(0, a - width):b + width].strip() + ('…' if b + width < len(ed) else '')
                r['n_texts_mentioning_name'] += 1
            r['n_texts'] += 1
            years = '–'.join(uniq([fmt_year(y) for y in (t['year_from'], t['year_to']) if re.fullmatch(r'-?\d+', y or '')]))
            out.append({
                'trismegistos_id': g, 'tm_text_id': tid,
                'relation': SEP.join(sorted(by_place[g][tid])),
                'title': t['title'], 'material': t['material'], 'text_lang': t['text_lang'],
                'year_from': t['year_from'], 'year_to': t['year_to'], 'keywords': t['keywords'].replace('|', SEP),
                'mentions_name': int(bool(snippet)), 'snippet': snippet,
                'edition_text': ed, 'translation_en': t['translation_en'],
            })
            if snippet:
                snippets.append((not t['translation_en'], int(t['year_from']) if re.fullmatch(r'-?\d+', t['year_from'] or '') else 9999, f'{t["title"]} ({years}): {snippet}'))
        r['text_snippets'] = SEP.join(s for *_, s in sorted(snippets)[:n_snippets])
    return out


def modern_name(r):
    m = re.search(r'\(([^()]*)\)\s*$', r['full_name'])
    return m.group(1).strip() if m and m.group(1) not in r['name_standard'] else ''


def build_tm():
    src = read_tsv(ROOT / 'Trismegistos' / 'trismegistos_places.tsv')
    rows, links, ghosts = [], [], 0
    for r in src:
        for p in split_ids(r['pleiades_id']):
            links.append((p, r['geo_id']))
        if r['country'] == 'ghost name':
            ghosts += 1
            continue
        rows.append({
            'trismegistos_id': r['geo_id'],
            'name_standard': r['name_standard'],
            'names_latin': dash_list(r['name_latin']),
            'names_greek': dash_list(r['unicode_greek']),
            'names_egyptian': dash_list(r['unicode_egyptian']),
            'names_coptic': dash_list(r['unicode_coptic']),
            # full_name = "<country>, <nome> - <standard name> (<modern name>)"; keep only the modern name
            'modern_name': modern_name(r),
            'ethnicon': dash_list(r['ethnicon']),
            'status': r['status'],
            'location': re.sub(r'\s*\(\d+\)', '', r['location']).strip(),
            'country': r['country'],
            'region': r['region'],
            'nomos_code': r['nomos_code'],
            'provincia': r['provincia'],
            'lat': r['lat'], 'lon': r['lon'],
            'begin_date': r['begin_date'], 'end_date': r['end_date'],
        })
    return rows, links, ghosts


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pl_rows, pl_links = build_pleiades()
    tm_rows, tm_links, ghosts = build_tm()
    text_rows = add_texts(tm_rows)

    paths_links = []
    pf = ROOT / 'PAThs' / 'paths_places.tsv'
    if pf.exists():
        for r in read_tsv(pf):
            paths_links += [(p, t) for p in split_ids(r['pleiades_id']) for t in split_ids(r['tm_geo_id'])]

    pl_title = {r['pleiades_id']: r['title'] for r in pl_rows}
    tm_name = {r['trismegistos_id']: r['name_standard'] for r in tm_rows}
    sources = defaultdict(set)
    for name, links in (('pleiades', pl_links), ('trismegistos', tm_links), ('paths', paths_links)):
        for pair in links:
            sources[pair].add(name)

    em, dropped = [], defaultdict(int)
    for (p, t), src in sources.items():
        if p not in pl_title or t not in tm_name:
            dropped['pleiades id not in dump' if p not in pl_title else 'tm id missing or ghost'] += 1
            continue
        src = [s for s in ('pleiades', 'trismegistos', 'paths') if s in src]
        em.append({'pleiades_id': p, 'trismegistos_id': t,
                   'pleiades_title': pl_title[p], 'trismegistos_name': tm_name[t],
                   'sources': SEP.join(src), 'n_sources': len(src)})
    em.sort(key=lambda r: (int(r['pleiades_id']), int(r['trismegistos_id'])))

    write_tsv(OUT / 'pleiades.tsv', pl_rows)
    write_tsv(OUT / 'trismegistos.tsv', tm_rows)
    write_tsv(OUT / 'em.tsv', em)
    if text_rows:
        write_tsv(OUT / 'trismegistos_texts.tsv', text_rows)

    print(f'pleiades.tsv      {len(pl_rows)} places', file=sys.stderr)
    print(f'trismegistos.tsv  {len(tm_rows)} places ({ghosts} ghost names removed)', file=sys.stderr)
    print(f'trismegistos_texts.tsv  {len(text_rows)} place-text links, {len({r["trismegistos_id"] for r in text_rows})} places, '
          f'{sum(r["mentions_name"] for r in text_rows)} mention the name', file=sys.stderr)
    print(f'em.tsv            {len(em)} pairs; dropped {dict(dropped)}', file=sys.stderr)
    for k in (3, 2, 1):
        print(f'  asserted by {k} source(s): {sum(r["n_sources"] == k for r in em)}', file=sys.stderr)


if __name__ == '__main__':
    main()
