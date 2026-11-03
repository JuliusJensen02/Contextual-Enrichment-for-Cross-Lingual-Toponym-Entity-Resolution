# Pleiades ↔ Trismegistos

A matching set between the two big gazetteers of the ancient world: Pleiades (42,417 places) and Trismegistos Places (64,507 places). Both sides are cut down to the attributes a matching method may see; all IDs and links to other databases are removed and kept only in `em.tsv`.

- Pleiades: JSON dump of 2 November 2026, https://atlantides.org/downloads/pleiades/json/ (CC BY 3.0)
- Trismegistos: `../Trismegistos/trismegistos_places.tsv` (TM Data Services, CC BY-SA 4.0)
- PAThs: `../PAThs/paths_places.tsv` (CC BY-NC-SA 4.0), used as a third source of links
- Built with `scripts/build_pleiades_trismegistos.py`, November 2026

## Files

| File | Content |
|---|---|
| `pleiades.tsv` | One row per Pleiades place (42,417) |
| `trismegistos.tsv` | One row per TM place, ghost names removed (64,507) |
| `em.tsv` | **Ground truth:** 13,890 Pleiades ↔ TM pairs |
| `trismegistos_texts.tsv` | Papyri and ostraca written or found at a TM place, with full edition text (58,595 place–text links, 731 places) |

Multiple values in a cell are separated by ` | `.

## `em.tsv`

| Column | Content |
|---|---|
| `pleiades_id`, `trismegistos_id` | The pair |
| `pleiades_title`, `trismegistos_name` | Titles, for reading only |
| `sources` | Who asserts the link: `pleiades` (reference of type `citesAsRelated` to a TM place), `trismegistos` (TM's `close_matches` to Pleiades), `paths` (PAThs `skos:exactMatch` to both) |
| `n_sources` | 1–3 |

| Sources | Pairs |
|---|---|
| pleiades + trismegistos + paths | 124 |
| pleiades + trismegistos | 5,303 |
| trismegistos + paths | 38 |
| pleiades + paths | 2 |
| trismegistos only | 7,944 |
| pleiades only | 446 |
| paths only | 33 |

The pairs cover 13,666 Pleiades places and 13,396 TM places. They are **not one-to-one**: 208 Pleiades places match more than one TM place, and 428 TM places match more than one Pleiades place (e.g. TM Memphis → Pleiades Memphis and Abu Sir).

None of the sources says "same place" in a checked way: Pleiades uses "cites as related", TM puts every partner link in `close_matches`, and PAThs uses `exactMatch` for everything. Pairs with `n_sources >= 2` (5,467) are the most reliable. Single-source pairs include neighbouring or nested places.

23 pairs were left out because one ID does not exist on the other side: 13 Pleiades IDs not in the dump, and 10 TM IDs that are missing or ghost names.

## Columns in `pleiades.tsv`

| Column | Content | Filled |
|---|---|---|
| `pleiades_id` | Pleiades ID (join key only) | 100 % |
| `title` | Pleiades title | 100 % |
| `description` | One-sentence description | 100 % |
| `details` | Longer editorial notes, HTML, URLs and the literal "None" removed. Mostly "The Barrington Atlas Directory notes: <modern name>" | 76 % |
| `place_types` | settlement, fort, river, … | 100 % |
| `names_romanized` | All romanized forms | 64 % |
| `names_greek`, `names_latin` | Attested Greek / Latin spellings in their own script | 7 %, 9 % |
| `names_by_language` | Every name that has a language, as `name@lang` (attested form, else first romanized form), e.g. `Mefi@cop`, `Mīt Ruhaina@arb` | 30 % |
| `n_names` | Number of name records | – |
| `lat`, `lon` | Representative point | 82 % |
| `year_from`, `year_to` | Min/max over names and locations (2100 = until today) | 93 % |
| `time_periods` | Attested periods (archaic … late-antique, modern, …) | 93 % |
| `connections_out` | Related places, as `type: title` (e.g. `part of (administrative): Ptolemaic Kingdom`) | 27 % |
| `connections_in` | Places that connect to this one, as `title (type)` | 9 % |
| `ancient_sources` | Ancient texts cited as evidence (e.g. `Hdt. (Godley: Perseus) 2.99`) | 11 % |

**Dropped from Pleiades:** `uri` (= ID); editorial metadata (`creators`, `contributors`, `history`, `created`, `review_state`, `rights`); `provenance` (Barrington Atlas map grid reference); `subject` (DARE/UNESCO tags); `bbox`, `features` and the full `locations` geometry (reduced to `lat`/`lon`); `placeTypeURIs` (duplicate); per-name details (accuracy, certainty, dates; folded into `year_*` and `time_periods`); `connectsWith` URIs (replaced by titles); all references except ancient sources: `citesAsRelated` (links to TM, Wikidata, GeoNames, …, i.e. the ground truth), `seeAlso`/`seeFurther` (Wikipedia, modern literature).

## Columns in `trismegistos.tsv`

| Column | Content | Filled |
|---|---|---|
| `trismegistos_id` | TM Geo ID (join key only) | 100 % |
| `name_standard` | TM standard name | 100 % |
| `names_latin`, `names_greek`, `names_egyptian`, `names_coptic` | Name variants per language | 21 %, 23 %, 3 %, 1 % |
| `modern_name` | Modern name, taken from the brackets at the end of TM's `full_name` (e.g. `Abaton (Biga Island)` → `Biga Island`) | 11 % (49 % of matched TM places) |
| `ethnicon` | Ethnic adjectives | 8 % |
| `status` | Type of place with Greek/Latin term | 39 % |
| `location` | Free-text location; TM IDs in parentheses removed | 54 % |
| `country`, `region`, `nomos_code`, `provincia` | Modern country, ancient region, Egyptian nome, Roman province | 100 %, 100 %, 97 %, 100 % |
| `lat`, `lon` | Point | 38 % |
| `begin_date`, `end_date` | First/last attestation in TM texts | 41 % |
| `n_texts` | Papyri/ostraca written or found at this place (place-level links only, not nome/region) | 731 places (552 matched) |
| `n_texts_mentioning_name` | How many of those texts contain the place's name | 374 places (332 matched) |
| `text_snippets` | Up to 5 passages around the place name, as `title (date): …text…`; texts with an English translation first, then oldest first. Serves as TM's "description" | 374 places |

**Dropped from TM:** `uri` (= ID); `responder_names` (same names as the language columns); `full_name` (= country + nome code + standard name; the bracketed modern name is kept as `modern_name`); `coordinates` (= `lat`/`lon`); `begin_date_formatted`, `end_date_formatted` (duplicates); `pleiades_id`, `geonames`, `exact_matches`, `close_matches`, `broad_matches`, all 15 `rel_*` columns and `wikipedia_urls` (links to other databases, i.e. the ground truth); `n_texts_papyri_incl_nome_region`, `in_dump`, `in_sql` (build bookkeeping). **Rows dropped:** 663 ghost names (readings later shown not to be places).

TM has **no description field** in any of its data services (table dump, SQL export, GeoResponder, GeoRelations). Text context comes from the papyri instead (`text_snippets` and `trismegistos_texts.tsv`), plus `location`, `status` and `modern_name`. Wikipedia articles can be joined from `../Trismegistos/trismegistos_wikipedia.tsv` on `trismegistos_id` = `geo_id`; they give the modern name, so use them with care.

## `trismegistos_texts.tsv`

One row per (TM place, text), from `../Trismegistos/trismegistos_place_texts.tsv` (place-level links only) and `../Trismegistos/trismegistos_texts.tsv` (papyri.info: HGV, DDbDP, DCLP).

| Column | Content |
|---|---|
| `trismegistos_id`, `tm_text_id` | Place and text |
| `relation` | `located`, `found`, `composed`, `stored`, `sent`, … |
| `title`, `material`, `text_lang`, `keywords` | Text metadata (HGV titles and keywords are often German) |
| `year_from`, `year_to` | Date of the text (negative = BCE) |
| `mentions_name` | 1 if the edition text contains the place's name (11,414 texts) |
| `snippet` | ±80 characters around the first mention |
| `edition_text`, `translation_en` | Full reading text; English translation where papyri.info has one |

Name matching: diacritics and case are ignored and the last two letters of the first word of each Greek/Latin name are dropped, so inflected forms match (`Μέμφει`, `Μεμφίτου` for Memphis). Places that share a first word (the several `Ptolemais`, `Ibion`, `Dios`) can pick up mentions of each other.

Coverage is almost only Egypt, and only 552 of the 13,396 matched TM places have texts. Texts are linked to where they were written or found, which does not mean they mention the place: only 19 % do.

## Avoiding leakage

- **Coordinates.** 7,980 matched pairs have coordinates on both sides, and 4,632 of them are identical to 4 decimals (TM copied them from Pleiades). Use coordinates on one side only, or round/perturb them.
- **Modern names on both sides.** TM `modern_name` and Pleiades `details` ("Barrington Atlas Directory notes: …") often give the same modern name, which makes a match trivial. Use them on one side only for a cross-lingual test.
- **Shared names.** TM and Pleiades both build on the Barrington Atlas, so Latin `title`/`name_standard` are often identical. The cross-lingual signal is in Greek, Egyptian and Coptic names.
- **Text mentions.** 5 Pleiades `details` mention Trismegistos in prose (no IDs).
- **IDs.** Never show `pleiades_id` or `trismegistos_id` to the matching method.

## Rebuilding

```bash
python scripts/build_pleiades_references.py     # downloads the Pleiades JSON dump into datasets/Pleiades/.cache
python scripts/build_pleiades_connections.py    # optional: GIS zip, gives readable connection types
python scripts/build_pleiades_trismegistos.py   # ~30 s; needs ../Trismegistos/ for the texts
```
