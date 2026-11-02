#!/usr/bin/env python3
"""Build the Trismegistos (TM) Places dataset: places, links, texts and full texts.

Sources (all open; TM data is CC BY-SA 4.0, papyri.info CC BY 3.0, Wikipedia CC BY-SA):
  1. TM Geo table dump  https://www.trismegistos.org/dataservices/tabledump/  (all 17 fields)
  2. TM_geo.sql         local MySQL export in this folder (adds begin/end dates)
  3. GeoResponder       https://www.trismegistos.org/dataservices/georesponder/georesponder.php?id=<geo>
                        (names per language, close/broad/exact matches to partner projects)
  4. GeoRelations       https://www.trismegistos.org/dataservices/georelations/<geo>  (partner IDs)
  5. papyri.info idp.data (GitHub, papyri/idp.data): HGV and DCLP metadata tie TM text IDs to
     TM Geo IDs (place of origin/provenance); DDbDP/DCLP hold the Greek/Latin/Coptic edition
     text, Translations hold English/German/... translations.
  6. Wikipedia          full plain text of the articles TM links each place to, fetched in
                        batches of 50 (prop=revisions wikitext, converted to plain text locally).
                        No API key is needed; pass --contact so Wikimedia can identify the client.

TM's HTML pages (place/<id>, text/<id>) and the extended RDF (text attestations per place)
are not usable from a script: the former sit behind a browser check, the latter returns
HTTP 500. The papyri.info route is therefore the source for place -> text links.

Every download is cached in <out>/.cache (git-ignored), and per-ID fetches resume, so the
script can be stopped and restarted. A full first run takes roughly 1.5-2 hours (mostly the
130k per-place TM calls); reruns take minutes. --refresh re-downloads the dump and papyri data.

Outputs (in datasets/Trismegistos/):
  trismegistos_places.tsv       one row per TM Geo ID
  trismegistos_place_texts.tsv  TM Geo ID <-> TM text ID (provenance from HGV / DCLP)
  trismegistos_texts.tsv        one row per TM text with metadata, edition text and translations
  trismegistos_wikipedia.tsv    TM Geo ID <-> Wikipedia article with full plain text

Usage: python build_trismegistos.py [--out DIR] [--workers N] [--limit N] [--contact EMAIL]
                                    [--refresh] [--skip-api] [--skip-papyri] [--skip-wikipedia]
"""
import argparse, collections, concurrent.futures as cf, csv, html, io, json, re, sys, tarfile, threading, time
import urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

csv.field_size_limit(10**9)
UA = 'Mozilla/5.0 (X11; Linux x86_64) toponym-entity-resolution research script (stdlib urllib)'
TM = 'https://www.trismegistos.org/dataservices'
DUMP_FIELDS = ['id', 'country', 'region', 'nomos_code', 'name_latin', 'name_standard', 'full_name', 'status',
               'ethnicon', 'location', 'unicode_greek', 'unicode_egyptian', 'unicode_coptic', 'provincia',
               'coordinates', 'pleiades_id', 'geonames']
IDP_TARBALL = 'https://codeload.github.com/papyri/idp.data/tar.gz/refs/heads/master'
TEI = '{http://www.tei-c.org/ns/1.0}'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
GEO_REF = re.compile(r'trismegistos\.org/place/(\d+)')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, file=sys.stderr, flush=True)


def http(url, data=None, timeout=120, tries=6):
    """GET (or POST form `data`) with retries and back-off. Returns bytes."""
    body = urllib.parse.urlencode(data, doseq=True).encode() if data else None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 404): raise
            if i == tries - 1: raise
            wait = 2 ** i * 2
            if isinstance(e, urllib.error.HTTPError) and e.code in (429, 503):
                try: wait = max(wait, int(e.headers.get('Retry-After', 0)) + 1)
                except ValueError: pass
            time.sleep(wait)


def clean(s):
    """One-line cell: collapse whitespace, keep line structure as ' / '."""
    if s is None: return ''
    s = str(s).replace('\t', ' ')
    lines = [re.sub(r'\s+', ' ', l).strip() for l in s.split('\n')]
    return ' / '.join(l for l in lines if l)


# ---------------------------------------------------------------- 1. TM table dump + SQL

def load_dump(cache):
    p = cache / 'tm_geo_dump.csv'
    if not p.exists():
        log('downloading TM Geo table dump (CSV, all fields)')
        raw = http(f'{TM}/tabledump/dump.php?serve=geo', {'mode': 'csv', 'checkbox[]': DUMP_FIELDS}, timeout=600)
        p.write_bytes(raw)
    txt = p.read_text(encoding='utf-8-sig')
    txt = re.sub(r'";(\r?\n|$)', r'"\1', txt)  # rows end in '";'
    rows = list(csv.DictReader(io.StringIO(txt)))
    log(f'dump: {len(rows):,} places')
    return {r['id']: r for r in rows}


def load_sql(path):
    """Parse the phpMyAdmin INSERT statements of TM_geo.sql into dicts keyed by TM Geo ID."""
    if not path.exists(): return {}
    s = path.read_text(encoding='utf-8')
    out = {}
    for m in re.finditer(r'INSERT INTO `geo` \((.*?)\) VALUES\s*', s):
        cols = [c.strip(' `') for c in m.group(1).split(',')]
        i, n = m.end(), len(s)
        while i < n:
            while s[i] in ' \n\r,': i += 1
            if s[i] == ';': break
            assert s[i] == '(', s[i:i + 50]
            i += 1; vals = []
            while True:
                while s[i] == ' ': i += 1
                if s[i] == "'":
                    i += 1; buf = []
                    while True:
                        c = s[i]
                        if c == '\\': buf.append({'n': '\n', 'r': '\r', 't': '\t', '0': '\0'}.get(s[i + 1], s[i + 1])); i += 2
                        elif c == "'" and s[i + 1] == "'": buf.append("'"); i += 2
                        elif c == "'": i += 1; break
                        else: buf.append(c); i += 1
                    vals.append(''.join(buf))
                else:
                    j = i
                    while s[i] not in ',)': i += 1
                    v = s[j:i].strip(); vals.append('' if v == 'NULL' else v)
                while s[i] == ' ': i += 1
                if s[i] == ',': i += 1; continue
                if s[i] == ')': i += 1; break
            r = dict(zip(cols, vals)); out[r['TM Geo ID']] = r
    log(f'TM_geo.sql: {len(out):,} places')
    return out


# ---------------------------------------------------------------- 2. per-ID TM endpoints

def load_cache(cache_file):
    """Read a JSONL cache ({"id":..,"data":..}); rewrite it without duplicates if it has any."""
    done, n = {}, 0
    if cache_file.exists():
        for line in cache_file.open(encoding='utf-8'):
            try: d = json.loads(line); done[d['id']] = d['data']; n += 1
            except Exception: pass
        if n > len(done):
            tmp = cache_file.with_suffix('.tmp')
            with tmp.open('w', encoding='utf-8') as f:
                for k, v in done.items(): f.write(json.dumps({'id': k, 'data': v}, ensure_ascii=False) + '\n')
            tmp.replace(cache_file)
    return done


def fetch_per_id(ids, cache_file, url_fn, workers, label):
    """Fetch url_fn(id) for every id not yet in cache_file (JSONL: {"id":..,"data":..})."""
    done = load_cache(cache_file)
    todo = [i for i in ids if i not in done]
    log(f'{label}: {len(done):,} cached, {len(todo):,} to fetch')
    lock, t0 = threading.Lock(), time.time()

    def one(i):
        try:
            raw = http(url_fn(i), timeout=60)
            try: data = json.loads(raw)
            except ValueError: data = {'_error': 'non-json', '_body': raw[:200].decode('utf-8', 'replace')}
        except Exception as e:
            data = {'_error': repr(e)}
        return i, data

    with cache_file.open('a', encoding='utf-8') as f, cf.ThreadPoolExecutor(workers) as ex:
        for k, (i, data) in enumerate(ex.map(one, todo), 1):
            if isinstance(data, dict) and '_error' in data and 'non-json' not in data['_error']:
                continue  # network failure: not cached, retried on the next run
            done[i] = data
            with lock: f.write(json.dumps({'id': i, 'data': data}, ensure_ascii=False) + '\n')
            if k % 2000 == 0:
                f.flush(); rate = k / (time.time() - t0)
                log(f'{label}: {k:,}/{len(todo):,} ({rate:.1f}/s, ~{(len(todo) - k) / rate / 60:.0f} min left)')
    missing = len([i for i in ids if i not in done])
    if missing: log(f'{label}: {missing:,} failed (network); rerun to retry')
    return done


def flatten_responder(d):
    """GeoResponder JSON -> dict of columns."""
    if not isinstance(d, dict) or 'title' not in d: return {}
    out = {}
    names = d.get('names') or {}
    out['responder_names'] = ' | '.join(f"{v.get('name', '')}@{k}" for k, v in names.items() if isinstance(v, dict))
    links = d.get('links') or {}
    for kind in ('exact matches', 'close matches', 'broad matches'):
        grp = links.get(kind) or {}
        if isinstance(grp, dict):
            uris = [f"{proj}={u.get('URI')}" for proj, lst in grp.items() for u in (lst or []) if isinstance(u, dict)]
        else:
            uris = []
        out[kind.split()[0] + '_matches'] = ' | '.join(uris)
    props = d.get('properties') or {}
    out['responder_status'] = props.get('status', '')
    return out


def flatten_relations(d):
    """GeoRelations JSON (list of {partner: null|str|[str]}) -> {partner: 'a|b'}."""
    out = collections.defaultdict(list)
    if isinstance(d, list):
        for item in d:
            if not isinstance(item, dict): continue
            for k, v in item.items():
                if k.startswith('TM') or v is None: continue
                for x in (v if isinstance(v, list) else [v]):
                    if x not in out[k]: out[k].append(str(x))
    return {k: '|'.join(v) for k, v in out.items()}


# ---------------------------------------------------------------- 3. papyri.info (idp.data)

def epidoc_text(el):
    """Serialise an EpiDoc edition/translation element to a clean reading text.

    Expansions are written out, supplied text is kept without brackets, regularised
    readings are preferred (reg > corr > expan), lost text becomes [...], <lb/> a newline."""
    parts = []

    def walk(e):
        tag = e.tag.replace(TEI, '') if isinstance(e.tag, str) else ''
        if tag in ('note', 'rdg', 'orig', 'sic', 'del', 'figure', 'certainty', 'bibl', 'head', 'surplus') or not isinstance(e.tag, str):
            parts.append(e.tail or ''); return
        if tag == 'lb':
            parts.append('' if e.get('break') == 'no' else '\n')
        elif tag in ('gap', 'space'):
            parts.append(' [...] ' if tag == 'gap' else ' ')
        elif tag == 'choice':
            kids = list(e)
            pick = next((k for want in ('reg', 'corr', 'expan') for k in kids if k.tag == TEI + want), kids[0] if kids else None)
            if pick is not None: walk_inner(pick)
        elif tag == 'app':
            lem = e.find(TEI + 'lem')
            if lem is not None: walk_inner(lem)
        elif tag == 'subst':
            add = e.find(TEI + 'add')
            if add is not None: walk_inner(add)
        elif tag == 'div' and e.get('type') == 'textpart':
            parts.append('\n'); walk_inner(e); parts.append('\n')
        elif tag in ('p', 'ab', 'l'):
            parts.append('\n'); walk_inner(e); parts.append('\n')
        else:
            walk_inner(e)
        parts.append(e.tail or '')

    def walk_inner(e):
        parts.append(e.text or '')
        for c in e: walk(c)

    walk_inner(el)
    txt = ''.join(parts)
    txt = re.sub(r'[ \t\r]+', ' ', txt)
    txt = re.sub(r'(\[\.\.\.\]\s*)+', '[...] ', txt)
    return '\n'.join(l.strip() for l in txt.split('\n') if l.strip())


def idnos(root):
    out = collections.defaultdict(list)
    for e in root.iter(TEI + 'idno'):
        if e.get('type') and (e.text or '').strip(): out[e.get('type')].append(e.text.strip())
    return out


def parse_meta(root):
    """HGV / DCLP header: title, date, places (with TM Geo IDs), keywords, material."""
    m = {}
    t = root.find(f'.//{TEI}titleStmt/{TEI}title')
    m['title'] = clean(''.join(t.itertext())) if t is not None else ''
    if m['title'].lower() in ('keiner', 'keine', 'none'): m['title'] = ''  # HGV placeholder for "no title"
    op = root.find(f'.//{TEI}origPlace')
    m['orig_place'] = clean(''.join(op.itertext())) if op is not None else ''
    dates = root.findall(f'.//{TEI}origin/{TEI}origDate')
    m['orig_date'] = ' | '.join(clean(''.join(d.itertext())) for d in dates)
    yrs = []
    for d in dates:
        for a in ('when', 'notBefore', 'notAfter'):
            v = d.get(a)
            if v and re.match(r'-?\d{4}', v): yrs.append(int(v[:5] if v.startswith('-') else v[:4]))
    m['year_from'], m['year_to'] = (min(yrs), max(yrs)) if yrs else ('', '')
    mat = root.find(f'.//{TEI}material')
    m['material'] = clean(mat.text) if mat is not None else ''
    m['keywords'] = '|'.join(clean(x.text) for x in root.iter(TEI + 'term') if x.text and x.text.strip())
    langs = [x.get('mainLang') for x in root.iter(TEI + 'textLang') if x.get('mainLang')]
    m['text_lang'] = '|'.join(langs)
    links = []  # (geo_id, provenance_type, subtype, name)
    for prov in root.iter(TEI + 'provenance'):
        ptype = prov.get('type') or ''
        for pn in prov.iter(TEI + 'placeName'):
            for g in GEO_REF.findall(pn.get('ref') or ''):
                links.append((g, ptype, pn.get('subtype') or 'place', clean(''.join(pn.itertext()))))
    m['links'] = list(dict.fromkeys(links))
    return m


def download_idp(cache):
    p = cache / 'idp.data.tar.gz'
    if p.exists(): return p
    log('downloading papyri.info idp.data (GitHub tarball, ~1-2 GB)')
    part = p.with_suffix('.part')
    req = urllib.request.Request(IDP_TARBALL, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=300) as r, part.open('wb') as f:
        n = 0
        while chunk := r.read(1 << 20):
            f.write(chunk); n += len(chunk)
            if n % (200 << 20) < (1 << 20): log(f'  {n >> 20:,} MB')
    part.rename(p)
    return p


def load_papyri(cache):
    pc = cache / 'papyri_parsed.json'
    if pc.exists():
        return json.loads(pc.read_text(encoding='utf-8'))
    tar_path = download_idp(cache)
    hgv, dclp, ddb, trans = [], [], [], []
    log('parsing idp.data (HGV_meta_EpiDoc, DCLP, DDbDP, Translations)')
    with tarfile.open(tar_path, 'r|gz') as tf:
        for k, mem in enumerate(tf):
            if not mem.isfile() or not mem.name.endswith('.xml'): continue
            sect = mem.name.split('/')[1] if '/' in mem.name else ''
            if sect not in ('HGV_meta_EpiDoc', 'DCLP', 'DDbDP', 'Translations'): continue
            try:
                root = ET.parse(tf.extractfile(mem)).getroot()
            except ET.ParseError as e:
                log(f'  skip {mem.name}: {e}'); continue
            ids = idnos(root)
            tm = ids.get('TM', [''])[0]
            if sect in ('HGV_meta_EpiDoc', 'DCLP'):
                m = parse_meta(root); m['tm'] = tm
                if sect == 'HGV_meta_EpiDoc':
                    m['hgv'] = ids.get('filename', [''])[0]; m['ddb_hybrid'] = ids.get('ddb-hybrid', [''])[0]; hgv.append(m)
                else:
                    m['dclp_hybrid'] = ids.get('dclp-hybrid', [''])[0]; m['ldab'] = '|'.join(ids.get('LDAB', []))
                    ed = root.find(f".//{TEI}div[@type='edition']")
                    m['text'] = epidoc_text(ed) if ed is not None else ''
                    m['text_lang'] = m['text_lang'] or (ed.get(XML_LANG) if ed is not None else '') or ''
                    dclp.append(m)
            elif sect == 'DDbDP':
                ed = root.find(f".//{TEI}div[@type='edition']")
                if ed is None: continue
                ddb.append({'tm': tm, 'hgv': '|'.join(ids.get('HGV', [])), 'ddb_hybrid': ids.get('ddb-hybrid', [''])[0],
                            'lang': ed.get(XML_LANG) or '', 'text': epidoc_text(ed)})
            else:
                for div in root.iter(TEI + 'div'):
                    if div.get('type') == 'translation':
                        trans.append({'tm': tm, 'hgv': ids.get('HGV', [''])[0], 'lang': div.get(XML_LANG) or '',
                                      'text': epidoc_text(div)})
            if k % 50000 == 0: log(f'  {k:,} tar members; HGV {len(hgv):,} DCLP {len(dclp):,} DDbDP {len(ddb):,} translations {len(trans):,}')
    out = {'hgv': hgv, 'dclp': dclp, 'ddb': ddb, 'trans': trans}
    pc.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    log(f'papyri: HGV {len(hgv):,}, DCLP {len(dclp):,}, DDbDP {len(ddb):,}, translations {len(trans):,}')
    return out


def build_texts(pap):
    """Merge HGV/DCLP/DDbDP/translations per TM text ID -> (texts, place_text_links)."""
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    links = {}
    for src, recs in (('HGV', pap['hgv']), ('DCLP', pap['dclp'])):
        for m in recs:
            if not m['tm']: continue
            t = T[m['tm']]; t['sources'].append(src)
            for f in ('title', 'orig_place', 'orig_date', 'material', 'keywords', 'text_lang', 'hgv', 'ddb_hybrid',
                      'dclp_hybrid', 'ldab'):
                if m.get(f) not in (None, ''): t[f].append(str(m[f]))
            for f, fn in (('year_from', min), ('year_to', max)):
                if m[f] != '': t[f] = [fn(t[f] + [m[f]])]
            if src == 'DCLP' and m.get('text'): t['edition'].append(m['text'])
            for g, ptype, sub, name in m['links']:
                links[(g, m['tm'], src, ptype, sub)] = name
    for d in pap['ddb']:
        if not d['tm']: continue
        t = T[d['tm']]
        if d['text'] and d['text'] not in t['edition']: t['edition'].append(d['text'])
        if d['lang']: t['edition_lang'].append(d['lang'])
        if d['ddb_hybrid']: t['ddb_hybrid'].append(d['ddb_hybrid'])
        t['sources'].append('DDbDP')
    for tr in pap['trans']:
        if not tr['tm'] or not tr['text']: continue
        lang = tr['lang'] if tr['lang'] in ('en', 'de') else 'other'
        T[tr['tm']]['translation_' + lang].append(tr['text'] if lang != 'other' else f"[{tr['lang']}] {tr['text']}")
    uniq = lambda xs: '|'.join(dict.fromkeys(x for x in xs if x))
    texts = []
    for tm, t in T.items():
        texts.append({
            'tm_text_id': tm, 'sources': uniq(t['sources']), 'title': uniq(t['title']),
            'hgv_ids': uniq(t['hgv']), 'ddb_hybrid': uniq(t['ddb_hybrid']), 'dclp_hybrid': uniq(t['dclp_hybrid']),
            'ldab_ids': uniq(t['ldab']), 'material': uniq(t['material']), 'orig_place': uniq(t['orig_place']),
            'orig_date': uniq(t['orig_date']), 'year_from': (t['year_from'] or [''])[0], 'year_to': (t['year_to'] or [''])[0],
            'keywords': uniq('|'.join(t['keywords']).split('|')),
            'geo_ids': '',  # filled below
            'text_lang': uniq(t['text_lang'] + t['edition_lang']),
            'edition_text': ' // '.join(clean(x) for x in t['edition']),
            'translation_en': ' // '.join(clean(x) for x in t['translation_en']),
            'translation_de': ' // '.join(clean(x) for x in t['translation_de']),
            'translation_other': ' // '.join(clean(x) for x in t['translation_other']),
        })
    by_tm = collections.defaultdict(list)
    for (g, tm, *_ ) in links: by_tm[tm].append(g)
    for r in texts: r['geo_ids'] = '|'.join(dict.fromkeys(by_tm.get(r['tm_text_id'], [])))
    texts.sort(key=lambda r: int(r['tm_text_id']) if r['tm_text_id'].isdigit() else 10**12)
    link_rows = [{'geo_id': g, 'tm_text_id': tm, 'source': src, 'provenance_type': ptype, 'place_level': sub,
                  'name_in_source': name} for (g, tm, src, ptype, sub), name in links.items()]
    link_rows.sort(key=lambda r: (int(r['geo_id']), int(r['tm_text_id']) if r['tm_text_id'].isdigit() else 0))
    return texts, link_rows


# ---------------------------------------------------------------- 4. Wikipedia

WIKI_CUT = re.compile(r'^==+\s*(References|Notes|Footnotes|Citations|Sources|Bibliography|Further reading|External links|'
                      r'See also|Literature|Einzelnachweise|Weblinks|Literatur|Références|Notes et références|Bibliographie|'
                      r'Liens externes|Voir aussi)\s*==+\s*$', re.M | re.I)


def wikitext_to_text(w):
    """Rough wikitext -> plain text: drops templates, tables, refs, files, categories and back-matter sections."""
    m = WIKI_CUT.search(w)
    if m: w = w[:m.start()]
    w = re.sub(r'(?s)<!--.*?-->', '', w)
    w = re.sub(r'(?is)<ref[^>/]*/>|<ref[^>]*>.*?</ref>', '', w)
    w = re.sub(r'(?is)<(gallery|math|timeline|score|syntaxhighlight|imagemap)[^>]*>.*?</\1>', '', w)
    for pat in (r'\{\{[^{}]*\}\}', r'(?s)\{\|(?:(?!\{\|).)*?\|\}'):  # innermost templates / tables first
        while True:
            w2 = re.sub(pat, '', w)
            if w2 == w: break
            w = w2
    link = re.compile(r'\[\[([^\[\]|]*)(?:\|([^\[\]]*))?\]\]')
    def repl(m):
        target, label = m.group(1), m.group(2)
        if re.match(r'\s*:?\s*(File|Image|Datei|Bild|Fichier|Category|Kategorie|Catégorie)\s*:', target, re.I): return ''
        if label is None: return target
        return label.split('|')[-1] if '|' in label else label
    while True:
        w2 = link.sub(repl, w)
        if w2 == w: break
        w = w2
    w = re.sub(r'\[https?://[^\s\]]+\s*([^\]]*)\]', r'\1', w)
    w = re.sub(r"'{2,}", '', w)
    w = re.sub(r'^(=+)\s*(.*?)\s*\1\s*$', r'\2', w, flags=re.M)
    w = re.sub(r'(?m)^[*#:;]+\s*', '', w)
    w = re.sub(r'<[^>]+>', '', w)
    w = re.sub(r'__[A-Z]+__', '', w)
    w = html.unescape(w)
    lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in w.split('\n')]
    return '\n'.join(l for l in lines if l)


def fetch_wikipedia(urls, cache_file, batch=50):
    """urls: Wikipedia article URLs -> {url: {'query': {'pages': [{'title', 'extract'|'missing'}]}}}.

    Batched: 50 titles per request via prop=revisions (full wikitext), converted to plain text
    locally. (TextExtracts only returns one whole-article extract per request.)"""
    done = load_cache(cache_file)
    todo = collections.defaultdict(list)
    for u in sorted(set(urls) - set(done)):
        todo[urllib.parse.urlparse(u).netloc].append(u)
    log(f'wikipedia: {len(done):,} cached, {sum(map(len, todo.values())):,} to fetch in batches of {batch}')
    with cache_file.open('a', encoding='utf-8') as f:
        for host, us in todo.items():
            for k in range(0, len(us), batch):
                chunk = us[k:k + batch]
                title_of = {u: urllib.parse.unquote(u.split('/wiki/', 1)[1]).replace('_', ' ') for u in chunk}
                q = {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'redirects': 1,
                     'format': 'json', 'formatversion': 2, 'titles': '|'.join(dict.fromkeys(title_of.values()))}
                try:
                    d = json.loads(http(f'https://{host}/w/api.php?' + urllib.parse.urlencode(q), timeout=120))
                except Exception as e:
                    log(f'wikipedia: batch failed ({host}, {len(chunk)} titles): {e!r}; rerun to retry'); continue
                qd = d.get('query') or {}
                hop = {x['from']: x['to'] for x in qd.get('normalized', []) + qd.get('redirects', [])}
                pages = {p_['title']: p_ for p_ in qd.get('pages', [])}
                for u, t in title_of.items():
                    seen = set()
                    while t in hop and t not in seen: seen.add(t); t = hop[t]
                    pg = pages.get(t, {'title': t, 'missing': True})
                    revs = pg.get('revisions') or []
                    wt = (((revs[0].get('slots') or {}).get('main') or {}).get('content', '')) if revs else ''
                    rec = {'title': pg.get('title', t)}
                    if wt: rec['extract'] = wikitext_to_text(wt)
                    else: rec['missing'] = True
                    data = {'query': {'pages': [rec]}}
                    done[u] = data
                    f.write(json.dumps({'id': u, 'data': data}, ensure_ascii=False) + '\n')
                f.flush()
                if (k // batch) % 20 == 0: log(f'wikipedia: {host} {k + len(chunk):,}/{len(us):,}')
    return done


# ---------------------------------------------------------------- main

def write_tsv(path, rows, cols):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, cols, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        for r in rows: w.writerow({c: clean(r.get(c, '')) for c in cols})
    log(f'wrote {path} ({len(rows):,} rows)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'datasets/Trismegistos')
    ap.add_argument('--workers', type=int, default=4, help='parallel requests to TM / Wikipedia (default 4)')
    ap.add_argument('--limit', type=int, default=0, help='only the first N places (for testing)')
    ap.add_argument('--skip-api', action='store_true', help='skip GeoResponder / GeoRelations per-place calls')
    ap.add_argument('--skip-papyri', action='store_true', help='skip papyri.info texts')
    ap.add_argument('--skip-wikipedia', action='store_true', help='skip Wikipedia full texts')
    ap.add_argument('--refresh', action='store_true',
                    help='re-download the TM dump and papyri.info data (per-place API caches are kept)')
    ap.add_argument('--contact', default='', help='contact (e-mail/URL) for the User-Agent; Wikipedia throttles anonymous agents')
    a = ap.parse_args()
    global UA
    if a.contact: UA = f'TrismegistosPlacesBuilder/1.0 ({a.contact}) python-urllib'
    out, cache = a.out, a.out / '.cache'
    cache.mkdir(parents=True, exist_ok=True)
    (cache / '.gitignore').write_text('*\n')
    if a.refresh:
        for f in ('tm_geo_dump.csv', 'idp.data.tar.gz', 'papyri_parsed.json'): (cache / f).unlink(missing_ok=True)

    dump = load_dump(cache)
    sql = load_sql(out / 'TM_geo.sql')
    ids = sorted(set(dump) | set(sql), key=int)
    if a.limit: ids = ids[:a.limit]

    resp, rel = {}, {}
    if not a.skip_api:
        resp = fetch_per_id(ids, cache / 'georesponder.jsonl', lambda i: f'{TM}/georesponder/georesponder.php?id={i}',
                            a.workers, 'georesponder')
        rel = fetch_per_id(ids, cache / 'georelations.jsonl', lambda i: f'{TM}/georelations/{i}', a.workers, 'georelations')

    texts, link_rows = [], []
    if not a.skip_papyri:
        texts, link_rows = build_texts(load_papyri(cache))
    n_direct, n_all = collections.Counter(), collections.Counter()
    for l in link_rows:
        n_all[l['geo_id']] += 1
        if l['place_level'] == 'place': n_direct[l['geo_id']] += 1

    # ---- places table
    partners = sorted({k for i in ids for k in flatten_relations(rel.get(i))})
    rows, wiki_urls = [], collections.defaultdict(set)
    for i in ids:
        d, s = dump.get(i, {}), sql.get(i, {})
        r = {'geo_id': i, 'uri': f'https://www.trismegistos.org/place/{i}', 'in_dump': int(i in dump), 'in_sql': int(i in sql)}
        for f in DUMP_FIELDS[1:]:
            r[f] = d.get(f, '')
        # fall back to the SQL export where the dump is empty
        for f, sf in (('country', 'Country'), ('region', 'Region'), ('nomos_code', 'Nomos Code'), ('name_latin', 'Latin Name'),
                      ('name_standard', 'Standard Name'), ('full_name', 'Full Name'), ('status', 'Status'),
                      ('ethnicon', 'Ethnicon'), ('location', 'Location'), ('unicode_greek', 'Greek Unicode'),
                      ('unicode_egyptian', 'Egyptian Unicode'), ('unicode_coptic', 'Coptic Unicode'),
                      ('provincia', 'Province'), ('coordinates', 'Geographical Coordinates')):
            if not r[f] and s.get(sf): r[f] = s[sf]
        lat, lon = (r['coordinates'].split(',') + ['', ''])[:2] if r['coordinates'] else ('', '')
        r['lat'], r['lon'] = lat.strip(), lon.strip()
        has_dates = s.get('Begin Date') not in (None, '', '0') or s.get('End Date') not in (None, '', '0')
        r['begin_date'] = s.get('Begin Date', '') if has_dates else ''
        r['end_date'] = s.get('End Date', '') if has_dates else ''
        r['begin_date_formatted'] = s.get('Begin Date (Formatted)', '') if has_dates else ''
        r['end_date_formatted'] = s.get('End Date (Formatted)', '') if has_dates else ''
        r.update(flatten_responder(resp.get(i)))
        for k, v in flatten_relations(rel.get(i)).items(): r['rel_' + k] = v
        # the dump server ignores pleiades_id / geonames (commented out in its form): use GeoRelations
        r['pleiades_id'] = r['pleiades_id'] or r.get('rel_Pleiades', '')
        r['geonames'] = r['geonames'] or r.get('rel_GeoNames', '')
        for u in re.findall(r'https?://[a-z\-]+\.wikipedia\.org/wiki/[^ |]+', r.get('close_matches', '') + ' ' + r.get('exact_matches', '')):
            wiki_urls[i].add(u)
        for t in (r.get('rel_Wikipedia') or '').split('|'):
            if t and not any(u.endswith('/wiki/' + t.replace(' ', '_')) for u in wiki_urls[i]):
                wiki_urls[i].add('https://en.wikipedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_'), safe="(),'_-.:"))
        r['wikipedia_urls'] = '|'.join(sorted(wiki_urls[i]))
        r['n_texts_papyri'] = n_direct.get(i, 0)
        r['n_texts_papyri_incl_nome_region'] = n_all.get(i, 0)
        rows.append(r)
    cols = (['geo_id', 'uri', 'name_standard', 'name_latin', 'unicode_greek', 'unicode_egyptian', 'unicode_coptic',
             'responder_names', 'full_name', 'status', 'ethnicon', 'location', 'country', 'region', 'nomos_code',
             'provincia', 'lat', 'lon', 'coordinates', 'begin_date', 'end_date', 'begin_date_formatted',
             'end_date_formatted', 'pleiades_id', 'geonames', 'exact_matches', 'close_matches', 'broad_matches']
            + ['rel_' + p for p in partners]
            + ['wikipedia_urls', 'n_texts_papyri', 'n_texts_papyri_incl_nome_region', 'in_dump', 'in_sql'])
    write_tsv(out / 'trismegistos_places.tsv', rows, cols)

    if not a.skip_papyri:
        keep = set(ids)
        link_rows = [l for l in link_rows if l['geo_id'] in keep] if a.limit else link_rows
        write_tsv(out / 'trismegistos_place_texts.tsv', link_rows,
                  ['geo_id', 'tm_text_id', 'source', 'provenance_type', 'place_level', 'name_in_source'])
        write_tsv(out / 'trismegistos_texts.tsv', texts,
                  ['tm_text_id', 'sources', 'title', 'hgv_ids', 'ddb_hybrid', 'dclp_hybrid', 'ldab_ids', 'material',
                   'orig_place', 'geo_ids', 'orig_date', 'year_from', 'year_to', 'keywords', 'text_lang', 'edition_text',
                   'translation_en', 'translation_de', 'translation_other'])

    if not a.skip_wikipedia and not a.skip_api:
        allu = {u for us in wiki_urls.values() for u in us}
        wp = fetch_wikipedia(allu, cache / 'wikipedia.jsonl')
        wrows = []
        for i in ids:
            for u in sorted(wiki_urls.get(i, ())):
                d = wp.get(u) or {}
                pages = (d.get('query') or {}).get('pages') or [{}]
                pg = pages[0]
                wrows.append({'geo_id': i, 'wikipedia_url': u, 'lang': urllib.parse.urlparse(u).netloc.split('.')[0],
                              'title': pg.get('title', ''), 'missing': int('missing' in pg or 'extract' not in pg),
                              'text': pg.get('extract', '')})
        write_tsv(out / 'trismegistos_wikipedia.tsv', wrows, ['geo_id', 'wikipedia_url', 'lang', 'title', 'missing', 'text'])


if __name__ == '__main__':
    main()
