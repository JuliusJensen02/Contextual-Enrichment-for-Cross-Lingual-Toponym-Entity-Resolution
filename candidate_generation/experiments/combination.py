"""Steps 3 and 4 of the pipeline with any title score and any phonetic score.

Behind the 100 km filter:  score = w * title score + (1 - w) * phonetic score.
Every record keeps its k best-scoring records on the other side (score > 0); a pair is a
candidate if either side keeps it. Every weight from 0 to 1 in steps of 0.1 and every k is
scored in one go and written to a CSV, one row per (weight, k).

  --title     labse (the titles as written) or a letter score on the titles transliterated to
              Latin letters with anyascii: tfidf:2-3, jaccard:3, qgram:3, edit; or none
  --phonetic  a letter score on title_ipa: tfidf:2-3, jaccard:2, qgram:2, edit, jaro, ...; or none

  python experiments/combination.py --testset pleiades-tm --title labse --phonetic tfidf:2-3 --out x.csv

Needs prepare.py to have run for the test set (geo filter and LaBSE embeddings).
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np

from common import CHUNK, MAX_KM, embedding_path, far_mask, load  # first: sets up sys.path
from candidate_generator import CandidateGenerator  # noqa: I001
from scores import Embedding, letter_scorer

KS = [1, 3, 5, 10]
TENTHS = range(11)                       # the weight on the title score, in tenths
MIN_SCORES = [0.2, 0.3, 0.35, 0.4, 0.5]  # tried at w = 0.5, k = 5 only
COLUMNS = ["testset", "title_method", "phonetic_method", "title_weight", "k", "min_score", "truth", "found",
           "PC", "candidates", "seconds"]


def ipa_strings(dataset) -> list[str]:
    """The phonetic title of every record, as pipeline.py reads it (the first encoding)."""
    return [(record.phonetic or [""])[0].lower() for record in dataset]


def latin_titles(dataset) -> list[str]:
    """The title of every record in Latin letters, normalised like the names the methods get."""
    from anyascii import anyascii

    return [CandidateGenerator._normalize(anyascii(record.title)) for record in dataset]


def scorers(testset, A, B, title, phonetic):
    if title == "none":
        title_score = None
    elif title == "labse":
        title_score = Embedding(np.load(embedding_path(testset, A)), np.load(embedding_path(testset, B)))
    else:
        title_score = letter_scorer(title, latin_titles(A), latin_titles(B))
    phonetic_score = None if phonetic == "none" else letter_scorer(phonetic, ipa_strings(A), ipa_strings(B))
    return title_score, phonetic_score


def top_pairs(title_score, phonetic_score, far, tenths, kmax):
    """For every weight: each source record's kmax best target records and each target record's
    kmax best source records, best first. {tenth: (row_cols, row_scores, col_rows, col_scores)}
    with shapes [n, kmax'] and [kmax', m]."""
    n, m = far.shape
    k_rows, k_cols = min(kmax, m), min(kmax, n)
    rows = {w: ([], []) for w in tenths}
    cols = {w: (np.zeros((0, m), np.int64), np.full((0, m), -np.inf, np.float32)) for w in tenths}
    for c in range(0, n, CHUNK):
        stop = min(n, c + CHUNK)
        t = title_score.chunk(c, stop) if title_score else None
        p = phonetic_score.chunk(c, stop) if phonetic_score else None
        blocked = np.asarray(far[c:stop])
        for w in tenths:
            weight = np.float32(w / 10)
            score = p.copy() if t is None else t.copy() if p is None else weight * t + (1 - weight) * p
            score[blocked] = -np.inf
            # each source record's best target records
            part = np.argpartition(-score, k_rows - 1, axis=1)[:, :k_rows]
            values = np.take_along_axis(score, part, 1)
            order = np.argsort(-values, axis=1)
            rows[w][0].append(np.take_along_axis(part, order, 1))
            rows[w][1].append(np.take_along_axis(values, order, 1))
            # each target record's best source records: merge this chunk into the best so far
            k_chunk = min(k_cols, stop - c)
            part = np.argpartition(-score, k_chunk - 1, axis=0)[:k_chunk]
            best_row = np.vstack([cols[w][0], part + c])
            best_score = np.vstack([cols[w][1], np.take_along_axis(score, part, 0)])
            if best_score.shape[0] > k_cols:
                keep = np.argpartition(-best_score, k_cols - 1, axis=0)[:k_cols]
                best_row, best_score = np.take_along_axis(best_row, keep, 0), np.take_along_axis(best_score, keep, 0)
            cols[w] = (best_row, best_score)
    out = {}
    for w in tenths:
        order = np.argsort(-cols[w][1], axis=0)
        out[w] = (np.vstack(rows[w][0]), np.vstack(rows[w][1]),
                  np.take_along_axis(cols[w][0], order, 0), np.take_along_axis(cols[w][1], order, 0))
    return out


def kept(top, k, m, min_score=0.0) -> np.ndarray:
    """The candidate pairs at this k as codes (source row * m + target row): union of both sides."""
    row_cols, row_scores, col_rows, col_scores = top
    n = row_cols.shape[0]
    by_row = (np.arange(n)[:, None] * m + row_cols[:, :k])[(row_scores[:, :k] > 0) & (row_scores[:, :k] >= min_score)]
    by_col = (col_rows[:k] * m + np.arange(m)[None, :])[(col_scores[:k] > 0) & (col_scores[:k] >= min_score)]
    return np.unique(np.concatenate([by_row, by_col]))


def run(testset, title, phonetic, max_km=MAX_KM) -> list[dict]:
    start = time.time()
    test_set = load(testset)
    tenths = [0] if title == "none" else [10] if phonetic == "none" else list(TENTHS)
    settings = [(w, k, "") for w in tenths for k in KS] + [(5, 5, s) for s in MIN_SCORES if 5 in tenths]
    found, candidates, truth = dict.fromkeys(settings, 0), dict.fromkeys(settings, 0), 0
    for source, target in test_set.pairs:
        A, B = test_set.dataset(source), test_set.dataset(target)
        m = len(B)
        row_a, row_b = ({rid: i for i, rid in enumerate(d.ids)} for d in (A, B))
        links = np.array([row_a[a] * m + row_b[b] for a, b in test_set.links_between(source, target)], np.int64)
        truth += len(links)
        title_score, phonetic_score = scorers(testset, A, B, title, phonetic)
        top = top_pairs(title_score, phonetic_score, far_mask(testset, source, target, max_km), tenths, max(KS))
        for w, k, min_score in settings:
            codes = kept(top[w], k, m, min_score or 0.0)
            candidates[w, k, min_score] += len(codes)
            found[w, k, min_score] += int(np.isin(links, codes).sum())
        print(f"{A.label}-{B.label} done after {time.time() - start:.0f} s", flush=True)
    seconds = round(time.time() - start, 1)
    return [{"testset": testset, "title_method": title, "phonetic_method": phonetic, "title_weight": w / 10, "k": k,
             "min_score": min_score, "truth": truth, "found": found[w, k, min_score],
             "PC": round(found[w, k, min_score] / truth, 4) if truth else "",
             "candidates": candidates[w, k, min_score], "seconds": seconds}
            for w, k, min_score in settings]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--testset", required=True)
    ap.add_argument("--title", default="labse")
    ap.add_argument("--phonetic", default="tfidf:2-3")
    ap.add_argument("--max-km", type=float, default=MAX_KM)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = run(args.testset, args.title, args.phonetic, args.max_km)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        if row["k"] == 5 and row["min_score"] == "":
            print(f"w={row['title_weight']:.1f} k=5  PC {row['PC']:.3f}  |C| {row['candidates']:,}")


if __name__ == "__main__":
    main()
