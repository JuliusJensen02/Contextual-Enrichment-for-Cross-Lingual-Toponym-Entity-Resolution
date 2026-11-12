"""Run the blocking methods on samples of our test sets and print PC / PQ / RR.

A test set is any number of datasets plus gold links between them. Every method is run on
every pair of datasets in the test set and scored per pair and in total.

Test sets (gold links in brackets):
  pleiades-tm  Pleiades, Trismegistos        [final_datasets/Pleades_Trismegistos/em.tsv]
  mehdie       Kima, Yaqut, al-Thurayya      [same_as rows of MEHDIE internal_links_*.csv]
  zh-ru        Wikidata Chinese, Russian     [final_datasets/Wikidata-zh-ru/em_zh_ru.tsv]

Each run samples `--n-gold` gold links, takes their records, and adds `--n-distractors` random
records without a gold link per dataset so the methods have something to reject. Every gold
link whose two records both ended up in the sample counts as gold.
The methods compare place names only; coordinates are a second criterion: every method's
candidates are also shown restricted to places within each `--max-km` threshold (pairs where a
record has no coordinates are kept).

  python run_candidate_generation.py                          # all test sets, all methods
  python run_candidate_generation.py --testset mehdie --methods PassJoin LM_kNN_search --show 3
  python make_phonetic_samples.py && python run_candidate_generation.py --phonetic phonetic_samples
"""
import argparse
import random
import re
import time
from itertools import combinations
from pathlib import Path

import pandas as pd

from candidate_generator import CandidateGenerator, within_distance
from methods import LMKNNSearch, MinHashLSH, PassJoin, QGrams, TfidfKNN

DATA = Path(__file__).resolve().parents[1] / "final_datasets"
PT_DIR = DATA / "Pleades_Trismegistos"
MEHDIE_DIR = DATA / "MEHDIE"
ZR_DIR = DATA / "Wikidata-zh-ru"

ALL_METHODS = ["Q_grams", "PassJoin", "MinHash_LSH", "TFIDF_kNN", "LM_kNN_search"]


# ---------------------------------------------------------------------------- loading
# Every loader returns (datasets, gold):
#   datasets = {dataset_name: {record_id: {"name": main name, "alt": [other names]}}}
#   gold     = {((dataset, id), (dataset, id)), ...}  one entry per known match
def read_tsv(path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)


def split_multi(*values, sep=r"\s*\|\s*") -> list[str]:
    out = []
    for v in values:
        out += [x.strip() for x in re.split(sep, v) if x.strip()]
    return list(dict.fromkeys(out))  # dedupe, keep order


def points(lat: str, lon: str) -> list[tuple]:
    """'31.66; 31.67', '35.1; 35.2' -> [(31.66, 35.1), (31.67, 35.2)]; empty -> []."""
    return [(float(a), float(b)) for a, b in zip(lat.split(";"), lon.split(";")) if a.strip() and b.strip()]


def strip_qualifier(title: str) -> str:
    """'Aethusa (island)' -> 'Aethusa'; keeps leading/inner brackets like '(H)Adriaticum'."""
    return re.sub(r"\s+\([^)]*\)$", "", title).strip()


def load_pleiades_tm():
    p = read_tsv(PT_DIR / "pleiades.tsv")
    t = read_tsv(PT_DIR / "trismegistos.tsv")
    em = read_tsv(PT_DIR / "em.tsv")
    datasets = {
        "pleiades": {r.pleiades_id: {"name": strip_qualifier(r.title),
                                     "alt": split_multi(r.names_romanized, r.names_greek, r.names_latin),
                                     "coords": points(r.lat, r.lon)}
                     for r in p.itertuples()},
        "trismegistos": {r.trismegistos_id: {"name": r.name_standard,
                                             "alt": split_multi(r.names_latin, r.names_greek, r.modern_name),
                                             "coords": points(r.lat, r.lon)}
                         for r in t.itertuples()},
    }
    gold = {(("pleiades", r.pleiades_id), ("trismegistos", r.trismegistos_id)) for r in em.itertuples()}
    return datasets, gold


def load_mehdie():
    datasets, owner = {}, {}
    for name in ("kima", "yaqut", "thurayya"):
        df = read_tsv(MEHDIE_DIR / "flattened" / f"mehdie_db_{name}_flat.tsv")
        datasets[name] = {r.id: {"name": r.title,
                                 "alt": split_multi(r.name_variants, sep=r"\s*[;،]\s*"),  # Arabic comma packs variants too
                                 "coords": points(r.lat, r.lon)}                         # can hold several points
                          for r in df.itertuples()}
        owner.update(dict.fromkeys(datasets[name], name))  # MEHDIE ids are unique across the three
    links = pd.read_csv(MEHDIE_DIR / "internal_links_kima_yaqut_thurayya.csv", dtype=str)
    # sorted(): a link listed in both directions counts once
    gold = {tuple(sorted(((owner[s], s), (owner[t], t))))
            for s, t in zip(links.source_place_id[links.link_type == "same_as"],
                            links.target_place_id[links.link_type == "same_as"])
            if s in owner and t in owner}
    return datasets, gold


def load_zh_ru():
    zh = read_tsv(ZR_DIR / "wikidata_zh.tsv")
    ru = read_tsv(ZR_DIR / "wikidata_ru.tsv")
    em = read_tsv(ZR_DIR / "em_zh_ru.tsv")
    # Treated like the other test sets, coordinates included. Caveat: both records of a gold pair
    # come from the same Wikidata item, so their coordinates are identical (3,247 of 3,263 pairs)
    # and the geo restriction can never drop a gold link here.
    datasets = {
        "chinese": {r.id: {"name": r.title,
                           "alt": split_multi(r.variants, r.wiki_title, sep=";") + split_multi(r.tgaz_name),
                           "coords": points(r.lat, r.lon)}
                    for r in zh.itertuples()},
        "russian": {r.id: {"name": r.title, "alt": split_multi(r.variants, r.wiki_title, sep=";"),
                           "coords": points(r.lat, r.lon)}
                    for r in ru.itertuples()},
    }
    gold = {(("chinese", r.id_1), ("russian", r.id_2)) for r in em.itertuples()}
    return datasets, gold


TESTSETS = {"pleiades-tm": load_pleiades_tm, "mehdie": load_mehdie, "zh-ru": load_zh_ru}


# ---------------------------------------------------------------------------- sampling & gold
def sample(datasets, gold, n_gold, n_distractors, rng):
    """Records of n_gold random gold links + n_distractors records without a link per dataset."""
    picked = rng.sample(sorted(gold), min(n_gold, len(gold)))
    keep = {name: set() for name in datasets}
    for end_1, end_2 in picked:
        for ds, rid in (end_1, end_2):
            keep[ds].add(rid)
    linked = {end for link in gold for end in link}
    for ds, records in datasets.items():
        unlinked = sorted(rid for rid in records if (ds, rid) not in linked)
        keep[ds] |= set(rng.sample(unlinked, min(n_distractors, len(unlinked))))
    sampled = {ds: {rid: datasets[ds][rid] for rid in sorted(ids)} for ds, ids in keep.items()}  # fixed order
    sub_gold = {link for link in gold if all(rid in sampled[ds] for ds, rid in link)}
    return sampled, sub_gold


def gold_for(gold, source, target) -> set:
    """Gold links between two datasets, as (source_id, target_id), whatever the link direction."""
    out = set()
    for (ds_1, id_1), (ds_2, id_2) in gold:
        if (ds_1, ds_2) == (source, target):
            out.add((id_1, id_2))
        elif (ds_1, ds_2) == (target, source):
            out.add((id_2, id_1))
    return out


# ---------------------------------------------------------------------------- running
def build_methods(args) -> list:
    """The blocking methods asked for with --methods, with their parameters set."""
    methods = [
        QGrams(q=3, t=0.6, max_keys=500),
        PassJoin(tau=args.tau),
        MinHashLSH(threshold=0.3),
        TfidfKNN(k=args.k),
        LMKNNSearch(model=args.model, k=args.k),
    ]
    by_name = {m.name: m for m in methods}
    return [by_name[name] for name in args.methods]


def describe(rec) -> str:
    return " / ".join([rec["name"]] + rec["alt"][:3])


def add_phonetic(datasets, path):
    """Attach record["phonetic"] = encodings of its names, from a name -> phonetic TSV."""
    codes = dict(zip(*read_tsv(path)[["name", "phonetic"]].T.values))
    missing = 0
    for records in datasets.values():
        for r in records.values():
            names = [n for n in [r["name"], *r["alt"]] if n]
            missing += sum(n.replace("\t", " ") not in codes for n in names)
            r["phonetic"] = [codes[n.replace("\t", " ")] for n in names if n.replace("\t", " ") in codes]
    if missing:
        print(f"warning: {missing} names have no phonetic encoding in {path} (re-run make_phonetic_samples.py?)")


def run_testset(testset, methods, args):
    datasets, gold = sample(*TESTSETS[testset](), args.n_gold, args.n_distractors, random.Random(args.seed))
    pairs = list(combinations(datasets, 2))
    gold_by_pair = {p: gold_for(gold, *p) for p in pairs}
    sizes = ", ".join(f"{ds} {len(recs)}" for ds, recs in datasets.items())
    print(f"\n=== {testset}: {sizes} records; {len(gold)} gold links; {len(pairs)} dataset pair(s)")

    if args.phonetic:
        add_phonetic(datasets, Path(args.phonetic) / f"{testset}.tsv")
    thresholds = [None, *args.max_km]

    # Upper bound set by the geo restriction alone: gold links it keeps at each threshold.
    n_gold = sum(len(g) for g in gold_by_pair.values())
    with_coords = sum(bool(datasets[s][a].get("coords") and datasets[t][b].get("coords"))
                      for (s, t), g in gold_by_pair.items() for a, b in g)
    print(f"gold links with coordinates on both sides: {with_coords}/{n_gold}. Gold links kept by the geo "
          f"restriction alone: " + ", ".join(
              f"{km:g} km {sum(len(within_distance(g, datasets[s], datasets[t], km)) for (s, t), g in gold_by_pair.items()) / n_gold:.3f}"
              for km in args.max_km))

    print(f"{'method':14s} {'geo':>9s} {'pair':24s} {'gold':>5s} {'PC':>6s} {'PQ':>6s} {'RR':>7s} {'|C|':>8s} {'sec':>7s}")
    for method in methods:
        m = method.name
        # max_km=None: each method runs once unrestricted, and the geo restriction is applied per
        # threshold below (the class default of 50 km would otherwise apply already).
        gen = CandidateGenerator(datasets, method, phonetic_attrs=["phonetic"] if args.phonetic else None,
                                 max_km=None)
        t0 = time.time()
        try:
            results = gen.all_pairs()
        except ImportError as e:
            print(f"{m:14s} skipped: {e}")
            continue
        seconds = f"{time.time() - t0:7.2f}"
        for km in thresholds:
            geo = "none" if km is None else f"{km:g} km"
            restricted = results if km is None else {(s, t): within_distance(c, datasets[s], datasets[t], km) for (s, t), c in results.items()}
            for line in report(restricted, gold_by_pair, datasets, per_pair=args.per_pair or len(results) == 1):
                print(f"{m:14s} {geo:>9s} {line} {seconds}")
                seconds = ""  # time only on the method's first line
            if args.show and km is None:
                for (s, t), cands in results.items():
                    for a, b in sorted(gold_by_pair[(s, t)] - cands)[: args.show]:
                        print(f"{'':24s} missed: {describe(datasets[s][a])}  <->  {describe(datasets[t][b])}")


def report(results, gold_by_pair, datasets, per_pair) -> list[str]:
    """Table lines: one per dataset pair (if per_pair), plus an ALL PAIRS total if there are several."""
    lines, found, n_cands, possible = [], 0, 0, 0
    for (s, t), cands in results.items():
        g = gold_by_pair[(s, t)]
        r = CandidateGenerator.evaluate(cands, g, len(datasets[s]), len(datasets[t]))
        if per_pair:
            lines.append(f"{s + '-' + t:24s} {row(len(g), r['PC'] if g else None, r['PQ'], r['RR'], len(cands))}")
        found, n_cands = found + len(cands & g), n_cands + len(cands)
        possible += len(datasets[s]) * len(datasets[t])
    if len(results) > 1:
        n_gold = sum(len(g) for g in gold_by_pair.values())
        lines.append(f"{'ALL PAIRS':24s} {row(n_gold, found / n_gold if n_gold else None, found / n_cands if n_cands else 0, 1 - n_cands / possible, n_cands)}")
    return lines


def row(n_gold, pc, pq, rr, n_cands) -> str:
    pc = f"{pc:6.3f}" if pc is not None else f"{'-':>6s}"  # "-" when a pair has no gold links
    return f"{n_gold:5d} {pc} {pq:6.3f} {rr:7.4f} {n_cands:8,d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", choices=[*TESTSETS, "all"], default="all")
    ap.add_argument("--methods", nargs="+", choices=ALL_METHODS, default=ALL_METHODS)
    ap.add_argument("--n-gold", type=int, default=200, help="gold links to sample per test set")
    ap.add_argument("--n-distractors", type=int, default=300, help="extra unlinked records per dataset")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--tau", type=int, default=1, help="PassJoin edit-distance threshold")
    ap.add_argument("--k", type=int, default=3, help="neighbours per name for the kNN methods")
    ap.add_argument("--model", default="sentence-transformers/LaBSE", help="encoder for LM_kNN_search")
    ap.add_argument("--show", type=int, default=0, help="print N missed gold pairs per method and pair")
    ap.add_argument("--phonetic", metavar="DIR", default=None,
                    help="folder with <testset>.tsv (name -> phonetic); the letter-based methods then "
                         "compare the phonetic encodings instead of the names (LM_kNN_search keeps the names)")
    ap.add_argument("--max-km", nargs="*", type=float, default=[50],
                    help="geo restriction thresholds in km, e.g. --max-km 10 25 50 100 250 to compare "
                         "(no restriction is always shown too)")
    ap.add_argument("--per-pair", action="store_true", help="also show every dataset pair, not only the total")
    args = ap.parse_args()

    methods = build_methods(args)  # built once, so the language model is loaded only once
    for testset in (TESTSETS if args.testset == "all" else [args.testset]):
        run_testset(testset, methods, args)


if __name__ == "__main__":
    main()
