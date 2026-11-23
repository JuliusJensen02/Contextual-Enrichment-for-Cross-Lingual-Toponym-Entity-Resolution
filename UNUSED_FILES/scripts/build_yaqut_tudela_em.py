#!/usr/bin/env python3
"""Derive a Yaqut <-> Tudela ground truth for MEHDIE by transitive closure.

No MEHDIE testset pairs Yaqut with Tudela directly. This links them through
the other sources: the five em.tsv files, Tudela's own Kima IDs (the K... id
and Kima URLs in `matches`), and Wikidata IDs shared by Kima and Tudela
records. Each Yaqut record is matched to every Tudela record reachable from
it. Tudela records are endpoints only, never bridges, because some Tudela
records share a wrong Wikidata ID (e.g. Gebal and Gebal-the-other).

Output follows em.tsv (id_1 = Yaqut, id_2 = Tudela) plus `hops` and `path`.

Usage: python build_yaqut_tudela_em.py [mehdie_dir] [out_file]
"""
import csv, re, sys, collections
from pathlib import Path
csv.field_size_limit(10**9)
M = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / 'datasets/MEHDIE')
def rd(p): return list(csv.DictReader(open(M/p, encoding='utf-8-sig', newline=''), delimiter='\t'))

title, adj = {}, collections.defaultdict(dict)
def edge(a, b, why):
    adj[a].setdefault(b, why); adj[b].setdefault(a, why)

for src, files in {'yaqut': ['YaqutSham_KimaSham/YaqutSham.tsv', 'YaqutAndalusMagrebKima-KimaMagrebAndalusMapped/Yaqut_306.tsv'],
                   'kima': ['YaqutSham_KimaSham/KimaSham.tsv', 'YaqutAndalusMagrebKima-KimaMagrebAndalusMapped/Kima_303.tsv'],
                   'thurayya': ['TudelaThurayya/althurayya_283.tsv', 'KimaShamThurayyaSham/ThurayaSham_295.tsv'],
                   'tudela': ['TudelaThurayya/Tudela_257.tsv'], 'damast': ['DamastTudela/damast_315.tsv']}.items():
    for f in files:
        for r in rd(f):
            title[(src, r['id'])] = r['title']
            if src == 'kima':
                for q in re.findall(r'wikidata\.org/wiki/(Q\d+)', r['matches']):
                    edge((src, r['id']), ('wd', q), 'wikidata')
            if src == 'tudela':
                ks = set(re.findall(r'geo-kima\.org/Place/(\d+)', r['matches']))
                if r['id'].startswith('K'): ks.add(r['id'][1:].rstrip('*'))
                for k in ks: edge((src, r['id']), ('kima', k), 'tudela-kima-id')
                qs = set(re.findall(r'(?:wd:|wikidata\.org/wiki/)(Q\d+)', r['matches']))
                if r['id'].startswith('Q'): qs.add(r['id'])
                for q in qs: edge((src, r['id']), ('wd', q), 'wikidata')

for d, s1, s2 in [('YaqutSham_KimaSham', 'yaqut', 'kima'), ('YaqutAndalusMagrebKima-KimaMagrebAndalusMapped', 'yaqut', 'kima'),
                  ('KimaShamThurayyaSham', 'kima', 'thurayya'), ('TudelaThurayya', 'tudela', 'thurayya'), ('DamastTudela', 'damast', 'tudela')]:
    for r in rd(f'{d}/em.tsv'):
        edge((s1, r['id_1']), (s2, r['id_2']), f'em:{d}')

def lab(n): return f"{n[0]}:{n[1]}" + (f"({title[n]})" if n in title else '')
out = []
for y in sorted(n for n in title if n[0] == 'yaqut'):
    if y not in adj: continue
    prev, q = {y: None}, collections.deque([y])  # BFS -> shortest path to each Tudela node
    while q:
        n = q.popleft()
        if n[0] == "tudela": continue  # Tudela is an endpoint, never a bridge
        for m in adj[n]:
            if m not in prev: prev[m] = n; q.append(m)
    for t in prev:
        if t[0] != 'tudela': continue
        path, n = [], t
        while n: path.append(n); n = prev[n]
        path.reverse()
        steps = ' > '.join(lab(path[0]) if i == 0 else f"-[{adj[path[i-1]][p]}]-> {lab(p)}" for i, p in enumerate(path))
        out.append((y[1], title[y], t[1], title[t], 'true', len(path) - 1, steps))

w = csv.writer(open(sys.argv[2] if len(sys.argv) > 2 else M / 'YaqutTudela/em.tsv', 'w', encoding='utf-8', newline=''), delimiter='\t', lineterminator='\n')
w.writerow(['id_1', 'title_1', 'id_2', 'title_2', 'judgement', 'hops', 'path'])
w.writerows(out)
print(len(out), 'pairs;', len({o[0] for o in out}), 'yaqut;', len({o[2] for o in out}), 'tudela')
