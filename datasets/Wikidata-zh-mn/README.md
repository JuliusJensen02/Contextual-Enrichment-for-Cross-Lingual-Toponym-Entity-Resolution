# Wikidata Chinese–Mongolian–Russian toponyms

Historical Chinese, Mongolian and Russian place names from Wikidata for China, Mongolia and the surrounding region, plus gold sets of matches. The Chinese records are enriched with TGaz/CHGIS through the Wikidata property P4711 (CHGIS ID).

- Source: Wikidata via the QLever endpoint (https://qlever.dev/wikidata), queried 5 November 2026. Wikidata changes daily, so a rerun gives slightly different numbers.
- Licence: CC0 (Wikidata). TGaz columns follow the TGaz licence.
- Rebuild: `python scripts/build_wikidata_zh_mn.py` (about 50 minutes on a busy endpoint). It reads `datasets/tgaz_csv`, which is no longer in the working tree, so restore that folder or change `TGAZ` in the script first.

## Files

| File | Rows | Columns | Content |
|---|---|---|---|
| `wikidata_zh.tsv` | 14,562 | 36 | Chinese pool |
| `wikidata_mn.tsv` | 3,122 | 26 | Mongolian pool |
| `wikidata_ru.tsv` | 6,425 | 26 | Russian pool |
| `em.tsv` | 2,860 | 2 | Matches: `id_1` (Chinese), `id_2` (Mongolian) |
| `em_zh_ru.tsv` | 3,263 | 2 | Matches: `id_1` (Chinese), `id_2` (Russian) |
| `em_mn_ru.tsv` | 1,683 | 2 | Matches: `id_1` (Mongolian), `id_2` (Russian) |
| `wikidata_zh.rq`, `wikidata_mn.rq`, `wikidata_ru.rq` | | | The queries that select each pool |

All matches are direct: both records of a pair belong to the same Wikidata item. 1,514 items are in all three pools.

The pools are not one-to-one, unlike `Wikidata-he-ar`. Many records have no match in another pool, as in the MEHDIE testsets: for `em.tsv`, 11,702 Chinese and 262 Mongolian records. Wikidata has only about 8,700 items worldwide with coordinates and a Mongolian label, so **the Mongolian side limits the size of `em.tsv`**.

## Selection

**Region.** Latitude 13–59, longitude 68–140: the extent of China and Mongolia plus 5 degrees. It also covers Korea, most of Japan, Central Asia, southern Siberia, northern India and mainland Southeast Asia. Narrow it with `country`.

**Location.** Many historical items have no coordinates of their own, so `coord_source` records where the location comes from, in this order:

| `coord_source` | Meaning | zh | mn | ru |
|---|---|---|---|---|
| `own` | The item's P625 | 6,503 | 2,980 | 3,691 |
| `tgaz` | TGaz coordinates of the linked CHGIS record | 3,977 | 23 | 180 |
| `capital` | Coordinates of its capital (P36) | 512 | 76 | 570 |
| `parent` | Coordinates of its P131 or P17 | 2,433 | 17 | 1,961 |
| `parent_capital` | Coordinates of the capital of that parent | 143 | 1 | 7 |
| `none` | No location; `lat`, `lon` empty. Kept because the type places it in China (`fu`, `zhou`, Yuan circuit, Chinese state) | 994 | 25 | 16 |

Derived coordinates are approximate. A dynasty's location is its capital, and a `parent` location can be far from the place itself.

**Historical.** `historical_basis` says why a record counts as historical. Empty means a modern place.

| `historical_basis` | Rule | zh | mn | ru | em | em_zh_ru | em_mn_ru |
|---|---|---|---|---|---|---|---|
| `historical_country` | Instance of historical country (Q3024240) or a subclass | 670 | 128 | 468 | 128 | 396 | 123 |
| `ancient_city` | Ancient city (Q15661340) | 61 | 6 | 36 | 6 | 26 | 6 |
| `archaeological_site` | Archaeological site (Q839954) | 1,211 | 15 | 484 | 11 | 190 | 10 |
| `former_admin_unit` | Former administrative territorial entity (Q19953632) | 8,851 | 57 | 2,875 | 57 | 955 | 17 |
| `historical_region` | Historical region (Q1620908) | 103 | 11 | 53 | 11 | 35 | 9 |
| `living_former_capital` | A former-entity class, but still a settlement, e.g. Beijing, Kyoto | 433 | 11 | 66 | 11 | 39 | 11 |
| `dissolved` | A place with a dissolved date (P576) | 134 | 4 | 66 | 4 | 55 | 4 |
| `chgis_linked` | Has a TGaz record, no other signal | 162 | 0 | 7 | 0 | 7 | 0 |
| `old_settlement` | Settlement with P571 or P1249 before 1800 | 380 | 77 | 944 | 75 | 300 | 77 |
| empty | Modern place | 2,557 | 2,813 | 1,426 | 2,557 | 1,260 | 1,426 |

Anything that ended after 1949 is treated as modern. This also removes the Mongolian People's Republic (1992) and Vietnamese provinces merged in 2025.

**Who is in which pool.** The Chinese pool holds historical places with a Chinese name, plus modern places that have a Mongolian partner. The Mongolian pool holds every toponym in the region with a Mongolian name, historical or not. The Russian pool holds items with a Russian label that are historical or are in one of the other two pools. **For a strictly historical test, keep the pairs with a `historical_basis`: 303 in `em.tsv`, 2,003 in `em_zh_ru.tsv` and 257 in `em_mn_ru.tsv`.** `historical_basis` is identical on both sides of a pair. Most of the other pairs are modern places, such as Chinese townships and Mongolian districts.

Toponyms are defined as in `Wikidata-he-ar`: the six place classes, geographic region types, or any historical basis.

## Columns

**Both sets**

| Column | Content | zh | mn | ru |
|---|---|---|---|---|
| `id` | Opaque hash of the item with a set prefix. Stays the same across rebuilds and does not reveal the match; rows are sorted by `id` | 100 % | 100 % | 100 % |
| `title` | Name without disambiguators such as `(936-947)` | 100 % | 100 % | 100 % |
| `variants` | Other names, `;`-separated: labels in other Chinese variants, aliases, P1705, P1448 | 42 % | 20 % | 17 % |
| `description` | Wikidata description in the set's language | 40 % | 2 % | 49 % |
| `wiki_title` | Wikipedia article title in the set's language | 64 % | 55 % | 70 % |
| `lat`, `lon`, `coord_source` | See above | 93 % | 99 % | 100 % |
| `historical_basis` | See above | 82 % | 10 % | 78 % |
| `instance_of_label` | English type names (P31) | 100 % | 100 % | 100 % |
| `inception` | Earliest year from P571 or P1249; negative is BCE | 25 % | 19 % | 45 % |
| `dissolved` | Earliest year from P576 | 19 % | 6 % | 20 % |
| `country` | P17; can be a historical state | 91 % | 96 % | 95 % |
| `admin_unit` | P131 | 72 % | 89 % | 75 % |
| `part_of` | P361 | 5 % | 8 % | 7 % |
| `capital` | P36 | 8 % | 15 % | 19 % |
| `replaces`, `replaced_by` | P1365, P1366 | 7 %, 16 % | 9 %, 4 % | 11 %, 12 % |
| `neighbours` | P47 | 4 % | 12 % | 8 % |
| `on_water`, `on_feature` | P206, P706 | 2 %, 1 % | 4 %, 3 % | 3 %, 2 % |
| `named_after` | P138 | 2 % | 4 % | 3 % |
| `time_period` | P2348 | 1 % | 1 % | 1 % |
| `described_by` | Encyclopedias and sources (P1343) | 7 % | 16 % | 21 % |
| `population`, `elevation_m` | Largest P1082, first P2044 | 10 %, 8 % | 35 %, 25 % | 34 %, 17 % |

Linked attributes are English labels, `|`-separated.

**Only in `wikidata_zh.tsv`** (28 % filled): `tgaz_name`, `tgaz_pinyin`, `tgaz_beg_yr`, `tgaz_end_yr`, `tgaz_type`, `tgaz_type_py`, `tgaz_parent`, `tgaz_parent_py`, `tgaz_instances`, `tgaz_present_loc`. One Wikidata item can stand for several time-sliced TGaz records. `tgaz_instances` is their number, `tgaz_beg_yr` the earliest year and `tgaz_end_yr` the latest, and text columns are `|`-separated. 5,668 of the 5,672 CHGIS IDs in Wikidata resolve to a TGaz `sys_id` as `hvd_<id>`.

Only 1 % of the matched Chinese records have TGaz data, so TGaz adds little to the matched records so far.

## Avoiding leakage

Both records of a pair come from one Wikidata item, so **every shared column is identical on both sides**, in all three match files. To test matching, use only `title`, `variants`, `description`, `wiki_title` and the `tgaz_*` columns, or give the shared columns to the candidate side only. Wikidata QIDs, English labels and external identifiers are left out of all files for this reason.

## Known issues

- **Modern noise in `former_admin_unit`.** Mainly `dissolved municipality of Japan` (636, Meiji-era onwards) and `former township in PRC` (321). Filter on `instance_of_label` if needed.
- **Chinese pool spreads beyond China.** 2,575 records have Japan in `country`. In the Russian pool, 732 do.
- **Same name, different item.** 58 Chinese titles occur more than once among the matched records, such as `城关镇` and `突厥汗国`. They are distinct items, so ground truth is correct, but a matcher cannot separate them by name alone.
- **Lost items.** 2,872 items had no location and no China-specific type, so they are excluded. These include real places such as the Keraites and Khamag Mongol.
- **Wikidata errors remain.** Some labels are wrong, for example `毗湿奴` (Vishnu) typed as an ancient city.
- **Ships as archaeological sites.** Wrecks are typed as archaeological sites, so about 30 Chinese and 14 Russian records are ships, such as `Ямато`. Filter on `instance_of_label`.
- **Russian names are mostly modern.** They are Wikidata labels, not period attestations. The 1870s Russian names in `chgis_ras` are not included, because linking them would need fuzzy matching.
- **Mostly modern Mongolian spellings.** Mongolian names are Cyrillic transcriptions, not period attestations. Traditional-script names occur only in `variants` and rarely.

## Overlap with `final_datasets`

No records are shared, but some of the same places occur in both, mainly at the western and southern edge of the region (Afghanistan, Central Asia, India). Counts are of items and of pairs, with historical pairs in brackets.

| Link | Items | `em.tsv` | `em_zh_ru.tsv` | `em_mn_ru.tsv` |
|---|---:|---:|---:|---:|
| Shared ID: Pleiades, Trismegistos, MEHDIE Wikidata or GeoNames links | 120 | 66 (22) | 107 (63) | 66 (22) |
| Shared ID, or within 3 km | 278 | 87 (29) | 211 (153) | 87 (29) |

The ID row is firm. The 3 km row is an upper limit, because it also catches nearby but different places. It uses `own` and `tgaz` coordinates only. These places are **not** removed from the files.
