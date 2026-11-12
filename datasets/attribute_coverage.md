# Dataset Attribute Coverage

This report maps the requested attributes to the available dataset columns and
reports non-empty values.

## Datasets

| Dataset | File | Rows |
|---|---|---:|
| Pleiades | `datasets/Pleades_Trismegistos/pleiades.tsv` | 42,417 |
| Trismegistos | `datasets/Pleades_Trismegistos/trismegistos.tsv` | 64,507 |
| Yaqut | `datasets/MEHDIE/flattened/mehdie_db_yaqut_flat.tsv` | 15,904 |
| al-Thurayya | `datasets/MEHDIE/flattened/mehdie_db_thurayya_flat.tsv` | 4,482 |
| Wikidata RU | `datasets/Wikidata-zh-ru/wikidata_ru.tsv` | 6,425 |
| Wikidata ZH | `datasets/Wikidata-zh-ru/wikidata_zh.tsv` | 14,562 |

Counts are non-empty records; percentages use the total number of rows in each
dataset. `—` means that no usable matching attribute was found.

Abbreviations: **P** = Pleiades, **T** = Trismegistos, **Y** = Yaqut,
**Th** = al-Thurayya, **RU** = Wikidata Russian, **ZH** = Wikidata Chinese.

## Names

| Field | P | T | Y | Th | RU | ZH |
|---|---:|---:|---:|---:|---:|---:|
| Name/title | `title`: 42,417 (100%) | `name_standard`: 64,507 (100%) | `title`: 15,904 (100%) | `title`: 4,482 (100%) | `title`: 6,425 (100%) | `title`: 14,562 (100%) |
| Name variants | `names_by_language`: 12,667 (29.9%) | — | `name_variants`: 15,904 (100%) | `name_variants`: 4,482 (100%) | `variants`: 1,093 (17.0%) | `variants`: 6,062 (41.6%) |
| Romanized names | `names_romanized`: 27,355 (64.5%) | — | — | — | — | — |
| Greek names | `names_greek`: 2,909 (6.9%) | `names_greek`: 14,721 (22.8%) | — | — | — | — |
| Latin names | `names_latin`: 3,915 (9.2%) | `names_latin`: 13,509 (20.9%) | — | — | — | — |
| Egyptian names | — | `names_egyptian`: 1,969 (3.1%) | — | — | — | — |
| Coptic names | — | `names_coptic`: 659 (1.0%) | — | — | — | — |
| Wikipedia title | — | — | — | — | `wiki_title`: 4,513 (70.2%) | `wiki_title`: 9,294 (63.8%) |
| Number of names | `n_names > 0`: 27,355 (64.5%) | — | — | — | — | — |
| TGaz name | — | — | — | — | — | `tgaz_name`: 4,150 (28.5%) |
| TGaz pinyin | — | — | — | — | — | `tgaz_pinyin`: 4,150 (28.5%) |
| Modern name | — | `modern_name`: 7,176 (11.1%) | — | — | — | — |
| Named after | — | — | — | — | `named_after`: 195 (3.0%) | `named_after`: 255 (1.8%) |
| Replaces | — | — | — | — | `replaces`: 708 (11.0%) | `replaces`: 1,043 (7.2%) |
| Replaced by | — | — | — | — | `replaced_by`: 758 (11.8%) | `replaced_by`: 2,290 (15.7%) |

## Absolute and relational geography

| Field | P | T | Y | Th | RU | ZH |
|---|---:|---:|---:|---:|---:|---:|
| Latitude | `lat`: 34,840 (82.1%) | `lat`: 24,617 (38.2%) | `lat`: 2,675 (16.8%) | `lat`: 4,482 (100%) | `lat`: 6,409 (99.8%) | `lat`: 13,568 (93.2%) |
| Longitude | `lon`: 34,840 (82.1%) | `lon`: 24,617 (38.2%) | `lon`: 2,675 (16.8%) | `lon`: 4,482 (100%) | `lon`: 6,409 (99.8%) | `lon`: 13,568 (93.2%) |
| Elevation | — | — | — | — | `elevation_m`: 1,120 (17.4%) | `elevation_m`: 1,204 (8.3%) |
| Country codes | — | — | `ccodes`: 0 (0%) | `ccodes`: 4,468 (99.7%) | — | — |
| Country | — | `country`: 64,507 (100%) | — | — | `country`: 6,125 (95.3%) | `country`: 13,216 (90.8%) |
| Region | — | `region`: 64,507 (100%) | — | — | — | — |
| TGaz parent | — | — | — | — | — | `tgaz_parent`: 3,497 (24.0%) |
| TGaz parent pinyin | — | — | — | — | — | `tgaz_parent_py`: 3,497 (24.0%) |
| Parent name | — | — | `relation`: 4,475 (28.1%) | `relation`: 0 (0%) | — | `tgaz_parent`: 3,497 (24.0%) |
| Nomos code | — | `nomos_code`: 62,326 (96.6%) | — | — | — | — |
| Provincia | — | `provincia`: 64,506 (100%) | — | — | — | — |
| Part of | — | — | — | — | `part_of`: 441 (6.9%) | `part_of`: 674 (4.6%) |
| Capital | — | — | — | — | `capital`: 1,222 (19.0%) | `capital`: 1,144 (7.9%) |
| Neighbours | — | — | — | — | `neighbours`: 513 (8.0%) | `neighbours`: 579 (4.0%) |
| Population | — | — | — | — | `population`: 2,175 (33.9%) | `population`: 1,509 (10.4%) |
| Location description | — | `location`: 34,759 (53.9%) | — | — | — | `tgaz_present_loc`: 4,027 (27.7%) |

## Temporal attributes

| Field | P | T | Y | Th | RU | ZH |
|---|---:|---:|---:|---:|---:|---:|
| Inception | — | — | — | — | `inception`: 2,922 (45.5%) | `inception`: 3,598 (24.7%) |
| Dissolved | — | — | — | — | `dissolved`: 1,269 (19.8%) | `dissolved`: 2,776 (19.1%) |
| Begin date | — | `begin_date`: 26,520 (41.1%) | `begin_date`: 15,904 (100%) | `begin_date`: 4,482 (100%) | — | — |
| End date | — | `end_date`: 26,520 (41.1%) | `end_date`: 15,904 (100%) | `end_date`: 4,482 (100%) | — | — |
| Year from | `year_from`: 39,508 (93.1%) | — | — | — | — | — |
| Year to | `year_to`: 39,508 (93.1%) | — | — | — | — | — |
| Time period(s) | `time_periods`: 39,508 (93.1%) | — | — | — | `time_period`: 70 (1.1%) | `time_period`: 111 (0.8%) |
| TGaz begin year | — | — | — | — | — | `tgaz_beg_yr`: 4,150 (28.5%) |
| TGaz end year | — | — | — | — | — | `tgaz_end_yr`: 4,150 (28.5%) |

> **Caveat:** Yaqut and al-Thurayya `begin_date` and `end_date` values are
> dataset-wide defaults rather than genuinely place-specific dates.

## Classification

| Field | P | T | Y | Th | RU | ZH |
|---|---:|---:|---:|---:|---:|---:|
| Instance-of label | — | — | — | — | `instance_of_label`: 6,425 (100%) | `instance_of_label`: 14,562 (100%) |
| Place types | `place_types`: 42,416 (100%) | — | — | — | — | — |
| Types | — | — | `types`: 14,393 (90.5%) | `types`: 0 (0%) | — | — |
| Status | — | `status`: 25,476 (39.5%) | — | — | — | — |
| TGaz type | — | — | — | — | — | `tgaz_type`: 4,150 (28.5%) |
| TGaz type pinyin | — | — | — | — | — | `tgaz_type_py`: 4,150 (28.5%) |
| Ethnicon | — | `ethnicon`: 5,006 (7.8%) | — | — | — | — |

## Descriptions and sources

| Field | P | T | Y | Th | RU | ZH |
|---|---:|---:|---:|---:|---:|---:|
| Details | `details`: 32,413 (76.4%) | — | — | — | — | — |
| Described by | — | — | — | — | `described_by`: 1,331 (20.7%) | `described_by`: 1,022 (7.0%) |
| Ancient sources | `ancient_sources`: 4,864 (11.5%) | — | — | — | — | — |
| Keywords | — | — | — | — | — | — |
| Snippets | — | `text_snippets`: 374 (0.6%) | — | — | — | — |
| Edition text | — | — | — | — | — | — |
| Description | `description`: 42,402 (100%) | — | `description`: 2,661 (16.7%) | `description`: 4,482 (100%) | `description`: 3,146 (49.0%) | `description`: 5,822 (40.0%) |

## Summary

The strongest broadly available attributes are:

- names/titles in all datasets;
- coordinates in al-Thurayya and Wikidata, and for most Pleiades records;
- Pleiades temporal coverage;
- Trismegistos country, region, nomos, and provincia metadata;
- Wikidata classification through `instance_of_label`;
- descriptions in Pleiades and al-Thurayya.

