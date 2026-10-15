# Wikidata Hebrew–Arabic toponyms

Every Wikidata item that has coordinates (P625) **and** both a Hebrew and an Arabic label. It is a large, synthetic set of modern names and the counterpart to the historical MEHDIE testsets. It follows the construction of the Wikidata set in Sagi et al. (2025), which reported 41,560 pairs after removing labels longer than two words. No such filter is applied here.

- Source: Wikidata via the QLever endpoint (https://qlever.dev/wikidata), queried 15 October 2026. Wikidata changes daily, so a rerun gives slightly different numbers.
- Licence: CC0 (Wikidata).

## Files

| File | Content |
|---|---|
| `wikidata_he_ar.tsv` | All items, tab-separated UTF-8, one row per item and label pair |
| `wikidata_he_ar_places.tsv` | Toponyms only: the same columns plus `place_class` (see [Places-only file](#places-only-file)) |
| `wikidata_he_ar.rq` | The SPARQL query that produced `wikidata_he_ar.tsv` |

## Size and ground truth

| | Count |
|---|---|
| Rows | 50,804 |
| Unique items (`qid`) | 50,721 |
| Ground truth pairs | 50,721, one per item |
| Items that are places (`wikidata_he_ar_places.tsv`) | 34,079 |
| Candidate pairs before blocking | ≈ 2.6 billion |

**Ground truth:** the Hebrew label and the Arabic label with the same `qid` are a match, and every other combination is a non-match. The matching is one-to-one: every Hebrew record has exactly one Arabic match, and there are no records without a match unless you create them, for example by removing some Arabic records.

83 rows are extra rows for 29 items that have more than one Hebrew or Arabic label. Keep one row per `qid`, or treat the extra labels as variants.

## Columns

| Column | Content | Filled |
|---|---|---|
| `qid` | Wikidata ID. Same QID = match | 100 % |
| `label_he` | Hebrew label | 100 % |
| `label_ar` | Arabic label | 100 % |
| `lat`, `lon` | One coordinate (arbitrary if the item has several) | 100 % |
| `n_coords` | Number of coordinates on the item (2,277 rows have more than one) | 100 % |
| `instance_of` | Type QIDs (P31), `\|`-separated | 99.8 % |
| `instance_of_label` | English names of the types, same order | 99.7 % |
| `admin_unit` | Administrative unit QID (P131), one value | 82.6 % |
| `inception` | Founding date (P571), ISO format; negative years are BCE | 44.1 % |
| `pleiades_id` | Pleiades ID (P1584) | 3.8 % |
| `he_wiki`, `ar_wiki` | Hebrew and Arabic Wikipedia article URLs | 53.7 % / 86.5 % |

74 items with coordinates only on other globes (Moon, Mars, …) were removed.

## Not everything is a place

The query only requires coordinates, so the data also contains universities, battles, airports, stadiums, publishers and awards. To keep places only, select items that are an instance of one of these classes, or of a subclass of one:

| Class | QID | Items |
|---|---|---|
| administrative territorial entity | Q56061 | 24,145 |
| human settlement | Q486972 | 17,721 |
| landform | Q271669 | 3,831 |
| body of water | Q15324 | 1,956 |
| archaeological site | Q839954 | 1,304 |
| watercourse | Q355304 | 1,016 |

Add this to the query's `WHERE` clause to filter:

```sparql
?item wdt:P31/wdt:P279* ?cl .
VALUES ?cl { wd:Q486972 wd:Q56061 wd:Q271669 wd:Q15324 wd:Q355304 wd:Q839954 }
```

## Places-only file

`wikidata_he_ar_places.tsv` keeps the items that are toponyms. It has 34,161 rows and 34,079 unique items; 82 extra rows come from 28 items with more than one label. The columns are the same as `wikidata_he_ar.tsv` plus `place_class`.

An item is kept if one of these holds:

1. It is an instance of one of the six classes above, or of a subclass of one. Island (Q23442) and historical country (Q3024240) were also included, but they add no items beyond the six.
2. Its direct type (`instance_of_label`) is a geographic region, e.g. `region`, `cultural region`, `natural region`, `continent`, `part of the world`, `coast`, `territory`. This adds 290 items such as Asia, Scandinavia, New England and Upper Galilee. The whole region class (Q82794 with subclasses) is *not* used, because it also contains squares, parks, zoos and museums.

| `place_class` | Items |
|---|---|
| administrative territorial entity | 24,143 |
| human settlement | 17,717 |
| landform | 3,784 |
| body of water | 1,956 |
| archaeological site | 1,301 |
| watercourse | 1,016 |
| island | 929 |
| historical country | 767 |
| geographic region | 290 |

An item can have several classes, separated by `|`.

**What was removed:** 16,932 items, mostly battles (1,052), universities, airports, publishers, stadiums, sieges, museums, languages, organisations, sports seasons, buildings, earthquakes and attacks.

**Remaining noise:** a few hundred items inside the classes are not clean toponyms. Examples are museums and buildings at archaeological sites, electoral constituencies (administrative entities), refugee and concentration camps (settlements) and a few shipwrecks. Filter further on `instance_of_label` if needed.

Coverage in the places file: `admin_unit` 91.5 %, `inception` 40.4 %, `pleiades_id` 5.4 %, `he_wiki` 50.3 %, `ar_wiki` 87.8 %.

## Mining extra attributes

More attributes can be added from Wikidata for the same items. The counts below are for the items selected by the base query.

| Category | Attribute | How (in SPARQL) | Items |
|---|---|---|---|
| Name | Hebrew name variants | `skos:altLabel`, lang `he` | 8,708 (17 %) |
| | Arabic name variants | `skos:altLabel`, lang `ar` | 13,121 (26 %) |
| | English label | `rdfs:label`, lang `en` | 50,530 (99 %) |
| | Official name | `wdt:P1448` | 14,804 (29 %) |
| | Native-language name | `wdt:P1705` | 17,552 (35 %) |
| | Named after | `wdt:P138` | 8,417 (17 %) |
| Geography | Country | `wdt:P17` | 49,211 (97 %) |
| | Neighbours | `wdt:P47` | 12,100 (24 %) |
| | Population | `wdt:P1082` | 23,644 (47 %) |
| | Elevation | `wdt:P2044` | 19,819 (39 %) |
| | Next to body of water | `wdt:P206` | 5,863 (12 %) |
| | On physical feature | `wdt:P706` | 2,921 (6 %) |
| Time and source | Dissolved | `wdt:P576` | 2,010 (4 %) |
| | Replaces / replaced by | `wdt:P1365` / `wdt:P1366` | 3,229 / 1,201 |
| | Described by source (encyclopedias) | `wdt:P1343` | 13,555 (27 %) |
| Text context | Description, Hebrew | `schema:description`, lang `he` | 32,444 (64 %) |
| | Description, Arabic | `schema:description`, lang `ar` | 35,474 (70 %) |
| | Description, English | `schema:description`, lang `en` | 50,081 (99 %) |
| | Wikipedia article text | MediaWiki API on `he_wiki` / `ar_wiki` (see below) | 54 % / 87 % |
| Other gazetteers | GeoNames ID | `wdt:P1566` | 31,204 (61 %) |
| | Getty TGN ID | `wdt:P1667` | 9,427 (19 %) |
| | Pleiades ID | `wdt:P1584` (already included) | 1,925 (4 %) |

### Query pattern

Fetch one attribute per query and join on `qid` in Python. A single query with many `OPTIONAL` clauses returns one row per combination of values and quickly gets too large.

```sparql
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?item ?value ?valueLabel WHERE {
  ?item wdt:P625 ?c ;
        rdfs:label ?he , ?ar .
  FILTER(LANG(?he) = "he") FILTER(LANG(?ar) = "ar")
  ?item wdt:P17 ?value .                                     # change the property here
  OPTIONAL { ?value rdfs:label ?valueLabel . FILTER(LANG(?valueLabel) = "en") }
}
```

For name variants and descriptions, replace the property line:

```sparql
?item skos:altLabel ?value . FILTER(LANG(?value) IN ("he", "ar"))    # PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
?item schema:description ?value . FILTER(LANG(?value) = "he")        # PREFIX schema: <http://schema.org/>
```

For values that only make sense with a date, such as historical official names or population, query the full statement with qualifiers:

```sparql
PREFIX p:  <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
  ?item p:P1448 ?st .
  ?st ps:P1448 ?value .
  OPTIONAL { ?st pq:P580 ?start }   # start time (P585 = point in time, for population)
  OPTIONAL { ?st pq:P582 ?end }     # end time
```

### Running queries from Python

```python
import urllib.parse, urllib.request

def qlever(query):
    req = urllib.request.Request(
        "https://qlever.dev/api/wikidata",
        data=urllib.parse.urlencode({"query": query}).encode(),
        headers={"Accept": "text/tab-separated-values"})
    lines = urllib.request.urlopen(req, timeout=600).read().decode().rstrip("\n").split("\n")
    head = [h.lstrip("?") for h in lines[0].split("\t")]
    return [dict(zip(head, l.split("\t"))) for l in lines[1:]]
```

Values come back as RDF terms, e.g. `<http://www.wikidata.org/entity/Q858>` or `"حلب"@ar`, so strip the brackets, quotes and language tags. QLever answers bursts with HTTP 429; space queries a few seconds apart and retry.

### Wikipedia article text

The Hebrew and Arabic articles are written separately, so they give each side its own text context. Fetch the lead section with the MediaWiki API, 20 titles per request:

```
https://he.wikipedia.org/w/api.php?action=query&format=json&formatversion=2
    &prop=extracts&exintro=1&explaintext=1&exlimit=20&redirects=1&titles=<title1>|<title2>|...
```

The title is the part of `he_wiki` / `ar_wiki` after `/wiki/`, URL-decoded. Send requests one at a time with about one second between them and a descriptive `User-Agent`. Wikipedia rate-limits bursts with HTTP 429. Expect about an hour for both languages.

### Other gazetteers through the ID columns

| ID | Lookup | Gives |
|---|---|---|
| GeoNames | `https://www.geonames.org/<id>` or the dump `allCountries.zip` | Alternate names in many languages, feature class, population |
| Pleiades | `https://pleiades.stoa.org/places/<id>/json` or https://pleiades.stoa.org/downloads | Ancient names, time periods, locations |
| Getty TGN | `http://vocab.getty.edu/tgn/<id>` | Historical names with dates |

## Avoiding leakage

The ground truth is the shared `qid`, and every Wikidata attribute belongs to that same item. If both the Hebrew and the Arabic record get the same coordinates, country or population, those fields alone solve the match. Options:

1. Give each side only its own language's fields: label, name variants, description and Wikipedia text.
2. Give shared attributes such as geography to the candidate side only, as a gazetteer would have.
3. Take geography for one side from another source (GeoNames, Pleiades) or add noise to the coordinates.
4. Never show `qid`, Wikipedia URLs (they contain the title) or external IDs to the matching method.

## Known issues

- **Some labels are useless.** A few are placeholders like `…`. Some are identical in both languages (e.g. Latin-script names), and many are long multi-word names. Sagi et al. removed labels longer than two words.
- **Popular modern names.** These are well-known places and very likely in LLM training data, unlike the historical MEHDIE names.
- **Time is weak.** Only 44 % have an inception date.
