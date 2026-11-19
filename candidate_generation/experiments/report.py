"""Collects the results of run_all.py: merges the CSVs into results/ and prints the tables that
pipeline_explained.html shows.

  python experiments/report.py              # print the tables, write the merged CSVs
  python experiments/report.py --compare    # also compare with the CSVs from the previous run
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from common import CANDIDATE_GENERATION, LABELS, RERUN, load

RESULTS = CANDIDATE_GENERATION / "results"
SETS = list(LABELS)
TITLE_NAMES = {"labse": "LM_kNN_search", "edit": "PassJoin", "tfidf:2-3": "TFIDF_kNN", "jaccard:3": "MinHash_LSH",
               "qgram:3": "Q_grams", "none": "No title score, phonetic only"}
PHONETIC_NAMES = {"tfidf:2-3": "TFIDF_kNN, piece lengths 2-3", "tfidf:1-3": "TFIDF_kNN, piece lengths 1-3",
                  "tfidf:2-4": "TFIDF_kNN, piece lengths 2-4", "jaccard:2": "MinHash_LSH, piece length 2",
                  "jaccard:3": "MinHash_LSH, piece length 3", "qgram:2": "Q_grams, piece length 2",
                  "qgram:3": "Q_grams, piece length 3", "edit": "PassJoin", "jaro": "Jaro-Winkler (no method)",
                  "none": "none"}


def read(folder) -> list[dict]:
    rows = []
    for path in sorted((RERUN / folder).glob("*.csv")):
        with path.open(encoding="utf8", newline="") as file:
            rows.extend(csv.DictReader(file))
    return rows


def write(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pc(value) -> str:
    return f"{float(value):.3f}"


def table(head, rows):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for row in rows:
        print("| " + " | ".join(str(cell) for cell in row) + " |")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    summary = {}

    # ------------------------------------------------------------------ test sets
    print("## Test sets\n")
    rows = []
    for name in SETS:
        test_set = load(name)
        sizes = {d.label: len(d) for d in test_set.datasets}
        possible = sum(len(test_set.dataset(s)) * len(test_set.dataset(t)) for s, t in test_set.pairs)
        coordinates = {d.label: sum(bool(p) for p in d.coordinates.values()) for d in test_set.datasets}
        summary.setdefault("sets", {})[name] = {"records": sizes, "links": len(test_set.links), "pairs": possible,
                                                "with_coordinates": coordinates}
        rows.append([LABELS[name], ", ".join(f"{k} {v:,}" for k, v in sizes.items()), f"{len(test_set.links):,}",
                     f"{possible:,}", ", ".join(f"{k} {v:,}" for k, v in coordinates.items())])
    table(["Test set", "Records", "Links", "Possible pairs", "Records with coordinates"], rows)

    # ------------------------------------------------------------------ step 1
    print("## Step 1: geo threshold\n")
    geo = {name: json.loads((RERUN / "step1" / f"{name}.json").read_text(encoding="utf8")) for name in SETS
           if (RERUN / "step1" / f"{name}.json").is_file()}
    summary["step1"] = geo
    table(["Test set", "Fitted (per start)", "Exhaustive", "Farthest link", "Links without coordinates",
           "Links within 50/90/95/99 %"],
          [[LABELS[n], " / ".join(f"{r['km']:.2f}" for r in g["fitted"]), f"{g['exhaustive']['km']:.2f}",
            f"{g['farthest_link_km']:.2f}", f"{g['links_without_coordinates']} of {g['links']}",
            " / ".join(f"{v:.2f}" for v in g["link_percentiles_km"].values())] for n, g in geo.items()])
    for name, g in geo.items():
        print(f"{LABELS[name]}: {g['possible_pairs']:,} possible pairs, {g['pairs_always_kept']:,} always kept\n")
        table(["T (km)", "PC", "RR", "|C| all", "PC geo", "RR geo", "|C| geo"],
              [[f"{r['km']:g}", pc(r["PC"]), f"{r['RR']:.5f}", f"{r['candidates']:,}", pc(r["PC_geo"]),
                f"{r['RR_geo']:.5f}", f"{r['candidates_geo']:,}"] for r in g["grid"]])

    # ------------------------------------------------------------------ step 2
    print("## Step 2: the letter-based methods on title_ipa, behind the 100 km filter\n")
    step2 = read("step2")
    if step2:
        write(RESULTS / "sweep_parameters.csv", step2)
    totals = {}  # (testset, method, params) -> row: the ALL PAIRS row, or the only pair
    for row in step2:
        if row["PC"]:  # the CSV holds PC with 4 decimals: back to the exact share of the links
            row = dict(row, PC=round(float(row["PC"]) * int(row["truth"])) / int(row["truth"]))
        key = (row["testset"], row["method"], row["params"])
        if row["pair"] == "ALL PAIRS" or key not in totals:
            totals[key] = row
    best = {}
    for (testset, method, params), row in totals.items():
        current = best.get((testset, method))
        rank = (float(row["PC"]), -int(row["candidates"]))
        if current is None or rank > (float(current["PC"]), -int(current["candidates"])):
            best[testset, method] = row
    methods = ["TFIDF_kNN", "MinHash_LSH", "Q_grams", "PassJoin"]
    table(["Method"] + [f"{LABELS[s]} best PC (setting, |C|)" for s in SETS],
          [[m] + [f"{pc(best[s, m]['PC'])} ({best[s, m]['params']}; {int(best[s, m]['candidates']):,})"
                  if (s, m) in best else "-" for s in SETS] for m in methods])
    summary["step2_best"] = {f"{s}|{m}": {"PC": float(r["PC"]), "params": r["params"], "candidates": int(r["candidates"])}
                             for (s, m), r in best.items()}
    for method in methods:
        settings = sorted({p for (_, m, p) in totals if m == method})
        table([method] + [f"{LABELS[s]} PC" for s in SETS] + [f"{LABELS[s]} |C|" for s in SETS],
              [[p] + [pc(totals[s, method, p]["PC"]) if (s, method, p) in totals else "did not finish" for s in SETS]
               + [f"{int(totals[s, method, p]['candidates']):,}" if (s, method, p) in totals else "" for s in SETS]
               for p in settings])
    status = json.loads((RERUN / "status.json").read_text(encoding="utf8")) if (RERUN / "status.json").is_file() else {}
    summary["problems"] = status.get("problems", [])
    if summary["problems"]:
        print("Did not finish:", ", ".join(f"{p['id']} ({p['state']})" for p in summary["problems"]), "\n")

    # ------------------------------------------------------------------ steps 3 and 4
    combos = read("step3") + read("step4")
    if combos:
        write(RESULTS / "sweep_combination.csv", combos)
    value = {}  # (testset, title, phonetic, weight, k, min_score) -> (PC, candidates)
    for r in combos:
        value[r["testset"], r["title_method"], r["phonetic_method"], float(r["title_weight"]), int(r["k"]),
              r["min_score"]] = (int(r["found"]) / int(r["truth"]), int(r["candidates"]))  # exact, not the rounded PC

    def get(testset, title, phonetic, weight, k=5, min_score=""):
        return value.get((testset, title, phonetic, weight, k, min_score))

    def cells(title, phonetic, weight, k=5):
        found = [get(s, title, phonetic, weight, k) for s in SETS]
        if any(f is None for f in found):
            return ["-"] * (len(SETS) + 1)
        return [pc(f[0]) for f in found] + [pc(sum(f[0] for f in found) / len(found))]

    print("## Step 3: each method as the title score (w = 0.5, k = 5; phonetic score TFIDF_kNN 2-3)\n")
    rows = [[TITLE_NAMES[t]] + (cells(t, "tfidf:2-3", 0.5) if t != "none" else cells("none", "tfidf:2-3", 0.0))
            for t in ("labse", "edit", "tfidf:2-3", "jaccard:3", "qgram:3", "none")]
    table(["Title score from"] + [LABELS[s] for s in SETS] + ["Mean"], rows)
    summary["step3"] = rows

    print("## Step 4: weight on the title score (LM_kNN_search + TFIDF_kNN 2-3), mean PC over the test sets\n")
    weights = [w / 10 for w in range(11)]
    rows = [[f"{w:.1f}"] + [cells("labse", "tfidf:2-3", w, k)[-1] for k in (1, 3, 5, 10)]
            + cells("labse", "tfidf:2-3", w, 5)[:-1] for w in weights]
    table(["w", "k=1", "k=3", "k=5", "k=10"] + [f"{LABELS[s]} k=5" for s in SETS], rows)
    summary["step4_weights"] = rows

    print("## Step 4: combinations at w = 0.5, k = 5\n")
    rows = [["LM_kNN_search (LaBSE)", PHONETIC_NAMES[p]] + (cells("labse", p, 0.5) if p != "none" else cells("labse", p, 1.0))
            for p in PHONETIC_NAMES]
    rows += [[TITLE_NAMES[t], PHONETIC_NAMES["tfidf:2-3"]] + cells(t, "tfidf:2-3", 0.5)
             for t in ("edit", "tfidf:2-3", "jaccard:3", "qgram:3")]
    table(["Title score from", "Phonetic score from"] + [LABELS[s] for s in SETS] + ["Mean"], rows)
    summary["step4_combinations"] = rows
    sizes = {p: [get(s, "labse", p, 0.5) for s in SETS] for p in PHONETIC_NAMES if p != "none"}
    table(["Phonetic score from"] + [f"{LABELS[s]} |C|" for s in SETS],
          [[PHONETIC_NAMES[p]] + [f"{f[1]:,}" if f else "-" for f in found] for p, found in sizes.items()])

    print("## Step 4: each phonetic method at its best weight (by mean PC at k = 5)\n")
    rows = []
    for p in PHONETIC_NAMES:
        if p == "none":
            continue
        scored = [(float(cells("labse", p, w)[-1]), w) for w in weights if cells("labse", p, w)[-1] != "-"]
        if scored:
            top, w = max(scored, key=lambda s: (s[0], -abs(s[1] - 0.5)))
            rows.append([PHONETIC_NAMES[p], f"{w:.1f}"] + [cells("labse", p, w, k)[-1] for k in (1, 3, 5, 10)]
                        + [" / ".join(cells("labse", p, w)[:-1])])
    table(["Phonetic score from", "Best w", "k=1", "k=3", "k=5", "k=10", "k=5 per test set"], rows)
    summary["step4_best_weight"] = rows

    print("## Step 4: k and minimum score (LM_kNN_search + TFIDF_kNN 2-3, w = 0.5)\n")
    rows = [[f"k={k}"] + [f"{pc(f[0])} ({f[1]:,})" if f else "-" for f in (get(s, "labse", "tfidf:2-3", 0.5, k) for s in SETS)]
            for k in (1, 3, 5, 10)]
    rows += [[f"k=5, score >= {m}"] + [f"{pc(f[0])} ({f[1]:,})" if f else "-"
                                       for f in (get(s, "labse", "tfidf:2-3", 0.5, 5, m) for s in SETS)]
             for m in ("0.2", "0.3", "0.35", "0.4", "0.5")]
    table(["Setting"] + [f"{LABELS[s]} PC (|C|)" for s in SETS], rows)
    summary["step4_k"] = rows

    (RERUN / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf8")

    if args.compare:
        compare(totals, value)


def compare(totals, value):
    """MEHDIE and zh-ru did not change, so their numbers should match the previous run (git show
    HEAD:candidate_generation/results/...)."""
    import io
    import subprocess

    def previous(name):
        text = subprocess.run(["git", "show", f"HEAD:candidate_generation/results/{name}"], capture_output=True,
                              cwd=CANDIDATE_GENERATION, check=True).stdout.decode("utf8")
        return list(csv.DictReader(io.StringIO(text)))

    print("## Compared with the previous run (unchanged test sets)\n")
    old = {}
    for row in previous("sweep_parameters.csv"):
        key = (row["testset"], row["method"], row["params"])
        if row["pair"] == "ALL PAIRS" or key not in old:
            old[key] = row
    differences = defaultdict(list)
    for key, row in old.items():
        if key[0] != "pleiades-tm" and key in totals:
            differences[key[0]].append((abs(float(row["PC"]) - float(totals[key]["PC"])),
                                        abs(int(row["candidates"]) - int(totals[key]["candidates"])), key))
    for testset, found in differences.items():
        worst = max(found)
        exact = sum(d[0] == 0 and d[1] == 0 for d in found)
        print(f"step 2 {testset}: {len(found)} settings compared, {exact} identical, largest PC difference "
              f"{worst[0]:.4f} ({worst[2][1]} {worst[2][2]}), largest |C| difference {max(d[1] for d in found):,}")

    methods = {("TFIDF_kNN", "pieces 2-3"): "tfidf:2-3", ("TFIDF_kNN", "pieces 1-3"): "tfidf:1-3",
               ("TFIDF_kNN", "pieces 2-4"): "tfidf:2-4", ("MinHash_LSH", "n=2"): "jaccard:2",
               ("MinHash_LSH", "n=3"): "jaccard:3", ("Q_grams", "q=2"): "qgram:2", ("Q_grams", "q=3"): "qgram:3"}
    labels = {"MEHDIE": "mehdie", "PLEIADES_TRISMEGISTOS": "pleiades-tm", "WIKIDATA_ZH_RU": "zh-ru"}
    differences = defaultdict(list)
    unknown = set()
    for row in previous("sweep_combination.csv"):
        testset = labels.get(row["testset"], row["testset"])
        method = methods.get((row["phonetic_method"], row["params"]),
                             {"PassJoin": "edit", "title only": "none"}.get(row["phonetic_method"]))
        if method is None:
            unknown.add((row["phonetic_method"], row["params"]))
            continue
        new = value.get((testset, "labse", method, float(row["title_weight"]), int(row["k"]), ""))
        if new and testset != "pleiades-tm":
            differences[testset, method].append((abs(float(row["PC"]) - new[0]), abs(int(row["candidates"]) - new[1])))
    for (testset, method), found in sorted(differences.items()):
        print(f"step 4 {testset} {method:10s}: {len(found)} rows, mean PC difference "
              f"{sum(d[0] for d in found) / len(found):.4f}, largest {max(d[0] for d in found):.4f}, "
              f"largest |C| difference {max(d[1] for d in found):,}")
    if unknown:
        print("not compared (unknown labels in the old file):", sorted(unknown))


if __name__ == "__main__":
    main()
