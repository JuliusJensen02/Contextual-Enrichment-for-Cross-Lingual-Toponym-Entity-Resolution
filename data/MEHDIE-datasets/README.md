# MEHDIE datasets

Cross-lingual (Hebrew ↔ Arabic) historical toponym matching benchmark from:

> Sagi, T. et al. (2025). *Utilizing phonetic similarity for cross-source and cross-language toponym matching: a benchmark and prototype.* Language Resources and Evaluation 59, 2427–2451. https://doi.org/10.1007/s10579-025-09812-9

The files are the paper's electronic supplementary material (`10579_2025_9812_MOESM1_ESM`), unchanged. Only the folder names have been shortened (the `testsetN-` prefix was removed).

## Contents

Five testsets. Each folder holds two source datasets and one ground truth file, `em.tsv`.

| Folder | Original name | Source 1 (rows) | Source 2 (rows) | Ground truth pairs | Pairs with coordinates on both sides |
|---|---|---|---|---|---|
| `YaqutSham_KimaSham/` | testset7 | `YaqutSham.tsv` (687) | `KimaSham.tsv` (1,899) | 33 | 29 |
| `KimaShamThurayyaSham/` | testset8 | `KimaSham.tsv` (1,899) | `ThurayaSham_295.tsv` (291) | 21 | 21 |
| `TudelaThurayya/` | testset9 | `Tudela_257.tsv` (306) | `althurayya_283.tsv` (2,241) | 18 | 11 |
| `YaqutAndalusMagrebKima-KimaMagrebAndalusMapped/` | testset10 | `Yaqut_306.tsv` (484) | `Kima_303.tsv` (559) | 33 | 26 |
| `DamastTudela/` | testset11 | `damast_315.tsv` (447) | `Tudela_257.tsv` (306) | 32 | 21 |
| **Total** | | | | **137** | **108** |

Source 1 is always the dataset referenced by `id_1` in `em.tsv`, source 2 by `id_2`.

All files are tab-separated UTF-8 without BOM. Some use CRLF line endings, others LF. Some text fields contain line breaks, so read them with a proper TSV parser rather than counting lines. In Python:

```python
import csv
csv.field_size_limit(10**9)
rows = list(csv.DictReader(open(path, encoding="utf-8-sig", newline=""), delimiter="\t"))
```

The numbers in the file names (`_257`, `_283`, `_295`, `_303`, `_306`, `_315`) do not match the row counts. Ignore them.

`KimaSham.tsv` has the same content in testsets 7 and 8 (only the line endings differ), and `Tudela_257.tsv` is byte-identical in testsets 9 and 11.

## Ground truth: `em.tsv`

| Column | Content |
|---|---|
| `id_1` | Record ID in source 1 |
| `title_1` | Name in source 1 |
| `id_2` | Record ID in source 2 |
| `title_2` | Name in source 2 |
| `judgement` | Always `true` |

- Only positive pairs are listed. Every other combination of records is an unlabelled non-match. The authors state that some true matches were probably missed, because not all combinations could be reviewed manually.
- The total is 137 pairs, not the 129 reported in Table 2 of the paper. In testsets 7 and 10, several Yāqūt records point to the same Kima record (e.g. two `المرية` records both match Kima `8741`). Unique `id_2` values: 30 in testset 7 and 32 in testset 10.

## Source datasets

### Kima (Hebrew gazetteer): `KimaSham.tsv`, `Kima_303.tsv`

Modern Hebrew-script gazetteer (https://data.geo-kima.org/), regional subsets for al-Sham and Andalus/Maghreb.

| Column | Content |
|---|---|
| `id` | Kima place ID |
| `title` | Hebrew name |
| `title_source` | Always `KimaGazetteer` |
| `start` | Always `2000` (placeholder, not a historical date) |
| `title_uri` | `http://data.geo-kima.org/Place/<id>` |
| `ccodes` | Modern country code (IL, SY, LB, ES, MA, …) |
| `matches` | Wikidata and GeoNames URLs, `;`-separated (89 % al-Sham, 100 % Andalus/Maghreb) |
| `variants` | Name variants in Hebrew and Latin script, `;`-separated |
| `types` | Place type, rarely filled (1–11 %) |
| `aat_types` | Getty AAT code, rarely filled |
| `parent_name` | Modern country or region, in English |
| `lon`, `lat` | Coordinates (89 % al-Sham, 100 % Andalus/Maghreb) |
| `description` | Short description, rarely filled (e.g. "city in Israel") |

### Yāqūt (Arabic, *Muʿjam al-buldān*, 13th c.): `YaqutSham.tsv`, `Yaqut_306.tsv`

Structured extraction of Yāqūt al-Ḥamawī's geographical dictionary, regional subsets for al-Sham and Andalus/Maghreb.

| Column | Content |
|---|---|
| `id` | Entry ID (`dig…`) |
| `title` | Arabic name |
| `title_source` | Always `ياقوت الحموي الرومي` |
| `start`, `end` | Always `632` / `1250` (one span for the whole work) |
| `matches` | Always empty |
| `variants` | Rarely filled (1–4 %) |
| `types` | Place type in Arabic (`مدينة`, `قرية`, `حصن`, `موضع`, …), ≈95 % |
| `parent_name` | Historical region in Arabic (`الشام`, `الأندلس`, `مصر`, …) |
| `lat`, `lon` | Coordinates, only 43–47 % |
| `description` | Full dictionary entry text in Arabic, ≈98 % |
| `varified` (sic) | Value 1–4, ≈50 % filled. Undocumented; tracks the presence of coordinates, so most likely a georeferencing confidence level |

### al-Thurayya (Arabic, Cornu's atlas, 9th–10th c.): `ThurayaSham_295.tsv`, `althurayya_283.tsv`

Gazetteer based on Cornu, G. (1983), *Atlas du monde arabo-islamique à l'époque classique* (https://althurayya.github.io/). The al-Sham file is a subset.

| Column | Content |
|---|---|
| `id` | Transliteration + coordinate code + type letter, e.g. `GHAZZA_344E314N_S` |
| `title` | Arabic name |
| `title_source` | Always Cornu (1983) |
| `title_uri` | World Historical Gazetteer link |
| `variants` | Arabic and transliterated variants, **`:`-separated** |
| `lon`, `lat` | Coordinates (100 %) |
| `start`, `end` | Always `800` / `1000` |
| `type` | English type (town, village, site, region, body of water, …) |
| `aat_types` | Getty AAT code |
| `description` | Cornu category label, e.g. `towns/cite`, `waystations/etape` (not free text) |
| `ccodes` | Modern country code |

### Benjamin of Tudela (Hebrew travelogue, 1170s): `Tudela_257.tsv`

Places from the *Itinerary of Benjamin of Tudela*, from the TraveLab edition.

| Column | Content |
|---|---|
| `id` | Mixed: `K…` (Kima ID), `Q…` (Wikidata), `GN…` (GeoNames), `PL…` (Pleiades), `U…`/`BJ…` (local IDs) |
| `title` | Hebrew name |
| `description` | Hebrew passage from the travelogue where the place is mentioned (≈87 %, median ≈360 characters) |
| `title_source` | Asher or Adler edition |
| `lat`, `lon` | Coordinates, 57 % |
| `start` | Always `1168` |
| `geowkt` | Geometry as WKT `MULTIPOINT`, 38 % |
| `geo_source`, `geo_id` | Always empty |
| `variants` | Hebrew, Latin and sometimes Arabic variants, `;`-separated |
| `matches` | Links to Wikipedia, Wikidata, Kima, VIAF, GeoNames, GND, Pleiades, … (89 %) |

### DAMAST (Arabic, multi-script variants): `damast_315.tsv`

Places from the DAMAST project (Dhimmis & Muslims), around the year 1000.

| Column | Content |
|---|---|
| `id` | Running number 1–447 |
| `title` | Arabic name |
| `title_source` | Always `DAMAST` |
| `lat`, `lon` | Coordinates (96 %) |
| `start` | Always `1000` |
| `types` | Always `settlement` |
| `variants` | Many variants in Arabic, Syriac, Greek and Latin script, `;`-separated |
| `description` | English note, mostly on where the coordinates come from |
| `matches` | Wikidata/GeoNames references, only 11 records |
| `geowkt`, `geo_source`, `geo_id` | Always empty |

## Coverage by data category

| Source | Name | Geography | Time and source | Text context |
|---|---|---|---|---|
| Kima | Name + many variants | Coordinates, country | Placeholder only | Practically none |
| Yāqūt | Name, few variants | Region, type; coordinates ≈45 % | Constant for the work | Full entry text |
| al-Thurayya | Name + transliteration | Coordinates, type, country | Constant for the atlas | None (category label only) |
| Tudela | Name + variants | Coordinates ≈57 % | Edition + constant year | Travelogue passage |
| DAMAST | Name + many variants | Coordinates | Constant | None (coordinate note only) |

## Known issues

- **Time is constant per source.** `start`/`end` carry one value per dataset, so they identify the source rather than the place. Time as a real per-record category requires enrichment from other sources.
- **Identity leakage in Tudela.** The `id` values and the `matches` column contain Kima and Wikidata identifiers. Drop both before any record is shown to a matching method.
- **Incomplete records.** 29 of the 137 ground truth pairs lack coordinates on at least one side. Yāqūt and Tudela are the main gaps.
- **Different separators.** `variants` uses `;` everywhere except al-Thurayya, which uses `:`.
- **Incomplete ground truth.** Only verified positives are listed, so measured precision is a lower bound and measured recall an upper bound.
