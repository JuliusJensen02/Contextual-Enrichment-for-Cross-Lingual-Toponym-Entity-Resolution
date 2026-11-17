# Candidate generation experiments

Overview of every candidate generation (blocking) test run so far, with the numbers.
All tests ran on the full minimized datasets, never on samples.

## Rerun of 17 November 2026: new Pleiades-TM

The Pleiades-TM test set was rebuilt after the experiments below: Pleiades 3,915 records
(3,107 with coordinates), Trismegistos 535 (261 with coordinates), 65 ground truth links,
2,094,525 possible pairs. Before it was 2,909 / 252 records, 100 links and 733,068 pairs.
The Trismegistos title is the Greek name (Pleiades: Latin); `title_ipa` is its IPA.
**Every Pleiades-TM number in the sections below is from the old test set.** MEHDIE and zh-ru
did not change.

The experiments that decide the pipeline (7, 10, 11b, 12, 13) were run again on all three test
sets with the scripts in `experiments/` (`python experiments/run_all.py`, then
`python experiments/report.py`). All tables of the rerun are in `rerun/report.md`; the rows are
in `sweep_parameters.csv` (experiment 12) and `sweep_combination.csv` (experiments 10, 11b, 13),
which replace the files of the first run. `pipeline_explained.html` shows the rerun.

| | MEHDIE | Pleiades-TM (new) | zh-ru |
|---|---|---|---|
| Geo: fitted threshold / farthest link | 46.0 / 42.1 km | 86.7 / 78.1 km | 0.02 / 0.0 km |
| Phonetic only (TF-IDF 2-3), k = 5 | 0.825 | 0.831 | 0.633 |
| Title only (LaBSE), k = 5 | 0.640 | 0.585 | 0.777 |
| Pipeline (w = 0.5, k = 5): PC | 0.868 | 0.862 | 0.804 |
| Pipeline: candidate pairs | 297,693 | 20,283 | 98,218 |

- No decision changes: 100 km, TF-IDF on `title_ipa`, LaBSE on the title, w = 0.5, k = 5.
- On the new Pleiades-TM, at w = 0.5, k = 5, the letter-based title scores PassJoin and
  TFIDF_kNN find 58 of 65 links against 56 for LaBSE, and the phonetic scores range from 53 to
  57 links with LaBSE as the title score (TF-IDF 2-3: 56; MinHash_LSH n=2: 57, mean PC 0.849
  against 0.845). One link is 0.015 PC. Mean PC over the test sets is still highest at w = 0.5.
- The Pleiades-TM numbers of experiments 10, 11b and 13 were run a second time on 17 November,
  after `scripts/minimize_datasets.py` was fixed: it wrote the romanized `name_standard` as the
  Trismegistos title instead of the Greek name. Experiments 7 and 12 do not use the title and
  gave the same numbers.
- MEHDIE and zh-ru: experiment 12 reproduces the first run exactly. The scripts for experiments
  7, 10, 11b and 13 were written again (the first ones were not kept); their MEHDIE and zh-ru
  numbers differ from the first run by under 0.01 PC on average and by up to 0.06 PC (7 links)
  in single MEHDIE rows.
- Did not finish within 25 minutes, as in the first run: MinHash_LSH n=2, threshold 0.2 and
  PassJoin tau=2, both on MEHDIE.

## Reading the tables

| Term | Meaning |
|---|---|
| PC | Pair completeness: share of ground truth links that are among the candidates (recall). Higher is better. |
| \|C\| | Number of candidate pairs. Lower is better. |
| PQ | Pair quality: share of candidates that are ground truth links (precision). |
| k | Neighbours kept per name/record in the kNN methods. |
| ipa / names | What a letter-based method compares: the `title_ipa` encodings or the names as written. |

The goal is as high PC as possible with as few candidates as possible.

## Test sets

| Test set | Datasets (records) | Ground truth links | Possible pairs |
|---|---|---|---|
| MEHDIE | Kima 14,341, Yaqut 15,904, Thurayya 4,482 | 114 | 363,637,354 |
| Pleiades-TM | Pleiades 2,909, Trismegistos 252 | 100 | 733,068 |
| zh-ru | Wikidata_zh 14,562, Wikidata_ru 6,425 | 3,263 | 93,560,850 |

Things to keep in mind when reading the results:

- MEHDIE and Pleiades-TM have about 100 links each, so one link is about 1 percentage point of PC.
- Coordinate coverage: Kima 8,648, Yaqut 2,675, Thurayya 4,482 (all), Pleiades 2,472, Trismegistos 204,
  Wikidata_zh 13,568, Wikidata_ru 6,409.
- zh-ru has copied values on both sides: 3,247 of the 3,263 links have the identical coordinate
  point, and `name_variants` contains English labels that are identical on both sides. We have
  chosen to ignore this, but it explains some of the numbers below.

## Overview of the experiments

| # | Experiment | Input used | Where it ran | Main result |
|---|---|---|---|---|
| 1 | Parameter sweep of the five existing methods | title + name variants, `title_ipa`, geo as after-filter | `run_candidate_generation.py`, saved in `sweep.csv` | IPA is essential in MEHDIE, names are better in Pleiades-TM, everything is weak on zh-ru |
| 2 | zh-ru: other language models, more neighbours, context in the embedding | title + name variants (+ type, country, description) | loose script | LaBSE is the best model; type + country helps a lot but is not allowed input |
| 3 | New methods on allowed input only | title, `title_ipa`, coordinates | loose script | Name similarity + geo bonus in one score is best on all three test sets |
| 4 | Reducing \|C\| for the new method | title, `title_ipa`, coordinates | loose script | A score threshold cuts \|C\| by 3-30x for a few points of PC |
| 5 | Fitting the weights of the new score by gradient descent | title, `title_ipa`, coordinates | loose script | Gains of a few links at most; the hand-set weights were already close |
| 6 | Three-step pipeline: geo, then phonetic, then title | title, `title_ipa`, coordinates | loose script | Clearly worse than the combined score; the phonetic step is a ceiling |
| 7 | Geo only: fitting the distance threshold by gradient descent | coordinates | loose script | Optimum is just past the farthest link (42 / 78 / 0 km). Decision: one common threshold of 100 km |
| 8 | Which phonetic similarity, behind the 100 km filter | `title_ipa`, coordinates | loose script | TF-IDF cosine on 2-3 grams kept; no alternative is consistently better |
| 9 | Which title similarity, behind the 100 km filter | title, coordinates | loose script | No single winner; shortlist of LaBSE, multilingual-e5-large and edit distance on transliterated titles |
| 10 | Combination: title method, weight, k, score threshold | title, `title_ipa`, coordinates | loose script | LaBSE, equal weight, k=5, no score threshold |
| 11 | The five methods in `methods/` in the pipeline: alone behind the filter, and as text score | title, `title_ipa`, coordinates | `run_candidate_generation.py` (`sweep_pipeline.csv`) and loose script | LM_kNN_search is the best text score; the choice from experiment 10 stands |
| 12 | Every parameter of the four letter-based methods varied on `title_ipa`, behind the 100 km filter | `title_ipa`, coordinates | `run_candidate_generation.py` (`sweep_parameters.csv`) | Shorter pieces lift MinHash_LSH and Q_grams clearly, at many more candidates; TFIDF_kNN stays best for a given number of candidates |
| 13 | Combined score with each phonetic method at its best piece length | title, `title_ipa`, coordinates | loose script (`sweep_combination.csv`) | All phonetic methods land within 0.01 mean PC of each other; the piece length no longer matters; TFIDF_kNN kept |

Experiments 2-10 and 11b ran in throwaway scripts outside the repository.

Rule decided after experiment 2: the candidate generator may only use the title, the phonetic
title and the coordinates. Experiments 3 and later follow that rule. Experiments 1 and 2 do
not: they also use `name_variants` and `wiki_title`.

## The pipeline the experiments led to

Experiments 7-10 each decide one part of the final pipeline, which is implemented in
`pipeline.py`:

| Pipeline part | Decided in | Choice |
|---|---|---|
| 1. Geo filter | Experiment 7 | Pairs more than 100 km apart are dropped; pairs where a record has no coordinates are always kept |
| 2. Phonetic similarity | Experiment 8 | TF-IDF cosine on the letter 2- and 3-grams of `title_ipa` |
| 3. Title similarity | Experiments 9 and 10 | Cosine of the LaBSE embeddings of the titles |
| 4. Combination | Experiment 10 | Score = 0.5 * title similarity + 0.5 * phonetic similarity; every record keeps its 5 best, from both sides (union); no score threshold |

Distance is only a filter. It is not part of the score.

Result of `python pipeline.py` on the full test sets:

| Test set | PC | PQ | RR | \|C\| |
|---|---|---|---|---|
| MEHDIE | 0.868 | 0.00033 | 0.99918 | 297,697 |
| Pleiades-TM | 0.890 | 0.00601 | 0.97981 | 14,802 |
| zh-ru | 0.804 | 0.02673 | 0.99895 | 98,218 |

These differ from the experiment 10 script by one link in MEHDIE (0.868 against 0.860) and a
handful of candidates. The likely cause (not verified) is that the titles are embedded in a
different batch order, which changes the similarities in the last decimals and with them a
few near-ties.

---

## Experiment 1: parameter sweep of the existing methods

The five methods in `methods/`, each with several parameter values, the letter-based ones with
phonetic on and off, and the geo restriction at several distances.

- Methods and parameters: Q_grams `t` 0.4 / 0.6 / 0.8; PassJoin `tau` 0 / 1; MinHash_LSH threshold
  0.2 / 0.3 / 0.5 / 0.7; TFIDF_kNN and LM_kNN_search (LaBSE) `k` 1 / 3 / 5 / 10.
- Geo: no restriction, then candidates restricted to 10, 25, 50, 100 and 250 km. Pairs where a
  record has no coordinates are kept.
- Names here are the title plus all name variants.
- PassJoin `tau` 2 and above was not run on the full data: on a sample `tau=2` gave about 17
  times as many candidates as `tau=1`, which would be about 30 million pairs in MEHDIE.
- Raw results: `sweep.csv` (540 rows). Total runtime 23 min 38 s.

Command:

```
python run_candidate_generation.py --full --phonetic both --max-km 10 25 50 100 250 \
    --tau 0 1 --k 1 3 5 10 --minhash-threshold 0.2 0.3 0.5 0.7 --qgram-t 0.4 0.6 0.8 \
    --out candidate_generation/results/sweep.csv
```

### MEHDIE

| Method | Params | Input | PC no geo | PC 10 km | PC 25 km | PC 50 km | \|C\| no geo | \|C\| 50 km |
|---|---|---|---|---|---|---|---|---|
| Q_grams | t=0.4 | ipa | 0.711 | 0.684 | 0.693 | 0.711 | 436,874 | 333,699 |
| Q_grams | t=0.4 | names | 0.149 | 0.149 | 0.149 | 0.149 | 397,276 | 222,814 |
| Q_grams | t=0.6 | ipa | 0.588 | 0.570 | 0.570 | 0.588 | 113,774 | 83,765 |
| Q_grams | t=0.6 | names | 0.149 | 0.149 | 0.149 | 0.149 | 93,471 | 55,603 |
| Q_grams | t=0.8 | ipa | 0.456 | 0.439 | 0.439 | 0.456 | 17,493 | 13,351 |
| Q_grams | t=0.8 | names | 0.123 | 0.123 | 0.123 | 0.123 | 15,919 | 10,823 |
| PassJoin | tau=0 | ipa | 0.351 | 0.342 | 0.342 | 0.351 | 2,612 | 2,321 |
| PassJoin | tau=0 | names | 0.114 | 0.114 | 0.114 | 0.114 | 4,269 | 3,791 |
| PassJoin | tau=1 | ipa | 0.658 | 0.640 | 0.640 | 0.658 | 1,189,560 | 893,824 |
| PassJoin | tau=1 | names | 0.132 | 0.132 | 0.132 | 0.132 | 1,095,687 | 727,642 |
| MinHash_LSH | thr=0.2 | ipa | 0.746 | 0.728 | 0.728 | 0.746 | 4,302,188 | 3,428,438 |
| MinHash_LSH | thr=0.2 | names | 0.158 | 0.158 | 0.158 | 0.158 | 2,595,464 | 1,277,737 |
| MinHash_LSH | thr=0.3 | ipa | 0.632 | 0.614 | 0.614 | 0.632 | 383,405 | 305,328 |
| MinHash_LSH | thr=0.3 | names | 0.158 | 0.158 | 0.158 | 0.158 | 568,142 | 310,697 |
| MinHash_LSH | thr=0.5 | ipa | 0.517 | 0.500 | 0.500 | 0.517 | 20,493 | 16,601 |
| MinHash_LSH | thr=0.5 | names | 0.140 | 0.140 | 0.140 | 0.140 | 28,810 | 17,297 |
| MinHash_LSH | thr=0.7 | ipa | 0.351 | 0.342 | 0.342 | 0.351 | 3,037 | 2,665 |
| MinHash_LSH | thr=0.7 | names | 0.132 | 0.132 | 0.132 | 0.132 | 5,028 | 4,244 |
| TFIDF_kNN | k=1 | ipa | 0.588 | 0.561 | 0.570 | 0.588 | 63,872 | 48,072 |
| TFIDF_kNN | k=1 | names | 0.123 | 0.123 | 0.123 | 0.123 | 74,605 | 44,938 |
| TFIDF_kNN | k=3 | ipa | 0.684 | 0.658 | 0.667 | 0.684 | 181,578 | 134,982 |
| TFIDF_kNN | k=3 | names | 0.158 | 0.158 | 0.158 | 0.158 | 199,715 | 120,743 |
| TFIDF_kNN | k=5 | ipa | 0.737 | 0.711 | 0.719 | 0.737 | 295,810 | 219,251 |
| TFIDF_kNN | k=5 | names | 0.158 | 0.158 | 0.158 | 0.158 | 310,467 | 185,284 |
| TFIDF_kNN | k=10 | ipa | 0.798 | 0.772 | 0.781 | 0.798 | 575,873 | 425,382 |
| TFIDF_kNN | k=10 | names | 0.158 | 0.158 | 0.158 | 0.158 | 559,477 | 332,817 |
| LM_kNN_search | k=1 | names | 0.684 | 0.667 | 0.667 | 0.684 | 145,188 | 96,804 |
| LM_kNN_search | k=3 | names | 0.737 | 0.719 | 0.719 | 0.737 | 380,929 | 257,485 |
| LM_kNN_search | k=5 | names | 0.746 | 0.728 | 0.728 | 0.746 | 599,591 | 407,005 |
| LM_kNN_search | k=10 | names | 0.754 | 0.737 | 0.737 | 0.754 | 1,121,959 | 766,602 |

PC at 100 and 250 km equals PC without geo for every row.

### Pleiades-TM

| Method | Params | Input | PC no geo | PC 10 km | PC 25 km | PC 50 km | \|C\| no geo | \|C\| 50 km |
|---|---|---|---|---|---|---|---|---|
| Q_grams | t=0.4 | ipa | 0.480 | 0.460 | 0.470 | 0.470 | 1,738 | 559 |
| Q_grams | t=0.4 | names | 0.850 | 0.790 | 0.830 | 0.840 | 6,121 | 1,354 |
| Q_grams | t=0.6 | ipa | 0.440 | 0.420 | 0.430 | 0.430 | 302 | 121 |
| Q_grams | t=0.6 | names | 0.850 | 0.790 | 0.830 | 0.840 | 1,071 | 308 |
| Q_grams | t=0.8 | ipa | 0.390 | 0.380 | 0.380 | 0.380 | 91 | 48 |
| Q_grams | t=0.8 | names | 0.830 | 0.780 | 0.810 | 0.820 | 259 | 114 |
| PassJoin | tau=0 | ipa | 0.330 | 0.320 | 0.320 | 0.320 | 51 | 35 |
| PassJoin | tau=0 | names | 0.820 | 0.770 | 0.800 | 0.810 | 163 | 95 |
| PassJoin | tau=1 | ipa | 0.420 | 0.400 | 0.410 | 0.410 | 1,469 | 478 |
| PassJoin | tau=1 | names | 0.840 | 0.780 | 0.820 | 0.830 | 6,613 | 1,417 |
| MinHash_LSH | thr=0.2 | ipa | 0.770 | 0.730 | 0.750 | 0.760 | 12,162 | 3,487 |
| MinHash_LSH | thr=0.2 | names | 0.870 | 0.810 | 0.850 | 0.860 | 37,130 | 8,409 |
| MinHash_LSH | thr=0.3 | ipa | 0.710 | 0.670 | 0.690 | 0.700 | 2,311 | 767 |
| MinHash_LSH | thr=0.3 | names | 0.870 | 0.810 | 0.850 | 0.860 | 8,026 | 1,999 |
| MinHash_LSH | thr=0.5 | ipa | 0.490 | 0.480 | 0.480 | 0.480 | 188 | 93 |
| MinHash_LSH | thr=0.5 | names | 0.860 | 0.810 | 0.840 | 0.850 | 585 | 183 |
| MinHash_LSH | thr=0.7 | ipa | 0.350 | 0.340 | 0.340 | 0.340 | 59 | 40 |
| MinHash_LSH | thr=0.7 | names | 0.820 | 0.770 | 0.800 | 0.810 | 180 | 100 |
| TFIDF_kNN | k=1 | ipa | 0.740 | 0.700 | 0.720 | 0.730 | 2,995 | 911 |
| TFIDF_kNN | k=1 | names | 0.880 | 0.820 | 0.860 | 0.870 | 7,198 | 1,537 |
| TFIDF_kNN | k=3 | ipa | 0.820 | 0.780 | 0.800 | 0.810 | 8,220 | 2,408 |
| TFIDF_kNN | k=3 | names | 0.890 | 0.830 | 0.870 | 0.880 | 18,488 | 3,838 |
| TFIDF_kNN | k=5 | ipa | 0.830 | 0.790 | 0.810 | 0.820 | 13,315 | 3,823 |
| TFIDF_kNN | k=5 | names | 0.900 | 0.840 | 0.880 | 0.890 | 29,000 | 6,058 |
| TFIDF_kNN | k=10 | ipa | 0.840 | 0.790 | 0.820 | 0.830 | 25,777 | 7,426 |
| TFIDF_kNN | k=10 | names | 0.900 | 0.840 | 0.880 | 0.890 | 53,016 | 11,237 |
| LM_kNN_search | k=1 | names | 0.890 | 0.830 | 0.870 | 0.880 | 10,090 | 2,242 |
| LM_kNN_search | k=3 | names | 0.890 | 0.830 | 0.870 | 0.880 | 25,028 | 5,452 |
| LM_kNN_search | k=5 | names | 0.890 | 0.830 | 0.870 | 0.880 | 38,962 | 8,515 |
| LM_kNN_search | k=10 | names | 0.890 | 0.830 | 0.870 | 0.880 | 69,725 | 15,482 |

PC at 100 and 250 km equals PC without geo for every row.

### zh-ru

The geo restriction never changes PC here (both sides of a link have the same coordinates), so
only one PC column is shown.

| Method | Params | Input | PC | \|C\| no geo | \|C\| 50 km |
|---|---|---|---|---|---|
| Q_grams | t=0.4 | ipa | 0.111 | 35,514 | 6,939 |
| Q_grams | t=0.4 | names | 0.315 | 34,384 | 5,210 |
| Q_grams | t=0.6 | ipa | 0.055 | 2,410 | 619 |
| Q_grams | t=0.6 | names | 0.315 | 21,298 | 4,088 |
| Q_grams | t=0.8 | ipa | 0.023 | 354 | 136 |
| Q_grams | t=0.8 | names | 0.315 | 15,453 | 3,244 |
| PassJoin | tau=0 | ipa | 0.009 | 38 | 30 |
| PassJoin | tau=0 | names | 0.315 | 10,290 | 2,883 |
| PassJoin | tau=1 | ipa | 0.059 | 28,819 | 6,219 |
| PassJoin | tau=1 | names | 0.315 | 110,987 | 8,942 |
| MinHash_LSH | thr=0.2 | ipa | 0.236 | 850,025 | 54,626 |
| MinHash_LSH | thr=0.2 | names | 0.315 | 261,750 | 16,980 |
| MinHash_LSH | thr=0.3 | ipa | 0.119 | 64,119 | 6,442 |
| MinHash_LSH | thr=0.3 | names | 0.315 | 180,761 | 12,441 |
| MinHash_LSH | thr=0.5 | ipa | 0.037 | 3,054 | 627 |
| MinHash_LSH | thr=0.5 | names | 0.315 | 68,449 | 6,113 |
| MinHash_LSH | thr=0.7 | ipa | 0.011 | 67 | 43 |
| MinHash_LSH | thr=0.7 | names | 0.315 | 13,169 | 3,085 |
| TFIDF_kNN | k=1 | ipa | 0.146 | 19,943 | 2,064 |
| TFIDF_kNN | k=1 | names | 0.250 | 4,463 | 1,761 |
| TFIDF_kNN | k=3 | ipa | 0.220 | 57,867 | 5,277 |
| TFIDF_kNN | k=3 | names | 0.299 | 13,800 | 3,333 |
| TFIDF_kNN | k=5 | ipa | 0.257 | 94,724 | 8,398 |
| TFIDF_kNN | k=5 | names | 0.306 | 22,557 | 4,245 |
| TFIDF_kNN | k=10 | ipa | 0.309 | 184,530 | 15,648 |
| TFIDF_kNN | k=10 | names | 0.309 | 43,644 | 5,775 |
| LM_kNN_search | k=1 | names | 0.506 | 32,346 | 4,555 |
| LM_kNN_search | k=3 | names | 0.595 | 90,234 | 9,089 |
| LM_kNN_search | k=5 | names | 0.622 | 145,959 | 12,808 |
| LM_kNN_search | k=10 | names | 0.663 | 279,559 | 21,460 |

### Findings

- Phonetic: essential in MEHDIE (best PC 0.798 on IPA against 0.158 on names), slightly worse than
  names in Pleiades-TM (0.840 against 0.900).
- zh-ru on names is stuck at about 0.315 for the letter-based methods. Those are the links whose
  two records share an identical English label in `name_variants`, not real matching.
- Geo as an after-filter: 50 km costs nothing in MEHDIE and 0.01 in Pleiades-TM; 10 and 25 km cost
  up to 0.06 in Pleiades-TM and about 0.02-0.03 in MEHDIE; 100 km costs nothing anywhere.
- LaBSE saturates: from k=3 to k=10 PC rises 0.017 in MEHDIE while the candidates triple.
- No existing method gets above 0.663 on zh-ru or 0.798 on MEHDIE.

---

## Experiment 2: why zh-ru is weak, and other models

Only zh-ru. Still title plus name variants, as in experiment 1. The LaBSE baseline was
reproduced first (0.664 at k=10 against 0.663 in the sweep; the difference is tie-breaking).

### Which links are missed (LaBSE, k=10)

| Country of the place | Missed / total | Share missed |
|---|---|---|
| Japan | 214 / 638 | 0.34 |
| People's Republic of China | 215 / 472 | 0.46 |
| Mongolia | 145 / 295 | 0.49 |
| Russia | 25 / 252 | 0.10 |
| South Korea | 153 / 177 | 0.86 |
| India | 15 / 169 | 0.09 |

- Japanese and Korean places: the Chinese name is the characters read in Mandarin
  (`旌善郡` against `Чонсон`), so there is no phonetic similarity to find.
- Chinese places: the Chinese name carries a type suffix that the Russian name lacks
  (`邢台县` against `Синтай`).

### Variants tested

| Variant | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 | PC k=50 | \|C\| k=50 |
|---|---|---|---|---|---|---|
| LaBSE, names only (baseline) | 0.596 | 90,294 | 0.664 | 279,525 | 0.740 | 1,236,133 |
| LaBSE, name + type + country | 0.872 | 67,218 | 0.924 | 201,569 | 0.973 | 845,517 |
| LaBSE, name + type | 0.821 | 71,420 | 0.890 | 202,271 | 0.961 | 865,770 |
| LaBSE, name + Chinese type suffix stripped | 0.622 | 110,221 | 0.694 | 336,308 | 0.776 | 1,450,666 |
| LaBSE, name + description | 0.449 | 79,068 | 0.521 | 238,091 | 0.627 | 1,024,407 |
| multilingual-e5-large, names only | 0.573 | 94,831 | 0.641 | 296,235 | 0.722 | 1,300,941 |
| bge-m3, names only | 0.546 | 95,009 | 0.609 | 297,229 | 0.686 | 1,326,904 |
| paraphrase-multilingual-mpnet-base-v2, names only | 0.408 | 97,360 | 0.459 | 302,417 | 0.533 | 1,402,677 |

What the variants are:

- name + type + country: the embedded text is e.g. `邢台县 (county of China, People's Republic of China)`,
  from `instance_of_label` and `country`. Both fields are English and identical on both sides.
- name + type suffix stripped: suffixes such as 县 / 市 / 郡 / 省 are removed and the result is
  added as an extra name variant on the Chinese side.
- name + description: the own-language `description` is appended where it exists.

Other combinations (k=10):

| Variant | PC | \|C\| |
|---|---|---|
| LaBSE OR TFIDF_kNN on IPA (union) | 0.752 | 456,689 |
| LaBSE with suffix stripped OR TFIDF_kNN on IPA | 0.769 | 511,655 |
| Coordinates only, pairs at most 1 km apart | 0.995 | 85,733 |
| Coordinates only, pairs at most 50 km apart | 0.995 | 237,185 |

### Findings

- LaBSE is the best of the four language models on names alone.
- More neighbours do not solve it: names only reaches 0.740 at k=50 with 1.2 million candidates.
- Type + country lifts PC from 0.664 to 0.924 at k=10, but it works through the copied English
  values and uses input the candidate generator is not allowed to use. Not pursued.
- Coordinates alone give 0.995 because the points are identical on both sides.

---

## Experiment 3: new methods on title, phonetic title and coordinates only

All three test sets. Each record has exactly one title, one `title_ipa` (the first, if a record
has several; that affects 101 Trismegistos records) and at most one coordinate point. No name
variants.

Methods tested:

| Method | What it does |
|---|---|
| LaBSE on title | kNN on LaBSE embeddings of the title. |
| TFIDF on IPA | kNN on TF-IDF vectors of the letter 2- and 3-grams of `title_ipa`. |
| LaBSE + TFIDF | kNN on the sum of the two similarities above. |
| LaBSE + TFIDF within 50 km | Same score, but only records at most 50 km away (or without coordinates) can be neighbours. |
| Geo radius | All pairs at most 1, 10 or 50 km apart. Uses coordinates only. |
| Geo kNN | The k geographically nearest records on the other side. Uses coordinates only. |
| LaBSE + TFIDF + geo bonus | kNN on `LaBSE similarity + TFIDF similarity + exp(-distance / 10 km)`. The geo term is 0 when a record has no coordinates. |

Every kNN method takes each record's k best on the other side, in both directions (union).

### MEHDIE

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE on title | 0.360 | 64,251 | 0.509 | 184,503 | 0.570 | 594,742 |
| TFIDF on IPA | 0.526 | 63,872 | 0.693 | 181,578 | 0.798 | 575,873 |
| LaBSE + TFIDF | 0.614 | 64,405 | 0.781 | 184,667 | 0.868 | 591,531 |
| LaBSE + TFIDF within 10 km | 0.623 | 58,873 | 0.798 | 164,457 | 0.868 | 501,414 |
| LaBSE + TFIDF within 50 km | 0.658 | 62,787 | 0.825 | 179,735 | 0.912 | 566,915 |
| Geo kNN | 0.711 | 29,117 | 0.816 | 83,479 | 0.816 | 272,019 |
| LaBSE + TFIDF + geo bonus (10 km) | 0.860 | 64,413 | 0.912 | 184,092 | 0.947 | 591,233 |
| LaBSE + TFIDF + geo bonus (50 km) | 0.860 | 64,826 | 0.912 | 186,580 | 0.939 | 602,573 |

### Pleiades-TM

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE on title | 0.720 | 2,978 | 0.800 | 8,827 | 0.870 | 29,202 |
| TFIDF on IPA | 0.710 | 2,958 | 0.790 | 8,758 | 0.820 | 29,117 |
| LaBSE + TFIDF | 0.770 | 2,967 | 0.860 | 8,790 | 0.890 | 29,149 |
| LaBSE + TFIDF within 10 km | 0.800 | 2,993 | 0.830 | 8,920 | 0.860 | 29,517 |
| LaBSE + TFIDF within 50 km | 0.850 | 2,991 | 0.880 | 8,911 | 0.910 | 29,493 |
| Geo kNN | 0.950 | 2,538 | 0.970 | 7,580 | 0.970 | 25,151 |
| LaBSE + TFIDF + geo bonus (10 km) | 0.980 | 2,972 | 1.000 | 8,790 | 1.000 | 29,152 |
| LaBSE + TFIDF + geo bonus (50 km) | 0.970 | 2,986 | 1.000 | 8,835 | 1.000 | 29,167 |

### zh-ru

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE on title | 0.301 | 19,574 | 0.377 | 57,141 | 0.474 | 185,473 |
| TFIDF on IPA | 0.146 | 19,943 | 0.219 | 57,867 | 0.310 | 184,530 |
| LaBSE + TFIDF | 0.361 | 19,572 | 0.470 | 57,085 | 0.574 | 184,149 |
| LaBSE + TFIDF within 10 km | 0.754 | 19,282 | 0.851 | 59,358 | 0.941 | 201,133 |
| LaBSE + TFIDF within 50 km | 0.691 | 19,276 | 0.807 | 58,906 | 0.902 | 199,381 |
| Geo kNN | 0.884 | 17,144 | 0.945 | 51,376 | 0.970 | 169,074 |
| LaBSE + TFIDF + geo bonus (10 km) | 0.952 | 17,892 | 0.975 | 55,236 | 0.985 | 184,627 |
| LaBSE + TFIDF + geo bonus (50 km) | 0.934 | 18,031 | 0.969 | 54,677 | 0.982 | 181,304 |

### Geo radius (coordinates only, no k)

| Radius | MEHDIE PC | MEHDIE \|C\| | Pleiades-TM PC | Pleiades-TM \|C\| | zh-ru PC | zh-ru \|C\| |
|---|---|---|---|---|---|---|
| 1 km | 0.614 | 3,240 | 0.790 | 180 | 0.995 | 85,733 |
| 10 km | 0.772 | 25,250 | 0.910 | 438 | 0.995 | 111,644 |
| 50 km | 0.816 | 329,772 | 0.960 | 1,805 | 0.995 | 237,185 |

Pairs where a record has no coordinates are not candidates here, which caps PC (0.816 in MEHDIE).

### Findings

- LaBSE + TFIDF + geo bonus is the best method on all three test sets at every k.
- A soft geo bonus beats a hard cut: in MEHDIE at k=3 the bonus gives 0.912, the 50 km cut 0.825.
- The scale of the bonus (10 or 50 km) hardly matters.
- Summing LaBSE and TFIDF beats either alone on all three test sets.
- Title only is weaker than title plus variants: LaBSE on zh-ru at k=10 drops from 0.664 to 0.474.
- On zh-ru the gain comes from the identical coordinates. In MEHDIE and Pleiades-TM a 1 km radius
  alone gives only 0.614 and 0.790, so there the name part does real work.

---

## Experiment 4: fewer candidates for the new method

Most records have no match at all, so plain kNN forces out k candidates for each of them. Three
ways of dropping candidates were tested on top of LaBSE + TFIDF + geo bonus (10 km). The score
lies between 0 and 3.

| Cut | Meaning |
|---|---|
| Score threshold | A neighbour is kept only if its score is at least the threshold. |
| Mutual | The pair must be in the top k from both sides, instead of from either side (union). |
| Gap to best | A neighbour is dropped if its score is more than a given amount below the record's best neighbour. |

### The same settings on all three test sets

| k | Mode | Score at least | MEHDIE PC | MEHDIE \|C\| | Pleiades-TM PC | Pleiades-TM \|C\| | zh-ru PC | zh-ru \|C\| |
|---|---|---|---|---|---|---|---|---|
| 1 | union | none | 0.860 | 64,413 | 0.980 | 2,972 | 0.952 | 17,892 |
| 1 | union | 1.0 | 0.860 | 30,959 | 0.960 | 548 | 0.952 | 10,744 |
| 1 | union | 1.2 | 0.842 | 14,500 | 0.920 | 285 | 0.944 | 8,679 |
| 1 | union | 1.5 | 0.781 | 5,231 | 0.820 | 133 | 0.768 | 5,743 |
| 1 | mutual | none | 0.439 | 5,041 | 0.820 | 189 | 0.860 | 3,095 |
| 1 | mutual | 1.0 | 0.439 | 4,604 | 0.810 | 153 | 0.860 | 3,053 |
| 1 | mutual | 1.2 | 0.439 | 3,654 | 0.810 | 113 | 0.854 | 3,011 |
| 1 | mutual | 1.5 | 0.421 | 2,241 | 0.760 | 87 | 0.708 | 2,479 |
| 3 | union | none | 0.912 | 184,092 | 1.000 | 8,790 | 0.975 | 55,236 |
| 3 | union | 1.0 | 0.912 | 60,773 | 0.960 | 653 | 0.975 | 23,240 |
| 3 | union | 1.2 | 0.895 | 21,112 | 0.920 | 301 | 0.965 | 17,954 |
| 3 | union | 1.5 | 0.816 | 6,001 | 0.820 | 135 | 0.780 | 9,817 |
| 3 | mutual | none | 0.825 | 24,270 | 0.870 | 693 | 0.950 | 7,725 |
| 3 | mutual | 1.0 | 0.825 | 19,704 | 0.860 | 370 | 0.950 | 6,556 |
| 3 | mutual | 1.2 | 0.816 | 12,479 | 0.860 | 204 | 0.942 | 5,622 |
| 3 | mutual | 1.5 | 0.772 | 5,324 | 0.800 | 114 | 0.766 | 3,820 |
| 10 | union | none | 0.947 | 591,233 | 1.000 | 29,152 | 0.985 | 184,627 |
| 10 | union | 1.0 | 0.912 | 87,024 | 0.960 | 661 | 0.983 | 50,111 |
| 10 | union | 1.2 | 0.895 | 22,511 | 0.920 | 301 | 0.973 | 41,227 |
| 10 | union | 1.5 | 0.816 | 6,004 | 0.820 | 135 | 0.781 | 14,208 |
| 10 | mutual | none | 0.904 | 103,307 | 0.890 | 2,458 | 0.968 | 25,243 |
| 10 | mutual | 1.0 | 0.904 | 52,701 | 0.880 | 528 | 0.967 | 13,264 |
| 10 | mutual | 1.2 | 0.886 | 20,386 | 0.880 | 237 | 0.957 | 9,621 |
| 10 | mutual | 1.5 | 0.807 | 5,967 | 0.810 | 123 | 0.774 | 5,248 |

### Best settings found per test set

These combine the three cuts and were picked per test set, so they show what is reachable
rather than one setting to use everywhere. "Gap" is the gap to best.

| Test set | PC | \|C\| | PQ | Setting |
|---|---|---|---|---|
| MEHDIE | 0.912 | 60,773 | 0.002 | k=3, union, score at least 1.0 |
| MEHDIE | 0.895 | 21,112 | 0.005 | k=3, union, score at least 1.2 |
| MEHDIE | 0.816 | 5,766 | 0.016 | k=2, union, score at least 1.5, gap at most 0.15 |
| MEHDIE | 0.693 | 3,577 | 0.022 | k=1, union, score at least 1.7 |
| Pleiades-TM | 1.000 | 8,790 | 0.011 | k=3, union, no threshold |
| Pleiades-TM | 0.960 | 548 | 0.175 | k=1, union, score at least 1.0 |
| Pleiades-TM | 0.920 | 285 | 0.323 | k=1, union, score at least 1.2 |
| Pleiades-TM | 0.870 | 166 | 0.524 | k=1, union, score at least 1.4 |
| Pleiades-TM | 0.810 | 113 | 0.717 | k=1, mutual, score at least 1.2 |
| zh-ru | 0.983 | 50,111 | 0.064 | k=10, union, score at least 1.0 |
| zh-ru | 0.974 | 21,219 | 0.150 | k=3, union, score at least 1.0, gap at most 0.3 |
| zh-ru | 0.964 | 9,429 | 0.334 | k=10, mutual, score at least 1.0, gap at most 0.15 |
| zh-ru | 0.941 | 5,129 | 0.599 | k=3, mutual, score at least 1.2, gap at most 0.15 |
| zh-ru | 0.854 | 3,011 | 0.926 | k=1, mutual, score at least 1.2 |

### Findings

- The score threshold does most of the cutting. At a threshold of 1.2, \|C\| is almost
  independent of k.
- The knee is between 1.2 and 1.5: up to 1.2 the threshold costs 1-8 points of PC, at 1.5 zh-ru
  drops from 0.965 to 0.780.
- Best common setting: k=3, union, score at least 1.2.
- Mutual kNN works well on zh-ru (0.942 with 5,622 candidates for 3,263 links) but costs 8 points
  in MEHDIE, where most Yaqut records have no coordinates.
- The thresholds were chosen on the same data they are measured on, so they are rough values,
  not tuned ones.

---

## Experiment 5: fitting the weights of the new score by gradient descent

The score from experiment 3 has five numbers that were set by hand:

`score = w_labse * LaBSE + w_tfidf * TFIDF + w_geo * exp(-km / scale)`, with `w_missing` in
place of the geo term when a coordinate is missing. Hand-set: 1, 1, 1, 10 km, 0.

- Fitted with Adam, 600 steps, starting from the hand-set values, with a ranking loss (the true
  partner of a record should outrank the other records). A binary cross-entropy loss was also
  tried; it gave similar weights and slightly lower PC and is not shown.
- `k`, the score threshold and union/mutual are not differentiable and were not fitted.
- Each fit is scored three ways: on the links it was fitted on, 5-fold cross-validated, and
  fitted on the other two test sets. The last two are the honest ones.
- To make repeated fitting fast, neighbours were searched only among each record's top 100 by
  LaBSE, by TFIDF and by distance. With the hand-set weights this matches the exact run to within
  one link (MEHDIE 0.921 against 0.912 at k=3).

PC at k=3 (union), without a threshold and with \|C\| cut to three budgets by a score threshold:

| Test set (budgets) | Weights | No threshold | Small | Medium | Large |
|---|---|---|---|---|---|
| MEHDIE (5,000 / 20,000 / 60,000) | hand-set | 0.921 | 0.772 | 0.895 | 0.912 |
| | fitted on its own links | 0.921 | 0.825 | 0.904 | 0.912 |
| | 5-fold cross-validated | 0.921 | 0.807 | 0.886 | 0.912 |
| | fitted on the other two test sets | 0.921 | 0.746 | 0.798 | 0.904 |
| Pleiades-TM (150 / 300 / 650) | hand-set | 1.000 | 0.850 | 0.920 | 0.960 |
| | fitted on its own links | 1.000 | 0.870 | 0.950 | 0.970 |
| | 5-fold cross-validated | 1.000 | 0.870 | 0.920 | 0.960 |
| | fitted on the other two test sets | 1.000 | 0.840 | 0.950 | 0.980 |
| zh-ru (5,000 / 10,000 / 20,000) | hand-set | 0.976 | 0.598 | 0.784 | 0.975 |
| | fitted on its own links | 0.977 | 0.602 | 0.801 | 0.976 |
| | 5-fold cross-validated | 0.977 | 0.603 | 0.801 | 0.976 |
| | fitted on the other two test sets | 0.973 | 0.595 | 0.778 | 0.973 |

Fitted weights (only the ratios matter):

| Fitted on | w_labse | w_tfidf | w_geo | scale | w_missing |
|---|---|---|---|---|---|
| MEHDIE | 3.61 | 6.76 | 7.71 | 23.0 km | 1.00 |
| Pleiades-TM | 3.56 | 2.65 | 8.44 | 37.9 km | 0.54 |
| zh-ru | 7.75 | 5.31 | 9.38 | 0.0 km | -3.27 |
| All three | 4.28 | 4.92 | 8.76 | 14.8 km | 0.88 |

### Findings

- Without a threshold the weights change nothing: the top 3 per record stay almost the same.
- With a tight budget there is a small gain; the best cross-validated case is MEHDIE at 5,000
  candidates, 0.772 to 0.807, which is 4 links.
- Weights do not transfer reliably: fitted on the other two test sets, MEHDIE at 20,000
  candidates drops from 0.895 to 0.798.
- Geo gets about twice the weight of each name signal in every fit. zh-ru drives the scale to
  0 km, which is the identical coordinates again.
- Conclusion: fitting is possible but not worth making part of the method. Simple fixed weights,
  for example 1 : 1 : 2 with a scale of about 15 km, are as good.

---

## Experiment 6: three-step pipeline (geo, then phonetic, then title)

A strict sequence of filters instead of one combined score:

1. Geo: drop pairs more than 10 or 50 km apart (pairs without coordinates are kept).
2. Phonetic: each record keeps its top N by TFIDF on `title_ipa` among the survivors (N = 10, 50, 200).
3. Title: each record keeps its top k by LaBSE on the title among those (k = 1, 3, 10).

With the 50 km geo step:

| Test set | IPA top N | PC after step 2 | \|C\| after step 2 | PC, k=1 | \|C\|, k=1 | PC, k=3 | \|C\|, k=3 | PC, k=10 | \|C\|, k=10 |
|---|---|---|---|---|---|---|---|---|---|
| MEHDIE | 10 | 0.868 | 525,952 | 0.588 | 62,775 | 0.825 | 179,557 | 0.868 | 525,952 |
| MEHDIE | 50 | 0.886 | 2,295,132 | 0.509 | 62,705 | 0.746 | 180,320 | 0.842 | 560,192 |
| MEHDIE | 200 | 0.921 | 8,531,520 | 0.491 | 62,513 | 0.693 | 179,543 | 0.816 | 561,386 |
| Pleiades-TM | 10 | 0.840 | 29,154 | 0.790 | 3,011 | 0.820 | 8,957 | 0.840 | 29,154 |
| Pleiades-TM | 50 | 0.910 | 94,917 | 0.790 | 3,014 | 0.820 | 8,958 | 0.870 | 29,430 |
| Pleiades-TM | 200 | 0.920 | 130,516 | 0.780 | 3,011 | 0.830 | 8,970 | 0.880 | 29,388 |
| zh-ru | 10 | 0.732 | 195,105 | 0.585 | 19,862 | 0.683 | 60,161 | 0.732 | 195,105 |
| zh-ru | 50 | 0.807 | 568,513 | 0.602 | 19,665 | 0.708 | 59,991 | 0.783 | 197,586 |
| zh-ru | 200 | 0.810 | 1,388,224 | 0.603 | 19,524 | 0.707 | 59,594 | 0.783 | 197,116 |

With the 10 km geo step:

| Test set | IPA top N | PC after step 2 | \|C\| after step 2 | PC, k=1 | \|C\|, k=1 | PC, k=3 | \|C\|, k=3 | PC, k=10 | \|C\|, k=10 |
|---|---|---|---|---|---|---|---|---|---|
| MEHDIE | 10 | 0.825 | 478,691 | 0.526 | 57,750 | 0.781 | 163,100 | 0.825 | 478,691 |
| MEHDIE | 50 | 0.842 | 2,230,138 | 0.482 | 57,684 | 0.719 | 163,902 | 0.798 | 513,061 |
| MEHDIE | 200 | 0.877 | 8,468,767 | 0.465 | 57,494 | 0.684 | 163,157 | 0.789 | 514,303 |
| Pleiades-TM | 10 | 0.800 | 29,166 | 0.760 | 3,014 | 0.780 | 8,972 | 0.800 | 29,166 |
| Pleiades-TM | 50 | 0.870 | 94,186 | 0.750 | 3,014 | 0.780 | 8,967 | 0.830 | 29,441 |
| Pleiades-TM | 200 | 0.880 | 129,743 | 0.740 | 3,011 | 0.790 | 8,978 | 0.840 | 29,397 |
| zh-ru | 10 | 0.754 | 194,405 | 0.620 | 19,862 | 0.702 | 60,323 | 0.754 | 194,405 |
| zh-ru | 50 | 0.809 | 526,417 | 0.634 | 19,673 | 0.730 | 60,202 | 0.794 | 196,802 |
| zh-ru | 200 | 0.810 | 1,349,820 | 0.635 | 19,541 | 0.728 | 59,967 | 0.794 | 196,737 |

Best pipeline setting against the combined score, both at a final k of 3:

| Test set | Pipeline setting | Pipeline PC | Pipeline \|C\| | Combined score PC | Combined score \|C\| |
|---|---|---|---|---|---|
| MEHDIE | 50 km, IPA top 10, LaBSE top 3 | 0.825 | 179,557 | 0.912 | 184,092 |
| Pleiades-TM | 50 km, IPA top 200, LaBSE top 3 | 0.830 | 8,970 | 1.000 | 8,790 |
| zh-ru | 10 km, IPA top 50, LaBSE top 3 | 0.730 | 60,202 | 0.975 | 55,236 |

### Findings

- The phonetic step is a ceiling: a link it drops cannot be recovered by the title step.
- Loosening the phonetic step does not help. In MEHDIE top 200 raises the ceiling to 0.921, but
  the title step then cannot tell the true match from the extra lookalikes and the final PC at
  k=3 falls from 0.825 to 0.693.
- Running geo first makes the phonetic step much stronger than phonetic alone: MEHDIE 0.798 to
  0.868 and zh-ru 0.309 to 0.732 at top 10.
- A hard sequence is worse than adding the signals into one score, where a strong title match
  can make up for a weak phonetic one and the other way round. Geo is the only step that is
  safe as a hard filter.

---

## Experiment 7: geo only, fitting the distance threshold

Coordinates only. A pair is a candidate if its two places are at most T km apart (the closest
two points if a record has several). Pairs where a record has no coordinates are always kept.

- T was fitted by gradient descent (Adam, 800 steps) from four starting points: 1, 10, 100 and
  1000 km. A hard cut-off has no gradient, so during fitting it is a sigmoid in log-distance
  that is sharpened step by step.
- Objective: the harmonic mean of PC and RR, both measured on the pairs where both records have
  coordinates ("geo pairs"), since those are the only pairs the threshold decides about.
- As a check, every threshold was also searched exhaustively.

### Fitted thresholds

| Test set | Gradient descent | Exhaustive search | Farthest link | Links within (50 / 90 / 95 / 99 %) |
|---|---|---|---|---|
| MEHDIE | 46.0 km | 42.2 km | 42.1 km | 0.00 / 0.91 / 1.77 / 30.13 km |
| Pleiades-TM | 85.0 km | 78.2 km | 78.1 km | 0.21 / 2.14 / 10.79 / 38.86 km |
| zh-ru | 0.02 km | 0.01 km | 0.00 km | 0.00 / 0.00 / 0.00 / 0.00 km |
| All three together | 45.5 km | 78.2 km | | |

### Metrics per threshold

"All pairs" includes the pairs without coordinates. "Geo pairs" are those where both records
have coordinates.

MEHDIE: 114 links (21 without coordinates on both sides); 363,637,354 possible pairs, of which
289,754,268 are always kept for lack of coordinates. PQ is about 0.0000004 at every threshold.

| T (km) | PC | RR | \|C\| all pairs | PC geo pairs | RR geo pairs | \|C\| geo pairs |
|---|---|---|---|---|---|---|
| 1 | 0.921 | 0.20317 | 289,757,667 | 0.903 | 0.99995 | 3,399 |
| 5 | 0.974 | 0.20315 | 289,764,664 | 0.968 | 0.99986 | 10,396 |
| 10 | 0.974 | 0.20311 | 289,779,769 | 0.968 | 0.99965 | 25,501 |
| 25 | 0.982 | 0.20288 | 289,861,594 | 0.978 | 0.99855 | 107,326 |
| 46.0 (fitted) | 1.000 | 0.20238 | 290,043,929 | 1.000 | 0.99608 | 289,661 |
| 50 | 1.000 | 0.20227 | 290,085,519 | 1.000 | 0.99552 | 331,251 |
| 100 | 1.000 | 0.20070 | 290,656,333 | 1.000 | 0.98779 | 902,065 |
| 250 | 1.000 | 0.19585 | 292,417,795 | 1.000 | 0.96395 | 2,663,527 |
| 500 | 1.000 | 0.18408 | 296,698,642 | 1.000 | 0.90601 | 6,944,374 |
| 1000 | 1.000 | 0.15951 | 305,634,445 | 1.000 | 0.78506 | 15,880,177 |

Pleiades-TM: 100 links (3 without coordinates); 733,068 possible pairs, of which 228,780 are
always kept.

| T (km) | PC | PQ | RR | \|C\| all pairs | PC geo pairs | RR geo pairs | \|C\| geo pairs |
|---|---|---|---|---|---|---|---|
| 1 | 0.820 | 0.000358 | 0.68767 | 228,960 | 0.814 | 0.99964 | 180 |
| 5 | 0.920 | 0.000402 | 0.68757 | 229,033 | 0.918 | 0.99950 | 253 |
| 10 | 0.940 | 0.000410 | 0.68732 | 229,218 | 0.938 | 0.99913 | 438 |
| 25 | 0.980 | 0.000427 | 0.68681 | 229,591 | 0.979 | 0.99839 | 811 |
| 50 | 0.990 | 0.000429 | 0.68545 | 230,585 | 0.990 | 0.99642 | 1,805 |
| 85.0 (fitted) | 1.000 | 0.000431 | 0.68343 | 232,067 | 1.000 | 0.99348 | 3,287 |
| 100 | 1.000 | 0.000430 | 0.68247 | 232,768 | 1.000 | 0.99209 | 3,988 |
| 250 | 1.000 | 0.000415 | 0.67133 | 240,941 | 1.000 | 0.97588 | 12,161 |
| 500 | 1.000 | 0.000386 | 0.64641 | 259,206 | 1.000 | 0.93967 | 30,426 |
| 1000 | 1.000 | 0.000309 | 0.55801 | 324,011 | 1.000 | 0.81116 | 95,231 |

zh-ru: 3,263 links (16 without coordinates); 93,560,850 possible pairs, of which 6,603,538 are
always kept.

| T (km) | PC | PQ | RR | \|C\| all pairs | PC geo pairs | RR geo pairs | \|C\| geo pairs |
|---|---|---|---|---|---|---|---|
| 0.02 (fitted) | 1.000 | 0.000488 | 0.92853 | 6,687,233 | 1.000 | 0.99904 | 83,695 |
| 1 | 1.000 | 0.000488 | 0.92850 | 6,689,271 | 1.000 | 0.99901 | 85,733 |
| 5 | 1.000 | 0.000487 | 0.92833 | 6,705,339 | 1.000 | 0.99883 | 101,801 |
| 10 | 1.000 | 0.000486 | 0.92823 | 6,715,182 | 1.000 | 0.99872 | 111,644 |
| 25 | 1.000 | 0.000483 | 0.92780 | 6,754,879 | 1.000 | 0.99826 | 151,341 |
| 50 | 1.000 | 0.000477 | 0.92688 | 6,840,723 | 1.000 | 0.99727 | 237,185 |
| 100 | 1.000 | 0.000462 | 0.92448 | 7,066,000 | 1.000 | 0.99468 | 462,462 |
| 250 | 1.000 | 0.000418 | 0.91662 | 7,801,046 | 1.000 | 0.98623 | 1,197,508 |
| 500 | 1.000 | 0.000345 | 0.89900 | 9,449,319 | 1.000 | 0.96727 | 2,845,781 |
| 1000 | 1.000 | 0.000233 | 0.85051 | 13,986,265 | 1.000 | 0.91510 | 7,382,727 |

### Findings

- Gradient descent ends at the same value from all four starting points for MEHDIE and
  Pleiades-TM, a few km above the exact optimum because the smoothed cut-off blurs the edge. The
  shared fit stopped in a local optimum (45.5 km against 78.2 km; objective 0.9967 against 0.9969).
- The optimum is decided by a single link: it lies just past the farthest link. Most links are
  far closer.
- Among the geo pairs the threshold is very effective: at the fitted value it keeps every link
  and removes over 99 % of the pairs in all three test sets.
- Over all pairs geo alone is a weak block, because pairs without coordinates are always kept.
  It removes 20 % of the pairs in MEHDIE, 69 % in Pleiades-TM and 93 % on zh-ru.
- zh-ru fits to 0 km because the coordinates are identical on both sides.
- The thresholds are fitted and measured on the same links; there is no held-out check.

### Decision

One common threshold for all test sets, 100 km, used as a fixed setting and not as a fitted
value. It loses no link in any test set and has a margin over the farthest link seen (78 km).
Per-test-set thresholds were rejected: each would be fitted to one link, on the links it is
evaluated on, and the zh-ru value is an artefact of copied coordinates. The per-test-set
optima are a description of the data, not tuned parameters.

| Common threshold | MEHDIE PC | Pleiades-TM PC | zh-ru PC | \|C\| geo pairs (MEHDIE / Pleiades-TM / zh-ru) |
|---|---|---|---|---|
| 45.5 km (fitted on all three) | 1.000 | 0.990 | 1.000 | 284,315 / 1,662 / 221,198 |
| 50 km | 1.000 | 0.990 | 1.000 | 331,251 / 1,805 / 237,185 |
| 100 km (chosen) | 1.000 | 1.000 | 1.000 | 902,065 / 3,988 / 462,462 |

In the code: `CandidateGenerator(max_km=100)` is the default, `--max-km` defaults to 100, and
keeping pairs without coordinates is no longer an option.

---

## Experiment 8: which phonetic similarity

Decides pipeline part 2. Setup shared by experiments 8-10: pairs more than 100 km apart are
removed first (pairs without coordinates kept), then each record keeps its top k by the
similarity under test, from both sides (union). Each record has one title and one `title_ipa`
(the first, if there are several). Pairs with a similarity of 0 are never candidates.

All methods compare the two `title_ipa` strings. "Skeleton" means the vowels a, e, i, o, u are
removed first.

### MEHDIE

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| TF-IDF cosine, 2-3 grams (chosen) | 0.614 | 62,453 | 0.781 | 177,152 | 0.868 | 553,829 |
| TF-IDF cosine, 1-2 grams | 0.614 | 63,065 | 0.763 | 180,235 | 0.851 | 573,257 |
| TF-IDF cosine, 2-4 grams | 0.614 | 62,373 | 0.754 | 176,990 | 0.842 | 553,785 |
| TF-IDF cosine, 3 grams | 0.553 | 58,726 | 0.754 | 162,378 | 0.825 | 486,783 |
| Jaccard overlap, 2 grams | 0.658 | 62,923 | 0.789 | 179,293 | 0.842 | 566,578 |
| Jaccard overlap, 3 grams | 0.605 | 59,140 | 0.781 | 165,085 | 0.842 | 501,764 |
| Edit distance, normalised | 0.658 | 63,344 | 0.781 | 181,763 | 0.860 | 585,181 |
| Jaro-Winkler | 0.658 | 63,338 | 0.807 | 181,278 | 0.860 | 577,294 |
| Skeleton + TF-IDF cosine, 2-3 grams | 0.456 | 62,911 | 0.693 | 176,980 | 0.816 | 551,479 |
| Skeleton + edit distance | 0.535 | 63,564 | 0.728 | 181,051 | 0.886 | 577,731 |
| Skeleton + Jaro-Winkler | 0.500 | 63,657 | 0.658 | 180,365 | 0.789 | 569,590 |

### Pleiades-TM

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| TF-IDF cosine, 2-3 grams (chosen) | 0.790 | 2,985 | 0.820 | 8,853 | 0.850 | 29,160 |
| TF-IDF cosine, 1-2 grams | 0.780 | 2,983 | 0.810 | 8,872 | 0.840 | 29,444 |
| TF-IDF cosine, 2-4 grams | 0.800 | 2,979 | 0.820 | 8,867 | 0.840 | 29,147 |
| TF-IDF cosine, 3 grams | 0.790 | 2,821 | 0.820 | 7,380 | 0.850 | 16,374 |
| Jaccard overlap, 2 grams | 0.770 | 2,993 | 0.820 | 8,907 | 0.850 | 29,278 |
| Jaccard overlap, 3 grams | 0.780 | 2,830 | 0.840 | 7,430 | 0.850 | 16,533 |
| Edit distance, normalised | 0.680 | 3,011 | 0.740 | 8,943 | 0.760 | 29,590 |
| Jaro-Winkler | 0.700 | 2,988 | 0.720 | 8,898 | 0.760 | 29,446 |
| Skeleton + TF-IDF cosine, 2-3 grams | 0.770 | 2,993 | 0.820 | 8,837 | 0.840 | 27,840 |
| Skeleton + edit distance | 0.610 | 3,000 | 0.660 | 8,912 | 0.760 | 29,491 |
| Skeleton + Jaro-Winkler | 0.630 | 2,988 | 0.690 | 8,871 | 0.750 | 29,310 |

### zh-ru

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| TF-IDF cosine, 2-3 grams (chosen) | 0.435 | 19,923 | 0.573 | 59,502 | 0.699 | 195,163 |
| TF-IDF cosine, 1-2 grams | 0.423 | 19,882 | 0.553 | 59,485 | 0.694 | 198,221 |
| TF-IDF cosine, 2-4 grams | 0.433 | 19,881 | 0.572 | 59,445 | 0.700 | 195,259 |
| TF-IDF cosine, 3 grams | 0.390 | 18,077 | 0.493 | 49,090 | 0.543 | 127,326 |
| Jaccard overlap, 2 grams | 0.443 | 19,835 | 0.567 | 59,570 | 0.688 | 196,558 |
| Jaccard overlap, 3 grams | 0.392 | 18,118 | 0.490 | 49,546 | 0.539 | 130,020 |
| Edit distance, normalised | 0.438 | 19,809 | 0.559 | 59,839 | 0.697 | 199,831 |
| Jaro-Winkler | 0.429 | 19,729 | 0.536 | 59,281 | 0.680 | 198,452 |
| Skeleton + TF-IDF cosine, 2-3 grams | 0.344 | 19,839 | 0.477 | 58,395 | 0.622 | 177,767 |
| Skeleton + edit distance | 0.357 | 20,050 | 0.490 | 60,134 | 0.649 | 198,809 |
| Skeleton + Jaro-Winkler | 0.344 | 20,083 | 0.475 | 60,021 | 0.625 | 198,437 |

### Findings

- No alternative beats TF-IDF cosine on 2-3 grams on all three test sets. Jaro-Winkler is best in
  MEHDIE at k=3 (0.807 against 0.781) but 10 points worse in Pleiades-TM (0.720 against 0.820).
- Removing the vowels makes every method worse.
- Decision: keep TF-IDF cosine on 2-3 grams. It has no parameter left to fit.

---

## Experiment 9: which title similarity

Decides pipeline part 3. Same setup as experiment 8, but the methods compare the two titles.

Note on Pleiades-TM: in the minimized data both the Pleiades and the Trismegistos titles are in
Latin script, so this test set compares Latin with Latin. That is kept as it is.

### 9a: methods on the titles as written

Four language models (cosine of the embeddings) and six letter-based methods. The letter-based
methods get the titles lowercased and without accents, but not transliterated.

MEHDIE:

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE | 0.439 | 63,326 | 0.596 | 182,338 | 0.684 | 587,463 |
| multilingual-e5-large | 0.491 | 63,483 | 0.684 | 183,898 | 0.763 | 595,815 |
| bge-m3 | 0.351 | 63,330 | 0.544 | 181,704 | 0.658 | 581,836 |
| paraphrase-multilingual-mpnet-base-v2 | 0.070 | 65,314 | 0.088 | 193,551 | 0.167 | 639,672 |
| TF-IDF cosine, 2-3 grams | 0.000 | 21,423 | 0.000 | 61,918 | 0.000 | 193,420 |
| TF-IDF cosine, 1-2 grams | 0.000 | 66,082 | 0.000 | 196,827 | 0.018 | 649,852 |
| Jaccard overlap, 2 grams | 0.000 | 21,507 | 0.000 | 62,372 | 0.000 | 195,221 |
| Jaccard overlap, 3 grams | 0.000 | 20,271 | 0.000 | 56,513 | 0.000 | 169,421 |
| Edit distance, normalised | 0.000 | 41,213 | 0.000 | 122,209 | 0.000 | 396,511 |
| Jaro-Winkler | 0.000 | 41,156 | 0.000 | 121,815 | 0.000 | 395,522 |

Pleiades-TM:

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE | 0.800 | 3,005 | 0.860 | 8,954 | 0.920 | 29,618 |
| multilingual-e5-large | 0.840 | 3,001 | 0.880 | 8,953 | 0.930 | 29,699 |
| bge-m3 | 0.820 | 3,002 | 0.890 | 8,938 | 0.910 | 29,610 |
| paraphrase-multilingual-mpnet-base-v2 | 0.800 | 3,021 | 0.810 | 9,071 | 0.870 | 30,395 |
| TF-IDF cosine, 2-3 grams | 0.870 | 2,988 | 0.900 | 8,893 | 0.920 | 29,312 |
| TF-IDF cosine, 1-2 grams | 0.840 | 2,987 | 0.880 | 8,909 | 0.910 | 29,580 |
| Jaccard overlap, 2 grams | 0.850 | 2,996 | 0.880 | 8,918 | 0.910 | 29,383 |
| Jaccard overlap, 3 grams | 0.880 | 2,872 | 0.900 | 7,877 | 0.910 | 17,540 |
| Edit distance, normalised | 0.730 | 3,017 | 0.800 | 8,960 | 0.890 | 29,607 |
| Jaro-Winkler | 0.750 | 2,992 | 0.770 | 8,921 | 0.820 | 29,508 |

zh-ru:

| Method | PC k=1 | \|C\| k=1 | PC k=3 | \|C\| k=3 | PC k=10 | \|C\| k=10 |
|---|---|---|---|---|---|---|
| LaBSE | 0.587 | 19,452 | 0.721 | 59,034 | 0.849 | 198,972 |
| multilingual-e5-large | 0.506 | 19,591 | 0.614 | 59,381 | 0.738 | 199,729 |
| bge-m3 | 0.494 | 19,577 | 0.622 | 58,944 | 0.758 | 197,289 |
| paraphrase-multilingual-mpnet-base-v2 | 0.244 | 20,411 | 0.361 | 61,263 | 0.580 | 204,191 |
| TF-IDF cosine, 2-3 grams | 0.000 | 0 | 0.000 | 0 | 0.000 | 0 |
| TF-IDF cosine, 1-2 grams | 0.003 | 20,984 | 0.037 | 62,942 | 0.110 | 209,679 |
| Jaccard overlap, 2 grams | 0.000 | 0 | 0.000 | 0 | 0.000 | 0 |
| Jaccard overlap, 3 grams | 0.000 | 0 | 0.000 | 0 | 0.000 | 0 |
| Edit distance, normalised | 0.010 | 513 | 0.012 | 822 | 0.012 | 1,056 |
| Jaro-Winkler | 0.010 | 564 | 0.012 | 986 | 0.012 | 1,372 |

### 9b: n-gram length 1 to 6

Whether longer letter pieces help. Titles as written, single n-gram lengths. Only Pleiades-TM
is shown: in MEHDIE and zh-ru the two sides are in different scripts and share no letters, so
PC is 0 at every length from 2 up.

| n | Jaccard PC k=1 | Jaccard PC k=3 | Jaccard PC k=10 | Jaccard \|C\| k=10 | TF-IDF PC k=1 | TF-IDF PC k=3 | TF-IDF PC k=10 | TF-IDF \|C\| k=10 |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.610 | 0.710 | 0.800 | 29,653 | 0.750 | 0.800 | 0.900 | 29,485 |
| 2 | 0.850 | 0.880 | 0.910 | 29,383 | 0.840 | 0.880 | 0.920 | 29,307 |
| 3 | 0.880 | 0.900 | 0.910 | 17,540 | 0.880 | 0.900 | 0.910 | 17,431 |
| 4 | 0.850 | 0.870 | 0.880 | 4,552 | 0.850 | 0.870 | 0.880 | 4,526 |
| 5 | 0.810 | 0.810 | 0.810 | 1,282 | 0.810 | 0.810 | 0.810 | 1,276 |
| 6 | 0.780 | 0.780 | 0.780 | 664 | 0.780 | 0.780 | 0.780 | 663 |

### 9c: letter-based methods on transliterated titles

The titles are first transliterated to Latin letters, so that titles in different scripts
share letters. Two transliteration libraries were tried, `unidecode` and `anyascii`. `anyascii`
is better in MEHDIE and on zh-ru in almost every row (edit distance at k=3: 0.719 against 0.535
in MEHDIE, 0.579 against 0.517 on zh-ru), so only `anyascii` is shown. Pleiades-TM is already
in Latin script, so transliteration changes nothing there (see 9a).

| Method (on `anyascii` titles) | MEHDIE PC k=1 | MEHDIE PC k=3 | MEHDIE PC k=10 | zh-ru PC k=1 | zh-ru PC k=3 | zh-ru PC k=10 |
|---|---|---|---|---|---|---|
| TF-IDF cosine, 2-3 grams | 0.298 | 0.439 | 0.605 | 0.425 | 0.576 | 0.701 |
| TF-IDF cosine, 1-2 grams | 0.307 | 0.491 | 0.675 | 0.441 | 0.583 | 0.713 |
| Jaccard overlap, 2 grams | 0.342 | 0.544 | 0.798 | 0.449 | 0.579 | 0.698 |
| Jaccard overlap, 3 grams | 0.254 | 0.404 | 0.518 | 0.379 | 0.481 | 0.519 |
| Edit distance, normalised | 0.482 | 0.719 | 0.868 | 0.454 | 0.579 | 0.720 |
| Jaro-Winkler | 0.325 | 0.658 | 0.798 | 0.454 | 0.570 | 0.711 |

\|C\| is about 64,000 / 186,000 / 597,000 in MEHDIE and 20,000 / 60,000 / 200,000 on zh-ru at
k = 1 / 3 / 10 for the methods without 3-grams.

### 9d: Pleiades-TM with Greek names on the Pleiades side (side test)

To see what a Greek-to-Latin comparison would give, the Pleiades title was replaced inside the
test script by the record's first ancient Greek name (2,885 of 2,909 records). The data was not
changed and this variant is not used.

| Method | PC k=1 | PC k=3 | PC k=10 |
|---|---|---|---|
| LaBSE | 0.620 | 0.680 | 0.750 |
| multilingual-e5-large | 0.690 | 0.790 | 0.820 |
| bge-m3 | 0.650 | 0.760 | 0.820 |
| TF-IDF cosine, 2-3 grams, transliterated | 0.680 | 0.760 | 0.800 |
| Jaccard overlap, 2 grams, transliterated | 0.710 | 0.770 | 0.790 |
| Edit distance, transliterated | 0.710 | 0.750 | 0.780 |

### Findings

- Letter-based methods on the titles as written only work where both sides share a script
  (Pleiades-TM). Across scripts they find nothing.
- N-gram length: 3 is the peak. Longer pieces give far fewer candidates but lose links, and at
  5 and 6 a larger k no longer adds anything.
- With transliteration the letter-based methods work across scripts. Edit distance is the best
  of them. A transliterated title carries much the same information as `title_ipa`: the
  numbers are close to those of experiment 8.
- No title method is best everywhere at k=3: edit distance on transliterated titles in MEHDIE
  (0.719), TF-IDF or Jaccard on 3-grams in Pleiades-TM (0.900), LaBSE on zh-ru (0.721).
- Shortlist for experiment 10: LaBSE, multilingual-e5-large and edit distance on transliterated
  titles.

---

## Experiment 10: combination

Decides pipeline part 4 and the final title method. Same setup as experiment 8.

`score = w * title similarity + (1 - w) * phonetic similarity`

- Phonetic similarity: TF-IDF cosine on 2-3 grams of `title_ipa` (experiment 8).
- Title similarity: each of the three shortlisted methods from experiment 9.
- `w` was searched exhaustively from 0 to 1 in steps of 0.1 instead of by gradient descent: it
  is one number, and experiment 5 showed that fitted weights do not transfer between test sets.
- w = 0 is the phonetic similarity alone, w = 1 the title similarity alone.

### Mean PC over the three test sets

| Title method | w | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|---|
| Phonetic only | 0.0 | 0.613 | 0.725 | 0.759 | 0.806 |
| LaBSE | 0.1 | 0.631 | 0.753 | 0.791 | 0.838 |
| LaBSE | 0.2 | 0.672 | 0.784 | 0.819 | 0.861 |
| LaBSE | 0.3 | 0.672 | 0.796 | 0.832 | 0.891 |
| LaBSE | 0.4 | 0.701 | 0.813 | 0.845 | 0.899 |
| LaBSE | 0.5 (chosen) | 0.720 | 0.823 | 0.851 | 0.895 |
| LaBSE | 0.6 | 0.726 | 0.820 | 0.852 | 0.893 |
| LaBSE | 0.7 | 0.739 | 0.822 | 0.845 | 0.883 |
| LaBSE | 0.8 | 0.702 | 0.801 | 0.838 | 0.883 |
| LaBSE | 0.9 | 0.668 | 0.773 | 0.815 | 0.858 |
| LaBSE | 1.0 | 0.609 | 0.726 | 0.766 | 0.818 |
| multilingual-e5-large | 0.1 | 0.623 | 0.722 | 0.771 | 0.815 |
| multilingual-e5-large | 0.2 | 0.623 | 0.728 | 0.777 | 0.820 |
| multilingual-e5-large | 0.3 | 0.633 | 0.746 | 0.790 | 0.826 |
| multilingual-e5-large | 0.4 | 0.653 | 0.754 | 0.793 | 0.844 |
| multilingual-e5-large | 0.5 | 0.656 | 0.770 | 0.811 | 0.851 |
| multilingual-e5-large | 0.6 | 0.669 | 0.790 | 0.822 | 0.857 |
| multilingual-e5-large | 0.7 | 0.691 | 0.803 | 0.837 | 0.865 |
| multilingual-e5-large | 0.8 | 0.703 | 0.814 | 0.838 | 0.866 |
| multilingual-e5-large | 0.9 | 0.712 | 0.810 | 0.829 | 0.863 |
| multilingual-e5-large | 1.0 | 0.612 | 0.726 | 0.771 | 0.810 |
| Edit distance, transliterated | 0.1 | 0.625 | 0.748 | 0.790 | 0.816 |
| Edit distance, transliterated | 0.2 | 0.643 | 0.766 | 0.799 | 0.825 |
| Edit distance, transliterated | 0.3 | 0.670 | 0.769 | 0.799 | 0.845 |
| Edit distance, transliterated | 0.4 | 0.673 | 0.777 | 0.802 | 0.852 |
| Edit distance, transliterated | 0.5 | 0.677 | 0.786 | 0.816 | 0.857 |
| Edit distance, transliterated | 0.6 | 0.677 | 0.786 | 0.821 | 0.857 |
| Edit distance, transliterated | 0.7 | 0.668 | 0.791 | 0.819 | 0.859 |
| Edit distance, transliterated | 0.8 | 0.661 | 0.769 | 0.808 | 0.853 |
| Edit distance, transliterated | 0.9 | 0.649 | 0.752 | 0.794 | 0.845 |
| Edit distance, transliterated | 1.0 | 0.556 | 0.699 | 0.750 | 0.826 |

### Per test set, each title method at its best weight

| Title method | w | MEHDIE PC k=3 | MEHDIE PC k=10 | Pleiades-TM PC k=3 | Pleiades-TM PC k=10 | zh-ru PC k=3 | zh-ru PC k=10 |
|---|---|---|---|---|---|---|---|
| Phonetic only | 0.0 | 0.781 | 0.868 | 0.820 | 0.850 | 0.573 | 0.699 |
| LaBSE | 0.5 | 0.816 | 0.904 | 0.890 | 0.920 | 0.763 | 0.861 |
| multilingual-e5-large | 0.8 | 0.825 | 0.877 | 0.910 | 0.920 | 0.707 | 0.802 |
| Edit distance, transliterated | 0.7 | 0.877 | 0.921 | 0.880 | 0.920 | 0.616 | 0.737 |

### k, with LaBSE and w = 0.5

| k | MEHDIE PC | MEHDIE \|C\| | Pleiades-TM PC | Pleiades-TM \|C\| | zh-ru PC | zh-ru \|C\| |
|---|---|---|---|---|---|---|
| 1 | 0.658 | 63,303 | 0.850 | 2,989 | 0.653 | 19,297 |
| 3 | 0.816 | 181,700 | 0.890 | 8,905 | 0.763 | 58,554 |
| 5 (chosen) | 0.860 | 297,689 | 0.890 | 14,802 | 0.804 | 98,216 |
| 10 | 0.904 | 581,300 | 0.920 | 29,472 | 0.861 | 197,698 |

### Score threshold, with LaBSE, w = 0.5 and k = 5

A candidate is kept only if its score is at least the threshold.

| Score at least | MEHDIE PC | MEHDIE \|C\| | Pleiades-TM PC | Pleiades-TM \|C\| | zh-ru PC | zh-ru \|C\| |
|---|---|---|---|---|---|---|
| none (chosen) | 0.860 | 297,689 | 0.890 | 14,802 | 0.804 | 98,216 |
| 0.2 | 0.851 | 284,719 | 0.890 | 12,169 | 0.789 | 85,742 |
| 0.3 | 0.842 | 242,313 | 0.870 | 3,318 | 0.646 | 35,771 |
| 0.35 | 0.833 | 204,564 | 0.830 | 1,462 | 0.507 | 16,136 |
| 0.4 | 0.816 | 150,290 | 0.780 | 670 | 0.373 | 7,378 |
| 0.5 | 0.693 | 54,385 | 0.740 | 227 | 0.173 | 1,448 |

### Findings

- Every combination beats both of its parts alone, for all three title methods.
- LaBSE has the best mean PC and is flat between w = 0.4 and 0.7, so w = 0.5 is not a sensitive
  choice.
- The best title method differs per test set: edit distance on transliterated titles in MEHDIE,
  multilingual-e5-large in Pleiades-TM, LaBSE on zh-ru. LaBSE is chosen because it is never far
  behind and is clearly best on zh-ru, the weakest test set.
- No common score threshold works. At 0.3 Pleiades-TM loses 2 points of PC for a quarter of the
  candidates, but zh-ru loses 16 points: true zh-ru pairs score low on both similarities.
- Compared with experiment 3: with the distance in the score (geo bonus) PC at k=3 was 0.912 /
  1.000 / 0.975; with distance only as a filter it is 0.816 / 0.890 / 0.763. Inside 100 km the
  distance no longer helps rank the candidates. Keeping distance out of the score was a
  deliberate choice.
- The weight, k and the choice of title method were picked on the same links they are measured
  on; there is no held-out check.

### Decision

LaBSE as the title similarity, w = 0.5, k = 5, union, no score threshold. Implemented in
`pipeline.py`.

---

## Experiment 11: the five methods in `methods/` in the pipeline

Experiments 8-10 used loose scripts, and only TFIDF_kNN and LM_kNN_search were in them in
substance. This experiment runs all five methods of `methods/` in the pipeline setup.

### 11a: each method alone behind the 100 km filter

Run with `run_candidate_generation.py`, which now gives a method only the title (no name
variants) or the IPA of the title, and applies the geo filter first. All rows: `sweep_pipeline.csv`.

```
python run_candidate_generation.py --full --phonetic both --tau 0 1 --k 1 3 5 10 \
    --minhash-threshold 0.2 0.3 0.5 0.7 --qgram-t 0.4 0.6 0.8 --out results/sweep_pipeline.csv
```

Each method at the setting with its highest PC. "title" is the title as written.

| Method | Input | Setting | MEHDIE PC | MEHDIE \|C\| | Pleiades-TM PC | Pleiades-TM \|C\| | zh-ru PC | zh-ru \|C\| |
|---|---|---|---|---|---|---|---|---|
| Q_grams | ipa | t=0.4 | 0.711 | 335,019 | 0.480 | 576 | 0.111 | 7,036 |
| Q_grams | title | t=0.4 | 0.000 | 80,507 | 0.540 | 523 | 0.000 | 0 |
| PassJoin | ipa | tau=1 | 0.658 | 896,736 | 0.420 | 494 | 0.059 | 6,283 |
| PassJoin | title | tau=1 | 0.000 | 304,660 | 0.520 | 404 | 0.001 | 1,076 |
| MinHash_LSH | ipa | thr=0.2 | 0.746 | 3,436,665 | 0.770 | 3,565 | 0.236 | 56,493 |
| MinHash_LSH | title | thr=0.2 | 0.000 | 296,342 | 0.800 | 2,961 | 0.000 | 0 |
| TFIDF_kNN | ipa | k=10 | 0.868 | 553,822 | 0.860 | 26,721 | 0.699 | 195,156 |
| TFIDF_kNN | title | k=10 | 0.000 | 193,364 | 0.910 | 29,285 | 0.000 | 0 |
| LM_kNN_search | title | k=10 | 0.684 | 587,600 | 0.910 | 29,587 | 0.849 | 198,975 |

### 11b: each method as the text score in the combined score

`score = w * text score + (1 - w) * phonetic score`, each record keeps its top k (union), behind
the 100 km filter, as in experiment 10. The phonetic score is TF-IDF cosine on `title_ipa`.
Loose script.

Q_grams, MinHash_LSH and PassJoin answer yes or no per pair, so each is given the score its
yes/no is based on. The four letter-based methods get the titles transliterated to Latin
letters (`anyascii`); without that they score 0 across scripts (11a).

| Text method | Text score |
|---|---|
| LM_kNN_search | LaBSE cosine |
| TFIDF_kNN | TF-IDF cosine on 2-3 grams |
| Q_grams | Shared 3-grams divided by the 3-grams of the longer title |
| MinHash_LSH | Jaccard overlap of the 3-grams |
| PassJoin | Edit distance scaled to 0-1 |

Mean PC over the three test sets, each method at its best weight (by k=3) and alone (w = 1):

| Text method | w | k=1 | k=3 | k=5 | k=10 | Alone, k=3 |
|---|---|---|---|---|---|---|
| Phonetic score only | 0.0 | 0.613 | 0.725 | 0.759 | 0.806 | |
| LM_kNN_search | 0.5 | 0.720 | 0.823 | 0.851 | 0.895 | 0.726 |
| PassJoin | 0.7 | 0.668 | 0.791 | 0.819 | 0.859 | 0.699 |
| TFIDF_kNN | 0.6 | 0.645 | 0.767 | 0.797 | 0.827 | 0.638 |
| MinHash_LSH | 0.7 | 0.641 | 0.757 | 0.783 | 0.824 | 0.598 |
| Q_grams | 0.5 | 0.633 | 0.749 | 0.776 | 0.808 | 0.516 |

Per test set at w = 0.5:

| Text method | MEHDIE PC k=5 | MEHDIE \|C\| k=5 | Pleiades-TM PC k=5 | Pleiades-TM \|C\| k=5 | zh-ru PC k=5 | zh-ru \|C\| k=5 |
|---|---|---|---|---|---|---|
| Phonetic score only | 0.825 | 287,846 | 0.820 | 14,733 | 0.632 | 98,934 |
| LM_kNN_search | 0.860 | 297,689 | 0.890 | 14,802 | 0.804 | 98,216 |
| PassJoin | 0.904 | 297,548 | 0.870 | 14,812 | 0.673 | 99,222 |
| TFIDF_kNN | 0.842 | 297,587 | 0.900 | 14,793 | 0.644 | 99,195 |
| MinHash_LSH | 0.816 | 292,989 | 0.900 | 14,787 | 0.627 | 99,328 |
| Q_grams | 0.816 | 292,177 | 0.880 | 14,786 | 0.631 | 99,220 |

### Findings

- Alone and on titles as written, the four letter-based methods find nothing across scripts.
  On `title_ipa` the three yes/no methods stay far below the kNN methods on zh-ru.
- In the combined score LM_kNN_search is the best text method on average and the only one
  that lifts zh-ru (0.632 to 0.804 at k=5). The decision from experiment 10 stands.
- PassJoin's score is the best in MEHDIE (0.904 at k=5).
- TFIDF_kNN, MinHash_LSH and Q_grams add little to the phonetic score in MEHDIE and on zh-ru:
  a transliterated title carries nearly the same information as `title_ipa`.

---

## Experiment 12: every parameter of the letter-based methods

Experiment 11a varied one parameter per method. Here every tunable parameter of Q_grams,
MinHash_LSH, PassJoin and TFIDF_kNN is varied, on `title_ipa` behind the 100 km filter, full
data. All rows: `sweep_parameters.csv`.

    python run_candidate_generation.py --full --phonetic on --methods <method> ...
      Q_grams      --qgram-q 2 3 4 --qgram-t 0.4 0.6 0.8          (max_keys 500)
                   --qgram-q 3 --qgram-t 0.4 0.6 --qgram-max-keys 100 2000
      MinHash_LSH  --minhash-n 2 3 4 --minhash-threshold 0.2 0.3 0.5 0.7   (num_perm 128)
                   --minhash-n 3 --minhash-threshold 0.2 0.3 --minhash-num-perm 64 256
      PassJoin     --tau 0 1 2
      TFIDF_kNN    --tfidf-ngrams 1-2 1-3 2-3 2-4 3-3 --k 1 3 5 10

Piece length and threshold are fully crossed. Signature size (num_perm) and key cap (max_keys)
are varied at the default piece length 3 only. Each run had a time limit of 20 to 25 minutes.
Two settings did not finish on MEHDIE and have no result: MinHash_LSH n=2, threshold 0.2 (also
ran for over a day without finishing in an earlier attempt) and PassJoin tau=2. The `seconds`
column is not reliable for one zh-ru TFIDF_kNN row (2-4, k=1): the computer slept during it.

### Q_grams: piece length q and threshold t (max_keys 500)

| q | t | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|---|
| 2 | 0.4 | 0.860 | 2,690,908 | 0.480 | 2,651 | 0.177 | 52,986 |
| 2 | 0.6 | 0.728 | 360,224 | 0.450 | 267 | 0.088 | 2,131 |
| 2 | 0.8 | 0.588 | 22,238 | 0.400 | 59 | 0.036 | 236 |
| 3 | 0.4 | 0.711 | 335,019 | 0.480 | 576 | 0.111 | 7,036 |
| 3 | 0.6 | 0.588 | 84,038 | 0.440 | 126 | 0.055 | 631 |
| 3 | 0.8 | 0.456 | 13,400 | 0.390 | 49 | 0.023 | 139 |
| 4 | 0.4 | 0.605 | 59,915 | 0.440 | 184 | 0.077 | 856 |
| 4 | 0.6 | 0.561 | 15,159 | 0.420 | 73 | 0.039 | 267 |
| 4 | 0.8 | 0.439 | 5,551 | 0.370 | 45 | 0.019 | 112 |

### Q_grams: key cap max_keys (q = 3)

| t | max_keys | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|---|
| 0.4 | 100 | 0.711 | 264,010 | 0.410 | 379 | 0.071 | 5,612 |
| 0.4 | 500 | 0.711 | 335,019 | 0.480 | 576 | 0.111 | 7,036 |
| 0.4 | 2000 | 0.711 | 337,197 | 0.530 | 615 | 0.124 | 7,110 |
| 0.6 | 100 | 0.588 | 82,266 | 0.410 | 107 | 0.044 | 571 |
| 0.6 | 500 | 0.588 | 84,038 | 0.440 | 126 | 0.055 | 631 |
| 0.6 | 2000 | 0.588 | 84,115 | 0.450 | 129 | 0.058 | 643 |

### MinHash_LSH: piece length n and threshold (num_perm 128)

| n | threshold | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|---|
| 2 | 0.2 | did not finish | | 0.890 | 61,266 | 0.452 | 355,201 |
| 2 | 0.3 | 0.851 | 3,079,454 | 0.790 | 8,922 | 0.266 | 58,055 |
| 2 | 0.5 | 0.640 | 110,755 | 0.580 | 444 | 0.077 | 1,815 |
| 2 | 0.7 | 0.404 | 4,959 | 0.350 | 44 | 0.019 | 110 |
| 3 | 0.2 | 0.746 | 3,436,665 | 0.770 | 3,565 | 0.236 | 56,493 |
| 3 | 0.3 | 0.632 | 306,168 | 0.710 | 790 | 0.120 | 6,685 |
| 3 | 0.5 | 0.518 | 16,654 | 0.490 | 98 | 0.037 | 648 |
| 3 | 0.7 | 0.351 | 2,690 | 0.350 | 41 | 0.011 | 45 |
| 4 | 0.2 | 0.623 | 238,568 | 0.730 | 935 | 0.132 | 10,534 |
| 4 | 0.3 | 0.561 | 67,855 | 0.660 | 282 | 0.069 | 1,754 |
| 4 | 0.5 | 0.430 | 5,334 | 0.430 | 82 | 0.024 | 125 |
| 4 | 0.7 | 0.360 | 2,425 | 0.330 | 39 | 0.010 | 37 |

### MinHash_LSH: signature size num_perm (n = 3)

| threshold | num_perm | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|---|
| 0.2 | 64 | 0.737 | 1,919,005 | 0.780 | 3,909 | 0.217 | 44,146 |
| 0.2 | 128 | 0.746 | 3,436,665 | 0.770 | 3,565 | 0.236 | 56,493 |
| 0.2 | 256 | 0.728 | 755,069 | 0.770 | 1,712 | 0.178 | 24,670 |
| 0.3 | 64 | 0.614 | 166,710 | 0.640 | 481 | 0.098 | 4,483 |
| 0.3 | 128 | 0.632 | 306,168 | 0.710 | 790 | 0.120 | 6,685 |
| 0.3 | 256 | 0.605 | 151,372 | 0.690 | 573 | 0.089 | 1,753 |

### PassJoin: edits allowed tau

| tau | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|
| 0 | 0.351 | 2,345 | 0.330 | 36 | 0.009 | 31 |
| 1 | 0.658 | 896,736 | 0.420 | 494 | 0.059 | 6,283 |
| 2 | did not finish | | 0.460 | 8,354 | 0.157 | 152,482 |

### TFIDF_kNN: piece lengths and k

| pieces | k | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| |
|---|---|---|---|---|---|---|---|
| 1-2 | 1 | 0.640 | 63,060 | 0.800 | 3,049 | 0.422 | 19,884 |
| 1-2 | 3 | 0.772 | 180,239 | 0.840 | 8,575 | 0.555 | 59,486 |
| 1-2 | 5 | 0.807 | 294,339 | 0.850 | 13,946 | 0.615 | 99,156 |
| 1-2 | 10 | 0.851 | 573,247 | 0.860 | 26,896 | 0.693 | 198,222 |
| 1-3 | 1 | 0.623 | 62,848 | 0.800 | 3,052 | 0.428 | 19,907 |
| 1-3 | 3 | 0.763 | 179,038 | 0.840 | 8,490 | 0.562 | 59,553 |
| 1-3 | 5 | 0.833 | 292,110 | 0.840 | 13,783 | 0.615 | 99,212 |
| 1-3 | 10 | 0.868 | 568,778 | 0.860 | 26,813 | 0.693 | 198,210 |
| 2-3 | 1 | 0.596 | 62,447 | 0.800 | 3,053 | 0.433 | 19,921 |
| 2-3 | 3 | 0.763 | 177,165 | 0.840 | 8,448 | 0.574 | 59,515 |
| 2-3 | 5 | 0.825 | 287,836 | 0.840 | 13,747 | 0.633 | 98,931 |
| 2-3 | 10 | 0.868 | 553,822 | 0.860 | 26,721 | 0.699 | 195,156 |
| 2-4 | 1 | 0.596 | 62,367 | 0.810 | 3,043 | 0.433 | 19,876 |
| 2-4 | 3 | 0.763 | 176,983 | 0.840 | 8,444 | 0.573 | 59,447 |
| 2-4 | 5 | 0.816 | 287,684 | 0.840 | 13,726 | 0.629 | 98,904 |
| 2-4 | 10 | 0.842 | 553,779 | 0.840 | 26,685 | 0.700 | 195,252 |
| 3 | 1 | 0.570 | 58,716 | 0.800 | 2,924 | 0.389 | 18,076 |
| 3 | 3 | 0.746 | 162,384 | 0.840 | 7,449 | 0.493 | 49,096 |
| 3 | 5 | 0.789 | 259,110 | 0.840 | 10,946 | 0.522 | 75,791 |
| 3 | 10 | 0.825 | 486,773 | 0.860 | 17,052 | 0.543 | 127,323 |

### Highest PC per method

| Method | MEHDIE | \|C\| | Pleiades-TM | \|C\| | zh-ru | \|C\| |
|---|---|---|---|---|---|---|
| TFIDF_kNN | 0.868 (2-3 or 1-3, k=10) | 553,822 | 0.860 (k=10) | 26,721 | 0.700 (2-4, k=10) | 195,252 |
| MinHash_LSH | 0.851 (n=2, thr 0.3) | 3,079,454 | 0.890 (n=2, thr 0.2) | 61,266 | 0.452 (n=2, thr 0.2) | 355,201 |
| Q_grams | 0.860 (q=2, t=0.4) | 2,690,908 | 0.530 (q=3, t=0.4, keys 2000) | 615 | 0.177 (q=2, t=0.4) | 52,986 |
| PassJoin | 0.658 (tau=1) | 896,736 | 0.460 (tau=2) | 8,354 | 0.157 (tau=2) | 152,482 |

### Findings

- Piece length matters for the yes/no methods. Piece length 2 lifts Q_grams in MEHDIE from
  0.711 to 0.860 and MinHash_LSH from 0.746 to 0.851, on Pleiades-TM MinHash_LSH from 0.770 to
  0.890, and on zh-ru MinHash_LSH from 0.236 to 0.452. The gains cost 6 to 17 times as many
  candidates, except MinHash_LSH in MEHDIE, where n=2 at threshold 0.3 gives slightly fewer
  candidates than n=3 at threshold 0.2 (3.08 against 3.44 million).
- MinHash_LSH with n=2, threshold 0.2 has the highest PC on Pleiades-TM (0.890 against 0.860 for
  TFIDF_kNN), with 61,266 candidates against 26,721, which is 8 % of all pairs.
- For a similar number of candidates TFIDF_kNN is ahead on all three test sets, e.g. Pleiades-TM
  about 8,500 candidates: 0.840 against 0.790; MEHDIE about 300,000 to 360,000: 0.825 against
  0.728 (Q_grams) and 0.632 (MinHash_LSH). On zh-ru no other method comes near (0.699 against
  0.452 with nearly twice the candidates).
- Signature size does not help: 64 and 256 are at or below 128 except Pleiades-TM at threshold
  0.2 (0.780 with 64). The candidate counts move a lot between sizes at the same threshold.
- A larger key cap helps Q_grams on Pleiades-TM (0.480 to 0.530) and slightly on zh-ru, not in
  MEHDIE. It was not combined with q=2.
- For TFIDF_kNN the piece lengths 1-2, 1-3, 2-3 and 2-4 are within 0.03 of each other; only
  3 alone is clearly worse on zh-ru. The default 2-3 is kept.
- The choice of TFIDF_kNN for the phonetic score stands.

---

## Experiment 13: combined score with each phonetic method at its best setting

Experiment 10 fitted the combined score with TF-IDF as the phonetic part only. Here the phonetic
part is each of the four methods, at the piece length that was best in experiment 12 and at the
default. Behind the 100 km filter: score = w * LaBSE title similarity + (1 - w) * phonetic
similarity; each record keeps its top k (score > 0), union of both sides. All rows (w from 0 to
1, k = 1, 3, 5, 10): `sweep_combination.csv`.

The phonetic similarity is the score behind each method, on `title_ipa`: TF-IDF cosine
(TFIDF_kNN), Jaccard overlap of the padded n-grams (MinHash_LSH), shared q-grams over the q-grams
of the longer title (Q_grams), edit distance scaled to 0-1 (PassJoin). Only the piece length
shapes these scores. Threshold, t, tau and the method's own k are cut-offs for a method running
alone; here the top k of the combined score replaces them, so PassJoin has no setting to vary.

### Pipeline setting: w = 0.5, k = 5

| Phonetic method | MEHDIE PC | \|C\| | Pleiades-TM PC | \|C\| | zh-ru PC | \|C\| | Mean PC |
|---|---|---|---|---|---|---|---|
| TFIDF_kNN, pieces 2-3 (pipeline) | 0.860 | 297,689 | 0.890 | 14,802 | 0.804 | 98,216 | 0.851 |
| TFIDF_kNN, pieces 1-3 | 0.860 | 298,274 | 0.890 | 14,802 | 0.804 | 98,266 | 0.851 |
| TFIDF_kNN, pieces 2-4 | 0.851 | 296,286 | 0.890 | 14,813 | 0.806 | 98,176 | 0.849 |
| MinHash_LSH, n=2 | 0.877 | 300,153 | 0.880 | 14,845 | 0.794 | 98,579 | 0.850 |
| MinHash_LSH, n=3 | 0.877 | 299,004 | 0.890 | 14,833 | 0.804 | 98,600 | 0.857 |
| Q_grams, q=2 | 0.868 | 299,744 | 0.880 | 14,830 | 0.785 | 98,757 | 0.844 |
| Q_grams, q=3 | 0.833 | 297,655 | 0.890 | 14,828 | 0.797 | 98,539 | 0.840 |
| PassJoin | 0.886 | 300,249 | 0.880 | 14,876 | 0.794 | 98,659 | 0.853 |
| Title only (w = 1) | 0.640 | | 0.880 | | 0.777 | | 0.766 |

### Each method at its own best weight (by mean PC at k = 5)

| Phonetic method | Best w | Mean PC k=1 | k=3 | k=5 | k=10 | k=5: MEHDIE / Pleiades-TM / zh-ru |
|---|---|---|---|---|---|---|
| TFIDF_kNN, pieces 2-3 | 0.6 | 0.726 | 0.820 | 0.852 | 0.893 | 0.868 / 0.880 / 0.807 |
| TFIDF_kNN, pieces 1-3 | 0.6 | 0.736 | 0.822 | 0.851 | 0.889 | 0.868 / 0.880 / 0.806 |
| TFIDF_kNN, pieces 2-4 | 0.6 | 0.714 | 0.822 | 0.849 | 0.889 | 0.851 / 0.890 / 0.807 |
| MinHash_LSH, n=2 | 0.6 | 0.736 | 0.831 | 0.853 | 0.885 | 0.877 / 0.880 / 0.801 |
| MinHash_LSH, n=3 | 0.5 | 0.732 | 0.827 | 0.857 | 0.895 | 0.877 / 0.890 / 0.804 |
| Q_grams, q=2 | 0.6 | 0.714 | 0.820 | 0.853 | 0.882 | 0.886 / 0.880 / 0.793 |
| Q_grams, q=3 | 0.7 | 0.723 | 0.806 | 0.841 | 0.868 | 0.825 / 0.900 / 0.799 |
| PassJoin | 0.7 | 0.700 | 0.825 | 0.858 | 0.892 | 0.877 / 0.890 / 0.806 |

### Findings

- In the combined score the phonetic methods are nearly interchangeable. At k = 5 the best
  weights give a mean PC between 0.841 and 0.858. One ground truth link is 0.009 PC in MEHDIE
  and 0.010 on Pleiades-TM, so the spread is one to three links per test set.
- The large differences between the methods alone (experiment 12, e.g. zh-ru 0.699 against 0.157)
  disappear: the LaBSE title score carries zh-ru, and the phonetic part only has to rank within
  the pairs that are already close.
- The best piece length alone is not the best in the combination: MinHash_LSH is better with
  n=3 than n=2 (0.857 against 0.853), Q_grams better with q=2 (0.853 against 0.841).
- PassJoin (0.858) and MinHash_LSH n=3 (0.857) are marginally above TFIDF_kNN (0.852) at k = 5;
  at k = 10 TFIDF_kNN and MinHash_LSH n=3 are highest (0.893 to 0.895).
- No method is better on all three test sets, and the differences are within a few links.
  TFIDF_kNN with pieces 2-3 is kept as the phonetic score.
- The TFIDF_kNN 2-3 row differs slightly from `pipeline.py`: at most 8 candidates, and one link
  in MEHDIE (0.860 against 0.868), as in experiment 10.

---

## Summary: best result per test set

| Test set | Best existing method (experiment 1, no geo) | PC | \|C\| | New method, k=3, score at least 1.2 | PC | \|C\| |
|---|---|---|---|---|---|---|
| MEHDIE | TFIDF_kNN on IPA, k=10 | 0.798 | 575,873 | LaBSE + TFIDF + geo bonus | 0.895 | 21,112 |
| Pleiades-TM | TFIDF_kNN on names, k=10 | 0.900 | 53,016 | LaBSE + TFIDF + geo bonus | 0.920 | 301 |
| zh-ru | LM_kNN_search, k=10 | 0.663 | 279,559 | LaBSE + TFIDF + geo bonus | 0.965 | 17,954 |

The existing methods here use the title plus all name variants; the new method uses only the
title, `title_ipa` and coordinates.

The "new method" in this table is the combined score with the geo bonus from experiments 3 and
4. It is not the final pipeline: the final pipeline uses distance only as a filter (see "The
pipeline the experiments led to" at the top) and reaches 0.868 / 0.890 / 0.804 with 297,697 /
14,802 / 98,218 candidates.
