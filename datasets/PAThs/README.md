# PAThs Places

PAThs ("Tracking Papyrus and Parchment Paths: An Archaeological Atlas of Coptic Literature") was an ERC Advanced Grant project at Sapienza University of Rome (PI Paola Buzi). It maps where Coptic literary manuscripts were produced, copied, used and kept. Its gazetteer covers 459 sites in Egypt and Nubia with a "Coptic phase" (3rd–11th c. CE): towns, monasteries, hermitages, tombs reused as cells, nomes and regions. Each place has an English standard name and name variants in Egyptian (transliterated), Greek, Latin, Coptic, Arabic and English.

- Source: Pelagios RDF export, https://docs.paths-erc.eu/raw-data/pelagios-rdf/paths.places.ttl (CC BY-NC-SA 4.0, maintained by Julian Bogdani)
- Documentation: field definitions https://docs.paths-erc.eu/handbook/places, DB schema https://docs.paths-erc.eu/schema/places, atlas https://atlas.paths-erc.eu
- Built with `scripts/build_paths.py`, November 2026

## Files

| File | Content |
|---|---|
| `paths.places.ttl` | The raw Turtle download (LAWD / SKOS / GeoSPARQL / PeriodO vocabularies) |
| `paths_places.tsv` | One row per PAThs place, names grouped per language (459 rows) |
| `paths_names.tsv` | One row per name variant: `paths_id`, `lang`, `name`, `arabic_script` (2,171 rows) |

## How the links to Pleiades and Trismegistos are made

The links are manual. The PAThs database has two plain text fields per place, `tmgeo` ("Trismegistos GeoID, if available") and `pleiades` ("Pleiades Id, if available"), which the project's editors filled in while compiling each record. The RDF export turns them into `skos:exactMatch` triples:

```turtle
<http://paths.uniroma1.it/atlas/places/1> a lawd:Place ;
  skos:exactMatch <http://pleiades.stoa.org/places/736963>, <https://www.trismegistos.org/place/1344> ;
  rdfs:label "Memphis"@en ;
  lawd:hasName [ lawd:variantForm "Μέμφις"@grc ], [ lawd:variantForm "ⲙⲛⲫⲉ"@cop ], [ lawd:variantForm "منف"@arz ] ...
```

They are not computed (no name or coordinate matching), and nothing in the file tells you whether a given link was checked. `exactMatch` is used even where the target is broader or narrower (e.g. Valley of the Kings tombs point to the Pleiades place for the whole Valley).

| | Places |
|---|---|
| Linked to Pleiades | 319 (Karnak has 2 IDs) |
| Linked to Trismegistos | 348 (7 places have 2–3 TM IDs, e.g. Buto, Karnak) |
| Linked to both | 306 |
| No link | 98 |

Checked against the other datasets in this repo:

- 318 of 320 Pleiades IDs exist in `../Pleiades/pleiades_places.tsv`; 356 of 357 TM IDs exist in `../Trismegistos/trismegistos_places.tsv`.
- For the 284 (PAThs place, TM ID) pairs where both PAThs and TM give a Pleiades ID, they agree 263 times and disagree 21 times (one of these only because TM's ID has a trailing `/`). The disagreements are mostly neighbouring or nested places (Leontopolis 727147 vs 727146, Nitria vs Wadi Natrun, Speos Artemidos).

This makes PAThs a small, independent third source of Pleiades ↔ TM links, and a source of Coptic and Arabic names for places in those datasets.

## Columns in `paths_places.tsv`

| Column | Content | Filled |
|---|---|---|
| `paths_id`, `uri` | PAThs place ID and URI (`http://paths.uniroma1.it/atlas/places/<id>`) | 100 % |
| `label`, `primary_form` | English standard name (identical in this export) | 100 % |
| `names_egyptian` | Transliterated Egyptian (`Ḥw.t-kȝ-Ptḥ`) | 100 places |
| `names_greek`, `names_latin` | Greek and Latin forms | 178, 38 places |
| `names_coptic` | Coptic forms | 155 places |
| `names_arabic` | Arabic forms (tag `arz`). 4 of 214 are romanised, not in Arabic script (`Karanōg`) | 181 places |
| `names_english` | English / modern romanised forms (tag `eng`, often repeats `label`) | 435 places |
| `n_names` | Number of distinct variants (15 places have none) | – |
| `lat`, `lon` | From the WKT point. **Only 1 place (Memphis) has coordinates** in this export | 1 place |
| `earliest_year`, `latest_year` | Coptic phase of the site (CE), from PeriodO `earliestYear`/`latestYear`; range 50–1500 | 248 places |
| `dc_temporal` | `latest/latest` in every row, i.e. an export bug. Use the two columns above | 248 places |
| `pleiades_id`, `tm_geo_id` | Linked IDs, ` \| `-separated | 319, 348 places |
| `other_matches` | Any other `exactMatch` URI (empty in the current export) | – |

Multiple values in a cell are separated by ` | `.

## Avoiding leakage

- **`pleiades_id`, `tm_geo_id`, `uri`** are the ground truth. Never show them to the matching method.
- **`names_english` and `label`** are often the same romanised form that Pleiades / TM use as their title, so a match on those is close to trivial. Use the Coptic, Arabic or Greek forms on one side for a real cross-lingual test.
- PAThs names were partly compiled from TM and Pleiades, so the same Greek spelling can appear on both sides.

## Known issues

- **Almost no coordinates or descriptions.** The Pelagios export leaves out the DB's `description`, `typology`, `nomos`, `province` and geodata fields. The atlas web app and API (https://atlas.paths-erc.eu) have them.
- **Probable typos in IDs:** Pleiades `864788873` (Western Thebes DeM 1401; TM's Valley of the Kings uses `864388873`) and `7272741` (Taposiris Magna; probably `727274`) do not exist in Pleiades. TM `17677` (Philae) is not in our TM file.
- **Stray whitespace** in some names (`" Λητοῦς Πόλις"`) is stripped in the TSVs.
- Licence is **non-commercial** (CC BY-NC-SA), unlike Pleiades (CC BY) and TM (CC BY-SA).

## Rebuilding

```bash
python scripts/build_paths.py            # uses paths.places.ttl if present, else downloads it
python scripts/build_paths.py --refresh  # re-download the TTL
```

Python standard library only (a small Turtle parser is included in the script).
