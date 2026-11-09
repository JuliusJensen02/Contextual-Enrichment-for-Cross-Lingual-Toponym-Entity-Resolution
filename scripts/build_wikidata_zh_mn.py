#!/usr/bin/env python3
"""Build the Chinese, Mongolian and Russian toponym sets from Wikidata, enriched with TGaz.

Runs wikidata_zh.rq, wikidata_mn.rq and wikidata_ru.rq on QLever, keeps the items in
the region, fetches attributes one query at a time and writes one TSV per language.
The sets are separate pools. em.tsv (zh-mn), em_zh_ru.tsv and em_mn_ru.tsv hold the id
pairs for items in both pools.
See datasets/Wikidata-zh-ru/README.md for the rules.

Usage: python build_wikidata_zh_mn.py [out_dir]
"""
import collections, csv, hashlib, http.client, json, re, shutil, sys, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'datasets/Wikidata-zh-ru'
TGAZ = ROOT / 'datasets/tgaz_csv'
CACHE = OUT / '.cache'
ENDPOINT = 'https://qlever.dev/api/wikidata'
PREFIXES = '''PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
'''
# China and Mongolia span lat 18-54, lon 73-135; the region adds 5 degrees on each side.
LAT, LON = (13, 59), (68, 140)
DISSOLVED_BY = 1949    # anything that ended later is modern, e.g. provinces merged in 2025
FOUNDED_BEFORE = 1800  # settlements only; later "foundings" are mostly municipal dates
BATCH = 2000
ATTEMPTS = 6
RETRY_CODES = {429, 500, 502, 503, 504}  # 500: QLever out of memory, passes once load drops
ID_SALT = 'wikidata-zh-mn'

# Most specific first: these classes nest, and the first hit becomes historical_basis.
ENTITY_CLASSES = {'Q3024240': 'historical_country', 'Q15661340': 'ancient_city',
                  'Q839954': 'archaeological_site', 'Q19953632': 'former_admin_unit',
                  'Q1620908': 'historical_region'}
PLACE_CLASSES = ['Q486972', 'Q56061', 'Q271669', 'Q15324', 'Q355304', 'Q23442']  # as Wikidata-he-ar
REGION_TYPES = {'region', 'cultural region', 'natural region', 'geographic region', 'continent',
                'part of the world', 'coast', 'territory'}
# Types that place an item in China by definition; many of these items have no location data.
CHINA_TYPES = {'fiscal district', 'fu', 'zhou', 'Branch Secretariat', 'historical Chinese state',
               'Chinese dynasty', 'ancient Chinese state'}
ZH_ORDER = ['zh', 'zh-hant', 'zh-hans', 'zh-tw', 'zh-hk', 'zh-mo', 'zh-cn', 'zh-sg', 'zh-my', 'lzh']
HAN = re.compile(r'[㐀-鿿\U00020000-\U0003ffff]')
MONGOLIAN = re.compile(r'[Ѐ-ӿ᠀-᢯]')
CYRILLIC = re.compile(r'[\u0400-\u04ff]')
DISAMBIGUATOR = re.compile(r'\s*[(（][^()（）]*[)）]\s*$')
# Wikidata attributes that link to another item; written as English labels.
LINKED = {'country': 'P17', 'admin_unit': 'P131', 'part_of': 'P361', 'capital': 'P36',
          'replaces': 'P1365', 'replaced_by': 'P1366', 'neighbours': 'P47', 'on_water': 'P206',
          'on_feature': 'P706', 'named_after': 'P138', 'time_period': 'P2348', 'described_by': 'P1343'}
SHARED = ['lat', 'lon', 'coord_source', 'historical_basis', 'instance_of_label', 'inception', 'dissolved',
          *LINKED, 'population', 'elevation_m']
TGAZ_COLUMNS = ['tgaz_name', 'tgaz_pinyin', 'tgaz_beg_yr', 'tgaz_end_yr', 'tgaz_type', 'tgaz_type_py',
                'tgaz_parent', 'tgaz_parent_py', 'tgaz_instances', 'tgaz_present_loc']


def qlever(query):
    error = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(30 * attempt)
        req = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({'query': query}).encode(),
                                     headers={'Accept': 'text/tab-separated-values',
                                              'User-Agent': 'toponym-er-research/0.1'})
        try:
            with urllib.request.urlopen(req, timeout=590) as resp:
                lines = resp.read().decode().rstrip('\n').split('\n')
            time.sleep(2)
            return [(l.split('\t') + ['', ''])[:3] for l in lines[1:] if l]
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')
            # QLever also answers 429 for a query that timed out; retrying that cannot help.
            if e.code not in RETRY_CODES or 'timed out' in body:
                raise RuntimeError(f'{e.code}: {body[:400]}')
            error = f'{e.code}: {body[:200]}'
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException) as e:
            error = repr(e)
        print(f'attempt {attempt + 1}/{ATTEMPTS} failed: {error}', flush=True)
    raise RuntimeError(f'gave up after {ATTEMPTS} attempts: {error}')


def cached(name, query):
    path = CACHE / f'{name}.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    rows = qlever(query)
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    return rows


def qid(term):
    return term.rstrip('>').rsplit('/', 1)[-1]

def text(term):
    m = re.match(r'^"(.*)"(?:@[\w-]+|\^\^.*)?$', term, re.S)
    s = m[1] if m else term
    return s.replace('\\t', ' ').replace('\\n', ' ').replace('\\"', '"').replace('\\\\', '\\').strip()

def lang(term):
    m = re.search(r'@([\w-]+)$', term)
    return m[1].lower() if m else ''

def year(term):
    m = re.match(r'^"?(-?\d+)-\d\d-\d\d', term)
    return int(m[1]) if m else None

def point(term):
    """Earth coordinates only: other globes carry an IRI prefix."""
    m = re.match(r'^"?POINT\((-?[\d.]+) (-?[\d.]+)\)', term)
    return (float(m[2]), float(m[1])) if m else None

def number(term):
    try:
        return float(text(term))
    except ValueError:
        return None

def names(values, script):
    """Unique names in the expected script, without disambiguators like '(936-947)'."""
    cleaned = (DISAMBIGUATOR.sub('', v).strip() for v in values)
    return list(dict.fromkeys(n for n in cleaned if script.search(n)))

def in_region(p):
    return LAT[0] <= p[0] <= LAT[1] and LON[0] <= p[1] <= LON[1]

def join(values):
    return '|'.join(str(v).replace('|', '/') for v in values)


def fetch(name, body, items, columns='?item ?v'):
    """Run a pattern for all items, in batches."""
    rows = []
    for i in range(0, len(items), BATCH):
        values = ' '.join(f'wd:{q}' for q in items[i:i + BATCH])
        rows += cached(f'{name}_{BATCH}_{i}', f'{PREFIXES}SELECT DISTINCT {columns} WHERE {{ VALUES ?item {{ {values} }} {body} }}')
    print(name, len(rows), flush=True)
    return rows


def multi(name, body, items, conv=text):
    d = collections.defaultdict(list)
    for r in fetch(name, body, items):
        v = conv(r[1])
        if v is not None and v not in d[qid(r[0])]:
            d[qid(r[0])].append(v)
    return d


def load_tgaz():
    """TGaz records and present-day locations by sys_id, e.g. hvd_79322."""
    with open(TGAZ / 'placename.csv', encoding='utf-8-sig', newline='') as f:
        internal = {r['id']: r['sys_id'] for r in csv.DictReader(f)}
    places = collections.defaultdict(list)
    csv.field_size_limit(10**9)
    with open(TGAZ / 'present_loc.csv', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['text_value'] and r['placename_id'] in internal:
                places[internal[r['placename_id']]].append(r['text_value'])
    with open(TGAZ / 'mv_pn_srch.csv', encoding='utf-8-sig', newline='') as f:
        records = {r['sys_id']: r for r in csv.DictReader(f)}
    return records, places


def tgaz_fields(ids, records, places):
    """One item can stand for several time-sliced TGaz records."""
    hits = [records[f'hvd_{i}'] for i in ids if f'hvd_{i}' in records]
    if not hits:
        return {}, None
    uniq = lambda key: join(dict.fromkeys(h[key] for h in hits if h[key]))
    years = lambda key: [int(h[key]) for h in hits if re.fullmatch(r'-?\d+', h[key])]
    point_ = next(((float(h['y_coord']), float(h['x_coord'])) for h in hits if h['x_coord'] and h['y_coord']), None)
    return dict(tgaz_name=uniq('name'), tgaz_pinyin=uniq('transcription'), tgaz_beg_yr=min(years('beg_yr'), default=''),
                tgaz_end_yr=max(years('end_yr'), default=''), tgaz_type=uniq('ftype_vn'), tgaz_type_py=uniq('ftype_tr'),
                tgaz_parent=uniq('parent_vn'), tgaz_parent_py=uniq('parent_tr'), tgaz_instances=len(hits),
                tgaz_present_loc=join(dict.fromkeys(p for i in ids for p in places[f'hvd_{i}']))), point_


def signals_from(query_file):
    signals = collections.defaultdict(set)
    rows = cached(query_file, (OUT / f'{query_file}.rq').read_text(encoding='utf-8'))
    for item, sig, _ in rows:
        signals[qid(item)].add(qid(sig) if sig.startswith('<') else text(sig))
    return signals


def main():
    zh_signals, mn_signals = signals_from('wikidata_zh'), signals_from('wikidata_mn')
    ru_signals = signals_from('wikidata_ru')
    signals = collections.defaultdict(set)
    for source in (zh_signals, mn_signals, ru_signals):
        for q, s in source.items():
            signals[q] |= s
    universe = sorted(signals)
    print(len(zh_signals), 'Chinese,', len(mn_signals), 'Mongolian,', len(ru_signals), 'Russian candidates')

    # Region first: the attribute queries below only run for items that survive.
    records, present = load_tgaz()
    chgis = multi('chgis', '?item wdt:P4711 ?v', universe)
    own = multi('coord', '?item wdt:P625 ?v', universe, point)
    capital = multi('capital_coord', '?item wdt:P36/wdt:P625 ?v', universe, point)
    parent = multi('parent', '?item wdt:P131|wdt:P17 ?p . ?p wdt:P625 ?v', universe, point)
    parent_capital = multi('parent_capital', '?item wdt:P131|wdt:P17 ?p . ?p wdt:P36/wdt:P625 ?v', universe, point)
    tgaz, tgaz_point = {}, {}
    for q in universe:
        tgaz[q], tgaz_point[q] = tgaz_fields(chgis[q], records, present)

    funnel = collections.Counter()
    location = {}
    unlocated = []
    for q in universe:
        for source, tag in ((own[q], 'own'), ([tgaz_point[q]] if tgaz_point[q] else [], 'tgaz'),
                            (capital[q], 'capital'), (parent[q], 'parent'), (parent_capital[q], 'parent_capital')):
            if source:
                # The first source with any coordinate decides; a parent never overrides own data.
                hit = [p for p in source if in_region(p)]
                if hit:
                    location[q] = (hit[0], tag)
                else:
                    funnel['outside region'] += 1
                break
        else:
            unlocated.append(q)
    items = sorted([*location, *unlocated])
    print(len(location), 'in region,', len(unlocated), 'without location', flush=True)

    types = collections.defaultdict(dict)
    for r in fetch('types', '?item wdt:P31 ?t . OPTIONAL { ?t rdfs:label ?l . FILTER(LANG(?l)="en") }', items, '?item ?t ?l'):
        types[qid(r[0])][qid(r[1])] = text(r[2]) if r[2] else qid(r[1])
    for q in unlocated:
        if set(types[q].values()) & CHINA_TYPES:
            location[q] = (('', ''), 'none')
        else:
            funnel['no location at all'] += 1
    items = sorted(location)

    is_place = set(multi('place', 'VALUES ?v { %s } ?item wdt:P31/wdt:P279* ?v' % ' '.join(f'wd:{c}' for c in PLACE_CLASSES), items))
    settlement = set(multi('settlement', '?item wdt:P31/wdt:P279* wd:Q486972 . BIND(wd:Q486972 AS ?v)', items, qid))
    inception = multi('inception', '?item wdt:P571 ?v', items, year)
    attested = multi('attested', '?item wdt:P1249 ?v', items, year)
    dissolved = multi('dissolved', '?item wdt:P576 ?v', items, year)
    population = multi('population', '?item wdt:P1082 ?v', items, number)
    elevation = multi('elevation', '?item wdt:P2044 ?v', items, number)
    linked = {c: multi(c, f'?item wdt:{p} ?o . ?o rdfs:label ?v . FILTER(LANG(?v)="en")', items) for c, p in LINKED.items()}
    side = '?v . BIND(LANG(?v) AS ?l) FILTER(?l="mn" || ?l="ru" || ?l="lzh" || STRSTARTS(?l,"zh"))'
    labels = collections.defaultdict(dict)
    for r in fetch('labels', f'?item rdfs:label {side}', items):
        labels[qid(r[0])].setdefault(lang(r[1]), text(r[1]))
    aliases = collections.defaultdict(lambda: collections.defaultdict(list))
    for name, prop in (('alias', 'skos:altLabel'), ('native', 'wdt:P1705'), ('official', 'wdt:P1448')):
        for r in fetch(name, f'?item {prop} {side}', items):
            aliases[qid(r[0])][lang(r[1]) if lang(r[1]) in ('mn', 'ru') else 'zh'].append(text(r[1]))
    descriptions = collections.defaultdict(dict)
    for r in fetch('description', f'?item schema:description {side}', items):
        descriptions[qid(r[0])].setdefault(lang(r[1]), text(r[1]))
    wiki = collections.defaultdict(dict)
    for s in ('mn', 'zh', 'ru'):
        for r in fetch(f'wiki_{s}', f'?a schema:about ?item ; schema:isPartOf <https://{s}.wikipedia.org/> ; schema:name ?v', items):
            wiki[qid(r[0])][s] = text(r[1])

    rows = []
    for q in items:
        ended = dissolved[q]
        begun = min(inception[q] + attested[q], default=None)
        basis = next((b for c, b in ENTITY_CLASSES.items() if c in signals[q]), None)
        modern_end = bool(ended) and min(ended) > DISSOLVED_BY
        # "Former capital" makes Beijing or Tokyo a former admin. unit, yet they still exist.
        if q in settlement and not ended and basis in ('former_admin_unit', 'historical_region'):
            basis = 'living_former_capital'
        if not basis and ended and q in is_place:
            basis = 'dissolved'
        if not basis and tgaz[q]:
            basis = 'chgis_linked'
        if not basis and q in settlement and begun is not None and begun < FOUNDED_BEFORE:
            basis = 'old_settlement'
        if modern_end:
            basis = None
        toponym = bool(basis) or q in is_place or bool(REGION_TYPES & set(types[q].values()))
        if not toponym:
            funnel['not a toponym'] += 1
            continue
        zh_all = [labels[q][l] for l in ZH_ORDER if l in labels[q]]
        zh_all += [v for l, v in labels[q].items() if l.startswith('zh') and l not in ZH_ORDER]
        zh_names = names(zh_all + aliases[q]['zh'], HAN)
        mn_names = names([labels[q].get('mn', '')] + aliases[q]['mn'], MONGOLIAN)
        ru_names = names([labels[q].get('ru', '')] + aliases[q]['ru'], CYRILLIC)
        # A modern place only enters the Chinese or Russian pool as a partner of another record.
        # Items found only through the Russian query stay out of the two other pools.
        selected = q in zh_signals or q in mn_signals
        keep_zh = selected and bool(zh_names) and (bool(basis) or bool(mn_names))
        keep_mn = selected and bool(mn_names)
        keep_ru = bool(ru_names) and (bool(basis) or keep_zh or keep_mn)
        if not (keep_zh or keep_mn or keep_ru):
            funnel['no usable record'] += 1
            continue
        latlon, source = location[q]
        desc = descriptions[q]
        shared = dict(lat=latlon[0], lon=latlon[1], coord_source=source, historical_basis=basis or '',
                      instance_of_label=join(sorted(types[q].values())), inception='' if begun is None else begun,
                      dissolved=min(ended, default=''), population=int(max(population[q])) if population[q] else '',
                      elevation_m=elevation[q][0] if elevation[q] else '',
                      **{c: join(linked[c][q]) for c in LINKED})
        rows.append(dict(qid=q, zh=zh_names if keep_zh else None, mn=mn_names if keep_mn else None,
                         ru=ru_names if keep_ru else None, shared=shared,
                         tgaz=tgaz[q], desc_zh=desc.get('zh') or next((v for k, v in desc.items() if k.startswith('zh-')), ''),
                         desc_mn=desc.get('mn', ''), desc_ru=desc.get('ru', ''), wiki_zh=wiki[q].get('zh', ''),
                         wiki_mn=wiki[q].get('mn', ''), wiki_ru=wiki[q].get('ru', '')))

    # Ids hash the QID per language: they reveal no match, and a row added or removed by a
    # later Wikidata edit leaves every other id unchanged. Sorting by id shuffles the rows.
    for s in ('zh', 'mn', 'ru'):
        pool = [r for r in rows if r[s]]
        for r in pool:
            r[f'id_{s}'] = s + hashlib.sha256(f"{ID_SALT}:{s}:{r['qid']}".encode()).hexdigest()[:10]
        pool.sort(key=lambda r: r[f'id_{s}'])
        extra = TGAZ_COLUMNS if s == 'zh' else []
        with open(OUT / f'wikidata_{s}.tsv', 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            w.writerow(['id', 'title', 'variants', 'description', 'wiki_title', *SHARED, *extra])
            for r in pool:
                w.writerow([r[f'id_{s}'], r[s][0], ';'.join(n.replace(';', ',') for n in r[s][1:]), r[f'desc_{s}'], r[f'wiki_{s}'],
                            *[r['shared'][c] for c in SHARED], *[r['tgaz'].get(c, '') for c in extra]])
    for filename, a, b in (('em.tsv', 'zh', 'mn'), ('em_zh_ru.tsv', 'zh', 'ru'), ('em_mn_ru.tsv', 'mn', 'ru')):
        pairs = sorted((r for r in rows if r[a] and r[b]), key=lambda r: r[f'id_{a}'])
        with open(OUT / filename, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            w.writerow(['id_1', 'id_2'])
            w.writerows((r[f'id_{a}'], r[f'id_{b}']) for r in pairs)
        print(filename, len(pairs))

    for k, v in funnel.items():
        print(f'{k}: {v}')
    print({s: sum(1 for r in rows if r[s]) for s in ('zh', 'mn', 'ru')})
    shutil.rmtree(CACHE, ignore_errors=True)


if __name__ == '__main__':
    main()
