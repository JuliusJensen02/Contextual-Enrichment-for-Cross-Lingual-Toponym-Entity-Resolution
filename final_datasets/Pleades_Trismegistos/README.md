# Pleiades–Trismegistos

Gazetteer data for ancient places from [Pleiades](https://pleiades.stoa.org/) and [Trismegistos Places](https://www.trismegistos.org/geo/), plus a gold set of entity matches (`em.tsv`) linking the two. All files are tab-separated, UTF-8, with a header row. A few fields contain tab characters and are wrapped in double quotes, so read them with a CSV parser that handles quoting (e.g. `pandas.read_csv(path, sep="\t")`, not a plain `split("\t")`).

Built by `scripts/build_pleiades_trismegistos.py`, `scripts/build_trismegistos.py`, `scripts/build_pleiades_connections.py` and `scripts/build_pleiades_references.py`.

## Overview

| File | Rows | Columns | One row per |
|---|---:|---:|---|
| `pleiades.tsv` | 42,417 | 18 | Pleiades place |
| `trismegistos.tsv` | 64,507 | 21 | Trismegistos place |
| `trismegistos_texts.tsv` | 58,595 | 13 | (Trismegistos place, text) pair |
| `em.tsv` | 13,890 | 6 | Matched (Pleiades place, Trismegistos place) pair |

**How coverage is counted:** a cell counts as non-empty if it is not blank after stripping whitespace. Numeric count columns such as `n_names` or `n_texts` are always filled, even when the value is `0`; see the notes under each table.

**Multi-valued fields** use ` | ` (space, pipe, space) as separator. **Years** are integers, with negative numbers for BCE (e.g. `-30` = 30 BCE).

**No cross-references:** `pleiades.tsv` and `trismegistos.tsv` contain matching features only. IDs pointing to the other database (and to Wikidata, GeoNames, etc.) were removed so they don't leak the answer. The links live only in `em.tsv`.

---

## `em.tsv`: entity matches

Gold alignment between Pleiades and Trismegistos places. Each (`pleiades_id`, `trismegistos_id`) pair appears once (13,890 distinct pairs).

- Covers **13,666** distinct Pleiades places (32.2% of `pleiades.tsv`) and **13,396** distinct Trismegistos places (20.8% of `trismegistos.tsv`).
- Some places are matched to more than one place in the other gazetteer, so the mapping is not strictly 1:1.

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `pleiades_id` | Pleiades place ID; joins to `pleiades.tsv` | 13,890 | 100.0% | 13,666 |
| `trismegistos_id` | Trismegistos Geo ID; joins to `trismegistos.tsv` | 13,890 | 100.0% | 13,396 |
| `pleiades_title` | Pleiades title of the place, for readability | 13,890 | 100.0% | 13,146 |
| `trismegistos_name` | Trismegistos standard name of the place, for readability | 13,890 | 100.0% | 12,264 |
| `sources` | Which resources assert the link: `pleiades` (a Pleiades reference points to the TM place), `trismegistos` (TM's own Pleiades link), `paths` (PAThs `skos:exactMatch` to both) | 13,890 | 100.0% | 7 |
| `n_sources` | Number of resources in `sources` (1–3); a rough confidence signal | 13,890 | 100.0% | 3 |

**Match provenance (`sources`).** Which resource(s) asserted the link:

| `sources` | Rows | Share |
|---|---:|---:|
| trismegistos | 7,944 | 57.2% |
| pleiades \| trismegistos | 5,303 | 38.2% |
| pleiades | 446 | 3.2% |
| pleiades \| trismegistos \| paths | 124 | 0.9% |
| trismegistos \| paths | 38 | 0.3% |
| paths | 33 | 0.2% |
| pleiades \| paths | 2 | <0.1% |

| `n_sources` | Rows | Share |
|---:|---:|---:|
| 1 | 8,423 | 60.6% |
| 2 | 5,343 | 38.5% |
| 3 | 124 | 0.9% |

---

## `pleiades.tsv`: Pleiades places

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `pleiades_id` | Pleiades place ID (primary key) | 42,417 | 100.0% | 42,417 |
| `title` | Display title, often with a qualifier in parentheses, e.g. `Aegyptus (Roman imperial province)` | 42,417 | 100.0% | 36,501 |
| `description` | One-sentence English summary of the place | 42,402 | 99.96% | 38,369 |
| `details` | Longer free-text notes, often from the Barrington Atlas Directory (modern location, identification); URLs removed | 32,413 | 76.4% | 27,390 |
| `place_types` | Pleiades place-type vocabulary terms, e.g. `settlement`, `river`, `province-2` | 42,416 | 99.99% | 1,658 |
| `names_romanized` | All romanized (Latin-script) forms of the place's attested names | 27,355 | 64.5% | 25,933 |
| `names_greek` | Attested names in Ancient Greek script | 2,909 | 6.9% | 2,822 |
| `names_latin` | Attested names in Latin | 3,915 | 9.2% | 3,838 |
| `names_by_language` | Every name that has a language tag, as `name@lang` (e.g. `Ὀάρακτα@grc`, `Palk Bay@en`) | 12,667 | 29.9% | 12,539 |
| `n_names` | Number of name records Pleiades holds for the place | 42,417 | 100.0% | 33 |
| `lat` | Latitude of the representative point (WGS84) | 34,840 | 82.1% | 30,978 |
| `lon` | Longitude of the representative point (WGS84) | 34,840 | 82.1% | 31,096 |
| `year_from` | Earliest year attested for any name or location of the place | 39,508 | 93.1% | 101 |
| `year_to` | Latest year attested (often `2100` = still in use / modern) | 39,508 | 93.1% | 95 |
| `time_periods` | Pleiades period terms the place is attested in, chronologically ordered, e.g. `classical \| roman \| modern` | 39,508 | 93.1% | 2,047 |
| `connections_out` | Relations from this place to others, as `type: other place title`, e.g. `part of (administrative): Aegyptus` | 11,256 | 26.5% | 5,617 |
| `connections_in` | Relations from other places to this one, as `other place title (type)` | 3,974 | 9.4% | 3,799 |
| `ancient_sources` | Ancient textual or epigraphic evidence cited for the place, e.g. `Plin., NH 4.103.6`, `Str. 4.6.8` | 4,864 | 11.5% | 4,222 |

Notes:
- `n_names` is `0` for 15,062 places (35.5%). These places have only a `title` and no attested name variants.

---

## `trismegistos.tsv`: Trismegistos places

"Ghost names" (TM entries flagged as non-existent places) were removed.

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `trismegistos_id` | Trismegistos Geo ID (primary key) | 64,507 | 100.0% | 64,507 |
| `name_standard` | TM's standard (Latinized) name; may contain lacunae such as `A.[ ]` | 64,507 | 100.0% | 60,450 |
| `names_latin` | Latin name variants | 13,509 | 20.9% | 12,637 |
| `names_greek` | Greek name variants (Greek script) | 14,721 | 22.8% | 13,308 |
| `names_egyptian` | Egyptian names in Egyptological transliteration, e.g. `Smn (Sw-mn)` | 1,969 | 3.1% | 1,604 |
| `names_coptic` | Coptic names (Coptic script) | 659 | 1.0% | 648 |
| `modern_name` | Modern name of the site, e.g. `Tukh el-Qaramus` | 7,176 | 11.1% | 7,061 |
| `ethnicon` | Demonyms derived from the place name, e.g. `Mytilenaios \| Mytilenaeus` | 5,006 | 7.8% | 4,858 |
| `status` | Settlement type in TM's vocabulary, e.g. `village`, `kleros`, `topos`, `region`; `?` marks uncertainty | 25,476 | 39.5% | 2,103 |
| `location` | Free-text position relative to another place, e.g. `near 00c Theogonis` | 34,759 | 53.9% | 13,613 |
| `country` | Modern country the place lies in | 64,507 | 100.0% | 142 |
| `region` | TM region; for Egypt a code (`00` Fayum, `U` Upper Egypt, …), elsewhere a region name | 64,507 | 100.0% | 191 |
| `nomos_code` | TM sub-region code, for Egypt the nome (e.g. `00c`, `U10a`) | 62,326 | 96.6% | 284 |
| `provincia` | Roman province, e.g. `Aegyptus`, `Achaia` | 64,506 | 99.99% | 180 |
| `lat` | Latitude (WGS84) | 24,617 | 38.2% | 24,309 |
| `lon` | Longitude (WGS84) | 24,617 | 38.2% | 24,246 |
| `begin_date` | Earliest year the place is attested in TM | 26,520 | 41.1% | 1,081 |
| `end_date` | Latest year the place is attested in TM | 26,520 | 41.1% | 1,074 |
| `n_texts` | Number of papyri linked to the place (rows in `trismegistos_texts.tsv`) | 64,507 | 100.0% | 127 |
| `n_texts_mentioning_name` | Number of those texts whose edition text contains the place name | 64,507 | 100.0% | 59 |
| `text_snippets` | Up to 5 context snippets from those texts, as `text title (date): …snippet…`; texts with an English translation first | 374 | 0.6% | 365 |

Notes:
- `n_texts > 0` for **731** places (1.1%). Only these places have rows in `trismegistos_texts.tsv`.
- `n_texts_mentioning_name > 0` for **374** places (0.6%), which is the same set that has `text_snippets`.
- Top countries: Egypt (13,585), Italy (7,624), Turkey (6,782), France (5,106), Spain (4,030), Greece (3,491).

---

## `trismegistos_texts.tsv`: texts linked to Trismegistos places

Papyri (from papyri.info: HGV, DCLP, DDbDP) that were written at, found at, or sent to a Trismegistos place. One row per (place, text) link. Covers **731** distinct places and **48,751** distinct texts.

| Column | Description | Non-empty | Coverage | Distinct values |
|---|---|---:|---:|---:|
| `trismegistos_id` | Trismegistos Geo ID of the place; joins to `trismegistos.tsv` | 58,595 | 100.0% | 731 |
| `tm_text_id` | Trismegistos Text ID | 58,595 | 100.0% | 48,751 |
| `relation` | How the text relates to the place: `located`, `found`, `composed`, `stored`, `sent`, … (combined with ` \| ` when several apply) | 58,595 | 100.0% | 13 |
| `title` | Title of the text, often in German (from HGV), e.g. `Arbeitsvertrag, Alexandrien` | 41,023 | 70.0% | 21,972 |
| `material` | Writing material, e.g. `Papyrus`, `Ostrakon`, `Holz` | 58,387 | 99.6% | 105 |
| `text_lang` | Language code(s) of the text, e.g. `grc`, `cop`, `la` | 54,924 | 93.7% | 16 |
| `year_from` | Earliest possible date of the text | 58,221 | 99.4% | 1,091 |
| `year_to` | Latest possible date of the text | 58,221 | 99.4% | 1,111 |
| `keywords` | HGV subject keywords (German), e.g. `Vertrag \| Arbeit \| Landwirtschaft` | 58,483 | 99.8% | 25,764 |
| `mentions_name` | `1` if the edition text contains the place name, otherwise `0` | 58,595 | 100.0% | 2 |
| `snippet` | About 80 characters of edition text on each side of the place-name mention | 11,414 | 19.5% | 11,123 |
| `edition_text` | Full transcription of the text in the original language; ` / ` marks line breaks, `[...]` marks gaps | 47,604 | 81.2% | 37,680 |
| `translation_en` | English translation, when one exists | 4,426 | 7.6% | 3,870 |

Notes:
- `mentions_name = 1` for 11,414 rows (19.5%), which are exactly the rows that have a `snippet`.
- `relation`: `located` 49,595 (84.6%), `found` 5,591, `composed | found` 1,638, `composed` 1,443, and 9 rarer combinations.
- `text_lang`: Greek `grc` 50,483 (86.2%), Coptic `cop` 2,774 (4.7%), Latin `la` 1,130 (1.9%), Syriac `syc` 328, Demotic `egy-Egyd` 115, plus a few others.
