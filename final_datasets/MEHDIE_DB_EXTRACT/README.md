# MEHDIE DB extract: Kima, Yaqut, al-Thurayya

Place records exported from the MEHDIE database (World Historical Gazetteer schema) for three gazetteers: **Kima** (historical Hebrew-script place names), **Yaqut** (Yāqūt al-Ḥamawī's *Muʿjam al-Buldān*) and **al-Thurayya** (gazetteer of the early Islamic world). The extract also includes the internal and external links between them. All files are comma-separated, UTF-8, with a header row. JSON-valued columns (`names`, `geoms`, `links`, …) are stored as quoted JSON strings.

## Overview

| File | Rows | Columns | One row per |
|---|---:|---:|---|
| `mehdie_db_kima_extract.csv` | 14,341 | 23 | Kima place record |
| `mehdie_db_yaqut_extract.csv` | 15,904 | 23 | Yaqut place record |
| `mehdie_db_thurayya_extract.csv` | 4,482 | 23 | al-Thurayya place record |
| `internal_links_kima_yaqut_thurayya.csv` | 920 | 5 | Link between two MEHDIE places |
| `external_links_kima_yaqut_thurayya.csv` | 5,251 | 4 | Link from a MEHDIE place to Wikidata/GeoNames/etc. |

**How coverage is counted:** a cell counts as empty if it is blank or an empty container (`{}`, `[]`, `[[]]`, `""`).

**Columns that are empty in all three place files:** `review_wd`, `review_tgn`, `review_whg`, `review_md`, `name_parts`, `whens`, `depictions`. **Constant columns:** `indexed` and `flag` are always `false`, and `minmax`/`timespans` hold one fixed period per source (Kima: 2000 or 1800; Yaqut: 632–1250; al-Thurayya: 800–1000).

**Answer leakage:** the `links` column of the place files holds `same_as`, `different` and `closeMatch` (Wikidata/GeoNames) links, the same kind of information as the two link files. Drop it before using the records as matcher input.

---

## Place file columns

The three place files share the same 23 columns, which come from the World Historical Gazetteer schema. Coverage per source is in the tables further down.

| Column | Description |
|---|---|
| `id` | MEHDIE database ID of the record (primary key); this is the ID used in `source_place_id` / `target_place_id` of the link files |
| `title` | Preferred name of the place. Kima: Hebrew; Yaqut: Arabic; al-Thurayya: transliteration or Arabic |
| `src_id` | ID of the place in its original source. Kima: numeric Kima ID; Yaqut: entry ID like `dig00001`; al-Thurayya: key like `ABADHA_526E311N_S` (name + coordinates) |
| `ccodes` | ISO 3166-1 alpha-2 country code(s) as a Postgres array, e.g. `{IL}` |
| `minmax` | Year range `{start,end}` of the record. This is a dataset-wide default, not place-specific |
| `timespans` | Same range as `minmax`, as a list of `[start, end]` spans |
| `fclasses` | GeoNames feature class(es): `A` administrative, `P` populated place, `L` area, `S` spot/building |
| `indexed` | Whether the record is indexed in WHG search (always `false`) |
| `flag` | Review flag (always `false`) |
| `review_wd` | Reconciliation review status against Wikidata (empty) |
| `review_tgn` | Reconciliation review status against Getty TGN (empty) |
| `review_whg` | Reconciliation review status against the WHG index (empty) |
| `dataset` | Name of the MEHDIE sub-dataset the record was uploaded in, e.g. `KIMA-IL`, `YaqutFull` |
| `review_md` | Manual review status (empty) |
| `name_parts` | Name components (empty) |
| `links` | JSON list of links: `type` (`closeMatch`, `same_as`, `different`, `located_in`, …) and `identifier` (`wd:Q…`, `gn:…`, a URL, or another MEHDIE `id`) |
| `descriptions` | JSON list of description texts. Kima: short Hebrew/English notes; Yaqut: the Arabic dictionary entry text; al-Thurayya: settlement category such as `towns/cite` |
| `names` | JSON list of name variants (`toponym`) with source citations. Al-Thurayya packs several variants into one `toponym`, separated by `:` |
| `geoms` | JSON list of geometries (all `Point`), with WKT `geowkt` and `coordinates` as `[lon, lat]` |
| `related` | JSON list of parent places (`relationType` `gvp:broaderPartitive`, `label` = parent name, e.g. a country or region) |
| `types` | JSON list of place types (`label` / `sourceLabel`), e.g. Kima `province`, Yaqut `قرية` (village), `موضع` (site), `جبل` (mountain) |
| `whens` | Temporal attestations per record (empty) |
| `depictions` | Images of the place (empty) |

---

## `mehdie_db_kima_extract.csv`

14,341 records from 21 Kima sub-datasets, with **6,211** distinct `src_id`s. The same Kima place can appear in several sub-datasets.

| Column | Non-empty | Coverage | Distinct values |
|---|---:|---:|---:|
| `id` | 14,341 | 100.0% | 14,341 |
| `title` | 14,341 | 100.0% | 9,344 |
| `src_id` | 14,341 | 100.0% | 6,211 |
| `ccodes` | 13,834 | 96.5% | 32 |
| `minmax` | 14,341 | 100.0% | 2 |
| `timespans` | 14,341 | 100.0% | 2 |
| `fclasses` | 282 | 2.0% | 4 |
| `indexed` | 14,341 | 100.0% | 1 |
| `flag` | 14,341 | 100.0% | 1 |
| `review_wd` | 0 | 0.0% | 0 |
| `review_tgn` | 0 | 0.0% | 0 |
| `review_whg` | 0 | 0.0% | 0 |
| `dataset` | 14,341 | 100.0% | 21 |
| `review_md` | 0 | 0.0% | 0 |
| `name_parts` | 0 | 0.0% | 0 |
| `links` | 8,707 | 60.7% | 8,707 |
| `descriptions` | 1,724 | 12.0% | 1,724 |
| `names` | 14,341 | 100.0% | 14,341 |
| `geoms` | 8,648 | 60.3% | 8,648 |
| `related` | 13,925 | 97.1% | 13,925 |
| `types` | 13,939 | 97.2% | 13,939 |
| `whens` | 0 | 0.0% | 0 |
| `depictions` | 0 | 0.0% | 0 |

Notes:
- `types` is non-empty for 97.2% of rows, but almost all entries have an empty label. Only 527 entries carry an actual type (province 177, extinct city 113, district 88, …).
- `dataset`: Kima-IL-PS 2,588 · KIMA-IL 2,497 · KimaShamPlusMapped 1,899 · KimaShamPlusUnmapped 1,567 · KimaShamMapped_ILonl 1,314 · KimaFarsPlusMapped 650 · KimaMagrebAndalusMap 559 · kimaShamNoILmapped 389 · Turkima 327 · KimaArabiaIRAQ 321 · KimaFarsPlusUnmapped 320 · Kima2024-1toMatchMag 315 · Kima-EG 247 · AustriaKimaDE 224 · AustriaKimaHE 223 · KimaMisrPlusMatched 182 · KimaMisrUnmatched 179 · KIMALESSHLOC 178 · Kima-IRAN 155 · KIMA-SY 116 · KimaPalest 91.
- `ccodes` top values: IL 8,806 · TR 997 · EG 648 · ES 560 · IN 466 · PS 331 · IR 309.
- `fclasses` (when present): A 273 · L 6 · S 2 · P 1.

---

## `mehdie_db_yaqut_extract.csv`

15,904 records, all from the `YaqutFull` dataset. Each `src_id` is unique.

| Column | Non-empty | Coverage | Distinct values |
|---|---:|---:|---:|
| `id` | 15,904 | 100.0% | 15,904 |
| `title` | 15,904 | 100.0% | 14,494 |
| `src_id` | 15,904 | 100.0% | 15,904 |
| `ccodes` | 0 | 0.0% | 0 |
| `minmax` | 15,904 | 100.0% | 1 |
| `timespans` | 15,904 | 100.0% | 1 |
| `fclasses` | 0 | 0.0% | 0 |
| `indexed` | 15,904 | 100.0% | 1 |
| `flag` | 15,904 | 100.0% | 1 |
| `review_wd` | 0 | 0.0% | 0 |
| `review_tgn` | 0 | 0.0% | 0 |
| `review_whg` | 0 | 0.0% | 0 |
| `dataset` | 15,904 | 100.0% | 1 |
| `review_md` | 0 | 0.0% | 0 |
| `name_parts` | 0 | 0.0% | 0 |
| `links` | 56 | 0.4% | 56 |
| `descriptions` | 2,661 | 16.7% | 2,661 |
| `names` | 15,904 | 100.0% | 15,904 |
| `geoms` | 2,675 | 16.8% | 2,675 |
| `related` | 4,475 | 28.1% | 4,475 |
| `types` | 15,904 | 100.0% | 15,904 |
| `whens` | 0 | 0.0% | 0 |
| `depictions` | 0 | 0.0% | 0 |

Notes:
- Yaqut has no country codes and coordinates for only 16.8% of records.
- `types` mostly carries a real Arabic type label: قرية (village) 2,577 · موضع (site) 2,525 · جبل (mountain) 1,058 · مدينة (city) 865 · ماء (water source) 614.

---

## `mehdie_db_thurayya_extract.csv`

4,482 records. These are **2,241 places, each appearing twice**, once in the `AlThurayyaTry` dataset and once in `Al-Thurayya` (2,241 rows each, 2,241 distinct `src_id`s). Deduplicate on `src_id` if you need one row per place.

| Column | Non-empty | Coverage | Distinct values |
|---|---:|---:|---:|
| `id` | 4,482 | 100.0% | 4,482 |
| `title` | 4,482 | 100.0% | 4,281 |
| `src_id` | 4,482 | 100.0% | 2,241 |
| `ccodes` | 4,468 | 99.7% | 39 |
| `minmax` | 4,482 | 100.0% | 1 |
| `timespans` | 4,482 | 100.0% | 1 |
| `fclasses` | 0 | 0.0% | 0 |
| `indexed` | 4,482 | 100.0% | 1 |
| `flag` | 4,482 | 100.0% | 1 |
| `review_wd` | 0 | 0.0% | 0 |
| `review_tgn` | 0 | 0.0% | 0 |
| `review_whg` | 0 | 0.0% | 0 |
| `dataset` | 4,482 | 100.0% | 2 |
| `review_md` | 0 | 0.0% | 0 |
| `name_parts` | 0 | 0.0% | 0 |
| `links` | 17 | 0.4% | 17 |
| `descriptions` | 4,482 | 100.0% | 4,482 |
| `names` | 4,482 | 100.0% | 4,482 |
| `geoms` | 4,482 | 100.0% | 4,482 |
| `related` | 0 | 0.0% | 0 |
| `types` | 0 | 0.0% | 0 |
| `whens` | 0 | 0.0% | 0 |
| `depictions` | 0 | 0.0% | 0 |

Notes:
- `ccodes` top values are IR 1,082 · EG 388 · SA 370 · IQ 296 · UZ 254 · SY 244 · AF 234 · YE 206.
- Al-Thurayya has no `types`; its settlement category is stored in `descriptions` instead (e.g. `towns/cite`, `waystations/etape`).

---

## `internal_links_kima_yaqut_thurayya.csv`

Links between places in different MEHDIE datasets. Every ID resolves to a record in one of the three place files.

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `link_type` | Relation from source to target: `same_as` (same place), `different` (confirmed not the same place), `located_in` / `reverse_located_in`, `reverse_part_of` | 920 | 100.0% | 5 |
| `source_place_id` | MEHDIE `id` of the source place | 920 | 100.0% | 789 |
| `source_dataset` | Sub-dataset of the source place | 920 | 100.0% | 8 |
| `target_place_id` | MEHDIE `id` of the target place | 920 | 100.0% | 732 |
| `target_dataset` | Sub-dataset of the target place | 920 | 100.0% | 9 |

| `link_type` | Rows | Share |
|---|---:|---:|
| different | 789 | 85.8% |
| same_as | 116 | 12.6% |
| reverse_located_in | 11 | 1.2% |
| reverse_part_of | 3 | 0.3% |
| located_in | 1 | 0.1% |

Notes:
- Most links are **negative** (`different`). Only 116 are positive `same_as` matches.
- Source places by gazetteer: Yaqut 473 · Kima 430 · al-Thurayya 17. Target places: Kima 473 · al-Thurayya 258 · Yaqut 189.
- `source_dataset`: YaqutFull 473 · Kima-IL-PS 264 · KimaShamMapped_ILonl 147 · AlThurayyaTry 17 · KimaMisrPlusMatched 8 · KIMA-SY 7 · KimaPalest 3 · KimaMagrebAndalusMap 1.
- `target_dataset`: Al-Thurayya 255 · KimaShamPlusMapped 196 · YaqutFull 189 · Kima-IL-PS 104 · KimaMagrebAndalusMap 89 · KimaShamPlusUnmapped 53 · KimaMisrPlusMatched 23 · Kima-EG 8 · AlThurayyaTry 3.

---

## `external_links_kima_yaqut_thurayya.csv`

`closeMatch` links from MEHDIE places to external authorities. All sources are Kima sub-datasets: Yaqut and al-Thurayya have no rows here.

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `link_type` | Link relation; always `closeMatch` | 5,251 | 100.0% | 1 |
| `source_place_id` | MEHDIE `id` of the Kima place | 5,251 | 100.0% | 3,424 |
| `source_dataset` | Kima sub-dataset of the place | 5,251 | 100.0% | 14 |
| `external_id` | External identifier, prefixed by authority: `wd:Q…` Wikidata, `gn:…` GeoNames, a full URL, or `zadikim:…` | 5,251 | 100.0% | 5,173 |

| External authority (`external_id` prefix) | Rows | Share |
|---|---:|---:|
| `wd:` Wikidata | 2,934 | 55.9% |
| `gn:` GeoNames | 2,149 | 40.9% |
| `https:` URL | 124 | 2.4% |
| `zadikim:` | 44 | 0.8% |

`source_dataset`: KIMA-IL 2,201 · KimaMagrebAndalusMap 807 · KimaFarsPlusMapped 577 · Turkima 273 · KimaArabiaIRAQ 260 · AustriaKimaHE 249 · KIMALESSHLOC 210 · Kima-EG 185 · KimaShamPlusMapped 127 · Kima-IRAN 123 · KimaPalest 102 · KimaMisrPlusMatched 65 · KIMA-SY 58 · kimaShamNoILmapped 14.
