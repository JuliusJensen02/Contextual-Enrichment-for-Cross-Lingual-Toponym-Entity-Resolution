# Trismegistos Places (TM Geo)

Trismegistos (KU Leuven) is a metadata hub for texts from the ancient world, c. 800 BCE – 800 CE. TM Places is its gazetteer: 65,170 places with Latin, Greek, Egyptian (Demotic/hieroglyphic) and Coptic names, ethnics, status, location, dates and links to about 30 partner projects. It is strongest for Egypt (13,585 places), followed by Italy, Turkey, France, Spain and Greece.

- Source: TM Data Services, https://www.trismegistos.org/dataservices/ (CC BY-SA 4.0). Cite as described at https://www.trismegistos.org/about_how_to_cite.php
- Texts: papyri.info `idp.data` (https://github.com/papyri/idp.data), i.e. HGV, DDbDP, DCLP and translations (CC BY 3.0)
- Wikipedia: the articles that TM links to (CC BY-SA)
- Built with `scripts/build_trismegistos.py`, November 2026

## Files

| File | Content |
|---|---|
| `TM_geo.sql` | MySQL export of TM's `geo` table (phpMyAdmin, 8 April 2026). Used for begin/end dates |
| `trismegistos_places.tsv` | One row per TM Geo ID: names, attributes, coordinates, dates, links to partner projects (65,170 rows) |
| `trismegistos_place_texts.tsv` | TM Geo ID ↔ TM text ID: where a papyrus or ostracon was written or found (102,244 links, 775 places) |
| `trismegistos_texts.tsv` | One row per TM text: metadata, **full edition text** and translations (81,980 texts) |
| `trismegistos_wikipedia.tsv` | TM Geo ID ↔ Wikipedia article with **full plain text** (one row per link, about 9,850 articles for 8,911 places) |
| `.cache/` | Raw downloads and API responses (git-ignored, used to resume the script) |

## Which records belong together

`geo_id` (the TM Geo ID) is the key, and every other file joins on it. `pleiades_id`, `rel_Syriaca` and the Wikipedia URLs link the places to `../Pleiades/`, `../Syriaca/` and `../Wikidata-he-ar/`. Those links are ground truth across datasets (see "Avoiding leakage").

```python
import csv
csv.field_size_limit(10**9)
read = lambda p: list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))

places = {r["geo_id"]: r for r in read("trismegistos_places.tsv")}
texts = {r["tm_text_id"]: r for r in read("trismegistos_texts.tsv")}
links = [l for l in read("trismegistos_place_texts.tsv") if l["place_level"] == "place"]

# all texts written/found at Tebtynis (2287)
tebt = [texts[l["tm_text_id"]] for l in links if l["geo_id"] == "2287"]
```

## Columns in `trismegistos_places.tsv`

| Column | Content | Filled |
|---|---|---|
| `geo_id`, `uri` | TM Geo ID and stable URI | 100 % |
| `name_standard` | TM standard name (romanised) | 100 % |
| `name_latin` | Latin name(s), ` - `-separated | 21 % |
| `unicode_greek`, `unicode_egyptian`, `unicode_coptic` | Greek, Egyptian (transliterated) and Coptic names | 24 %, 3 %, 1 % |
| `responder_names` | Same names from GeoResponder as `name@language` | – |
| `full_name` | Country, region/nome code and standard name | 100 % |
| `status` | Type of place with the Greek/Latin term (village: kome, city: polis, …) | 39 % |
| `ethnicon` | Ethnic adjective(s) | 8 % |
| `location` | Free-text location, often relative to other TM places with their IDs | 53 % |
| `country`, `region`, `nomos_code`, `provincia` | Modern country; ancient region (3rd c. BCE); Egyptian nome; Roman province (200 CE) | 100 %, 100 %, 96 %, 99 % |
| `lat`, `lon` (`coordinates`) | Point location | 38 % |
| `begin_date`, `end_date` (+ `_formatted`) | First and last attestation in TM texts (negative = BCE), from `TM_geo.sql` | 41 % |
| `pleiades_id`, `geonames` | Pleiades / GeoNames IDs (from GeoRelations) | 20 %, 6 % |
| `exact_matches`, `close_matches`, `broad_matches` | Partner URIs as `Project=URI \| …` (Pleiades, DARE, ToposText, Nomisma, EDH, Syriaca, Wikipedia, …) | 41 % |
| `rel_<Partner>` | Partner IDs from GeoRelations, `\|`-separated (Pleiades, Syriaca, EDH, DASI, Livius, Wikipedia, …) | – |
| `wikipedia_urls` | Linked Wikipedia articles (en 7.6k, de 1.1k, it, fr, es, …) | 14 % |
| `n_texts_papyri` | Texts in `trismegistos_place_texts.tsv` linked at place level | – |
| `n_texts_papyri_incl_nome_region` | Same, including nome/region-level links | – |
| `in_dump`, `in_sql` | Whether the place is in the live dump / in `TM_geo.sql` | – |

## Columns in `trismegistos_texts.tsv` and `trismegistos_place_texts.tsv`

| Column | Content |
|---|---|
| `tm_text_id` | TM text ID (`https://www.trismegistos.org/text/<id>`) |
| `sources` | HGV (metadata), DDbDP (documentary edition), DCLP (literary papyri) |
| `title`, `material`, `keywords` | HGV/DCLP metadata; keywords are mostly German (HGV) or English (DCLP) |
| `orig_place`, `geo_ids` | Place of origin as written in the source, and its TM Geo IDs |
| `orig_date`, `year_from`, `year_to` | Date (negative = BCE) |
| `text_lang` | `grc` 68k, `cop` 3k, `la` 2.6k, `syc`, Demotic, Aramaic, Arabic, … |
| `edition_text` | Reading text of the edition: abbreviations expanded, restorations kept without brackets, lost text as `[...]`, lines separated by ` / ` and multiple editions by ` // ` (63,573 texts) |
| `translation_en`, `translation_de`, `translation_other` | Translations from papyri.info (5.7k English, 230 German) |
| `place_level` (link file) | `place`, `nome`, `region` or `province`. A nome link (e.g. Arsinoites) is much less specific |
| `provenance_type` (link file) | `located`, `found`, `composed`, `sent`, … |

`trismegistos_wikipedia.tsv` has `geo_id`, `wikipedia_url`, `lang`, `title` (after redirects), `missing` and `text`. The text is converted from wikitext: templates, tables, references and the back-matter sections are removed.

## Coverage by data category

| Category | Fields |
|---|---|
| Name | `name_standard`, `name_latin`, `unicode_greek`, `unicode_egyptian`, `unicode_coptic`, `ethnicon` |
| Geography | `lat`/`lon`, `country`, `region`, `nomos_code`, `provincia`, `location`, `status` |
| Time | `begin_date`/`end_date`; `year_from`/`year_to` per text |
| Text context | `location`; edition texts and translations (775 places, almost all in Egypt); Wikipedia (8,911 places) |

## Avoiding leakage

- **Identifiers and links.** `pleiades_id`, `geonames`, `rel_*`, `*_matches` and `wikipedia_urls` point straight at other datasets. Never show them to the matching method.
- **`location` contains TM IDs**, e.g. `near 00c Tebtynis (2287)`. Strip the numbers in parentheses if needed.
- **Wikipedia gives the modern name.** It often lists modern and other-language names, and is likely in LLM training data. Use it on one side only.
- **Coordinates** of linked Pleiades/Wikidata places often come from the same source.

## Known issues

- **Ghost names:** 663 places have `country = ghost name` (readings later shown not to be places). Filter them out.
- **Fragmentary names:** Many Egyptian toponyms are fragmentary (`Ab[ ] Epoikion`, `A.[ ]`).
- **Text links are mostly Egyptian:** papyri.info covers papyri and ostraca, so only 775 places get texts. The place→text links in TM itself (its extended RDF) return HTTP 500, and Latin inscriptions (EDH) block scripted downloads, so neither is included.
- **Restored text is unmarked:** `edition_text` is a reading text and does not show which letters are restored.
- **Missing fields in the dump:** the live dump ignores `pleiades_id`/`geonames` and has no dates. Both are filled from GeoRelations and `TM_geo.sql`.

## Rebuilding

```bash
python scripts/build_trismegistos.py --contact you@example.org   # ~1.5–2 h first run, minutes afterwards
python scripts/build_trismegistos.py --limit 200                  # quick test on the first 200 places
python scripts/build_trismegistos.py --refresh                    # re-download dump + papyri data
```

No API keys are needed. `--contact` only goes into the User-Agent, which Wikimedia asks for. Python standard library only.
