# Pleiades (ancient places) ↔ Wikidata Hebrew/Arabic labels

Pleiades is a gazetteer of ancient places in the Mediterranean, the Near East and beyond. It has ancient names (mostly Latin and Ancient Greek, plus Akkadian, Arabic, Hebrew and others), locations and time spans. Some Wikidata items carry a Pleiades ID (property P1584) and also have a Hebrew or Arabic label. These items connect the ancient record to a modern Hebrew/Arabic name, and that connection is the ground truth.

- Source: Pleiades GIS data package, https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip, export of 14 October 2026, downloaded 15 October 2026. Pleiades exports daily.
- Wikidata links: fetched from QLever (https://qlever.dev/wikidata) on 15 October 2026
- Licence: Pleiades CC BY 3.0; Wikidata CC0

## Files

| File | Content |
|---|---|
| `pleiades_places.tsv` | The Pleiades side: one row per Pleiades place, with ancient names and attributes (42,399 places) |
| `pleiades_wikidata_links.tsv` | **Ground truth** and the Hebrew/Arabic side: Pleiades place ↔ Wikidata item with Hebrew and/or Arabic label (4,514 links) |

## Size and ground truth

| | Count |
|---|---|
| Pleiades places | 42,399 |
| Links Pleiades ↔ Wikidata | 4,514 |
| … of which the Pleiades place is in `pleiades_places.tsv` | 4,497 |
| … unique Wikidata items / unique Pleiades places | 4,470 / 4,448 |
| … with a Hebrew label | 2,948 |
| … with an Arabic label | 3,618 |
| … with both | 2,052 |
| Places with Arabic names inside Pleiades itself | 553 |
| Places with Hebrew names inside Pleiades itself | 82 |

The links are not strictly one-to-one:

- 58 Pleiades places are linked from more than one Wikidata item, and 42 Wikidata items link to more than one Pleiades place.
- 17 links point to Pleiades IDs that are not in this export (`in_pleiades_dump = 0`), e.g. withdrawn or merged places.

Most common types of the linked places: settlement 1,769, archaeological site 449, river 332, island 253, label 248, people 193, temple 169, modern settlement 153, region 149, mountain 117.

## Which records belong together

`pleiades_id` is the key. A row in `pleiades_wikidata_links.tsv` says that the Wikidata item (`qid`, with `label_he` / `label_ar`) is the same place as the Pleiades place with that `pleiades_id`.

| pleiades_id | qid | label_he | label_ar |
|---|---|---|---|
| 177528 | Q71 | ז'נבה | جنيف |

Pleiades place 177528 is "Genava" in `pleiades_places.tsv`, so Genava ↔ ז'נבה / جنيف is a match.

```python
import csv
csv.field_size_limit(10**9)
read = lambda p: list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))

places = {r["pleiades_id"]: r for r in read("pleiades_places.tsv")}
links = [r for r in read("pleiades_wikidata_links.tsv") if r["in_pleiades_dump"] == "1"]

# Pleiades side: ancient names; Hebrew/Arabic side: Wikidata labels; ground truth: pleiades_id
pairs = [(l["pleiades_id"], places[l["pleiades_id"]]["names_romanized"], l["label_he"], l["label_ar"])
         for l in links]
print(len(pairs))   # 4,497
```

Two tasks are possible:

1. **Ancient name ↔ modern Hebrew/Arabic name:** match the Pleiades names (`title`, `names_romanized`, `names_attested_other`) against `label_he` / `label_ar`. The other 37,968 Pleiades places without a link can serve as distractors.
2. **Within Pleiades:** for the 553 places with Arabic names (and 82 with Hebrew names), those names and the Latin/Greek names of the same row are already matched.

A proposed pair is correct if it has the same `pleiades_id`. Never show `pleiades_id` or `qid` to the matching method.

## Columns in `pleiades_places.tsv`

| Column | Content | Filled |
|---|---|---|
| `pleiades_id`, `uri` | Pleiades ID and URI | 100 % |
| `title` | Pleiades title (usually the main Latin/Greek name) | 100 % |
| `description` | Short English description | 100 % |
| `place_types` | Place types, `\|`-separated (settlement, river, fort, people, …) | 100 % |
| `lat`, `lon` | Representative point | 82 % |
| `location_precision` | `precise` or `rough` | 100 % |
| `year_from`, `year_to` | Earliest and latest year over the place's names and point locations (negative = BCE) | 82 % |
| `n_names` | Number of name records | – |
| `names_romanized` | Romanised names, `\|`-separated | 64 % |
| `names_ar` | Attested Arabic names (language tags `ar`, `arb`, `arz`, …) | 1.3 % |
| `names_he` | Attested Hebrew names (`he`, `hbo`) | 0.2 % |
| `names_attested_other` | Other attested names as `name@lang` (Greek, Latin, Akkadian, Turkish, …) | 25 % |
| `provenance` | Where the record comes from (often the Barrington Atlas) | 100 % |

## Columns in `pleiades_wikidata_links.tsv`

| Column | Content |
|---|---|
| `pleiades_id` | Pleiades ID (join key to `pleiades_places.tsv`) |
| `qid` | Wikidata item |
| `label_he`, `label_ar` | Hebrew and Arabic Wikidata labels (one may be empty) |
| `in_pleiades_dump` | 1 if the Pleiades ID exists in `pleiades_places.tsv` |

The links can also be joined on `qid` to `../Wikidata-he-ar/` to get the Wikidata attributes described there.

## Coverage by data category

| Category | Fields |
|---|---|
| Name | `title`, `names_romanized`, `names_attested_other`, `names_ar`, `names_he`; `label_he`, `label_ar` on the Wikidata side |
| Geography | `lat`/`lon`, `location_precision`, `place_types` |
| Time and source | `year_from`/`year_to`, `provenance` |
| Text context | `description` |

## Avoiding leakage

- **Coordinates often share an origin.** Coordinates of linked Wikidata items often come from Pleiades or a common source. Do not give both sides coordinates; use Pleiades geography on one side only.
- **`description` often names the modern place.** 687 of the 4,497 linked places mention it, e.g. "Genava (modern Geneva) was originally an oppidum of the Allobroges…". That can give away the match. Use it with care, or only on the Pleiades side when the other side is Hebrew/Arabic only.
- **Identifiers.** Never show `pleiades_id`, `qid` or `uri` to the matching method.

## Known issues

- **"Modern" upper bound:** 4,308 places have `year_to = 2100`, the Pleiades convention for "until modern times". Treat it as open-ended, not as a real date.
- **Not everything is a toponym:** types include `people` (ethnic groups), `label` (map labels) and `road`. Filter on `place_types` if needed.
- **Few Semitic names inside Pleiades:** only 553 places have Arabic names and 82 have Hebrew names.
- **Unlocated places:** 6,503 places are typed `unlocated` and have no coordinates.

## Rebuilding

The two files were built with a small Python script (standard library only, not kept in this folder).

**`pleiades_places.tsv`:**
1. Download and unzip `pleiades_gis_data.zip`. The tables are in `data/gis/`, and Pleiades' own `README.md` there describes every table.
2. Take one row per place from `places.csv`: `id`, `uri`, `title`, `description`, `representative_latitude`, `representative_longitude`, `location_precision`, `provenance`.
3. Join from the other tables:

| Columns | Source table |
|---|---|
| `place_types` | `places_place_types.csv` |
| `names_*` | `names.csv`, grouped by `place_id`. `romanized_form_1–3` give `names_romanized`; `attested_form` is split by `language_tag` |
| `year_from`, `year_to` | Minimum and maximum of `year_after_which` / `year_before_which` over `names.csv` and `location_points.csv` |

**`pleiades_wikidata_links.tsv`:** run this query on QLever.

```sparql
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?item ?pleiades ?he ?ar WHERE {
  ?item wdt:P1584 ?pleiades .
  OPTIONAL { ?item rdfs:label ?he . FILTER(LANG(?he) = "he") }
  OPTIONAL { ?item rdfs:label ?ar . FILTER(LANG(?ar) = "ar") }
  FILTER(BOUND(?he) || BOUND(?ar))
}
```

Single places are also available as JSON at `https://pleiades.stoa.org/places/<id>/json`. The full JSON dump is at https://atlantides.org/downloads/pleiades/json/pleiades-places-latest.json.gz.
