"""Step 1 of the pipeline: which distance threshold.

Coordinates only. A pair is a candidate if its two places are at most T km apart (the closest
two points if a record has several). Pairs where a record has no coordinates are always kept.

  - T is fitted by gradient descent (Adam, 800 steps) from 1, 10, 100 and 1000 km. A hard
    cut-off has no gradient, so during fitting it is a sigmoid in log-distance that is sharpened
    step by step.
  - Objective: the harmonic mean of PC and RR, both measured on the pairs where both records have
    coordinates ("geo pairs"), the only pairs the threshold decides about.
  - As a check the best threshold is also found by trying every one that matters (exhaustive).

  python experiments/geo_threshold.py --testset pleiades-tm --out step1_geo_pleiades-tm.json

For the gradient descent the distances of the geo pairs are summarised in a fine histogram over
log-distance (6000 bins): tens of millions of pairs would otherwise be scored 800 times.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from common import CHUNK, load
from pipeline import _distances, _points

GRID = [1, 5, 10, 25, 50, 100, 250, 500, 1000]
STARTS = [1, 10, 100, 1000]
MIN_KM, MAX_KM_ON_EARTH = 1e-3, 25_000


def harmonic(pc, rr):
    return 2 * pc * rr / (pc + rr) if pc + rr else 0.0


def fit(link_km: np.ndarray, pair_km_sorted: np.ndarray, start: float, steps=800) -> float:
    """Gradient descent on log T. Returns the fitted threshold in km."""
    import torch

    edges = np.logspace(np.log10(MIN_KM), np.log10(MAX_KM_ON_EARTH), 6001)
    counts = np.diff(np.searchsorted(pair_km_sorted, edges, side="right"))
    counts[0] += np.searchsorted(pair_km_sorted, edges[0], side="right")  # pairs closer than 1 m
    used = counts > 0
    pair_log = torch.tensor(np.log(np.sqrt(edges[:-1] * edges[1:]))[used])
    pair_weight = torch.tensor(counts[used] / counts.sum())
    link_log = torch.tensor(np.log(np.clip(link_km, MIN_KM, MAX_KM_ON_EARTH)))

    log_t = torch.tensor(float(np.log(start)), dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.Adam([log_t], lr=0.05)
    for step in range(steps):
        sharpness = 2 * (50 / 2) ** (step / (steps - 1))  # from 2 to 50
        pc = torch.sigmoid(sharpness * (log_t - link_log)).mean()
        rr = 1 - (torch.sigmoid(sharpness * (log_t - pair_log)) * pair_weight).sum()
        loss = -2 * pc * rr / (pc + rr)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return float(torch.exp(log_t.detach()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    start = time.time()
    test_set = load(args.testset)

    pair_km, link_km, possible, links_total = [], [], 0, 0
    for source, target in test_set.pairs:
        A, B = test_set.dataset(source), test_set.dataset(target)
        points_a, points_b = _points(A), _points(B)
        row_a, row_b = ({rid: i for i, rid in enumerate(d.ids)} for d in (A, B))
        links = sorted((row_a[a], row_b[b]) for a, b in test_set.links_between(source, target))
        links_total += len(links)
        possible += len(A) * len(B)
        for c in range(0, len(A), CHUNK):
            km = _distances(points_a[c:c + CHUNK], points_b)
            pair_km.append(km[~np.isnan(km)])
            link_km.extend(float(km[i - c, j]) for i, j in links if c <= i < c + CHUNK)
        print(f"distances {A.label}-{B.label} done after {time.time() - start:.0f} s", flush=True)
    pair_km = np.sort(np.concatenate(pair_km))
    link_km = np.array(link_km)
    link_km = np.sort(link_km[~np.isnan(link_km)])           # the links with coordinates on both sides
    links_without = links_total - len(link_km)
    always_kept = possible - len(pair_km)

    def metrics(t) -> dict:
        kept_pairs = int(np.searchsorted(pair_km, np.float32(t), side="right"))
        kept_links = int(np.searchsorted(link_km, t, side="right"))
        candidates = always_kept + kept_pairs
        pc_geo = kept_links / len(link_km) if len(link_km) else 0.0
        rr_geo = 1 - kept_pairs / len(pair_km) if len(pair_km) else 0.0
        return {"km": float(t), "PC": (links_without + kept_links) / links_total,
                "PQ": (links_without + kept_links) / candidates if candidates else 0.0,
                "RR": 1 - candidates / possible, "candidates": candidates,
                "PC_geo": pc_geo, "RR_geo": rr_geo, "candidates_geo": kept_pairs,
                "objective": harmonic(pc_geo, rr_geo)}

    # Exhaustive: PC only changes at the distance of a link, so only those thresholds can be best.
    exhaustive = max((metrics(t) for t in np.unique(link_km)), key=lambda r: (r["objective"], -r["km"]))
    fitted = [{"start_km": s, **metrics(fit(link_km, pair_km, s))} for s in STARTS]
    best_fit = max(fitted, key=lambda r: r["objective"])
    print("fitted from each start:", ", ".join(f"{r['start_km']} -> {r['km']:.2f} km" for r in fitted), flush=True)

    result = {
        "testset": args.testset, "links": links_total, "links_without_coordinates": links_without,
        "possible_pairs": possible, "pairs_always_kept": always_kept, "geo_pairs": int(len(pair_km)),
        "farthest_link_km": float(link_km[-1]),
        "link_percentiles_km": {str(q): float(np.percentile(link_km, q)) for q in (50, 90, 95, 99)},
        "fitted": fitted, "fitted_best": best_fit, "exhaustive": exhaustive,
        "grid": [metrics(t) for t in sorted({*GRID, best_fit["km"]})],
        "seconds": round(time.time() - start, 1),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf8")
    print(f"fitted {best_fit['km']:.2f} km, exhaustive {exhaustive['km']:.2f} km, "
          f"farthest link {result['farthest_link_km']:.2f} km", flush=True)


if __name__ == "__main__":
    main()
