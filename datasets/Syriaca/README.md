# Syriaca.org – The Syriac Gazetteer (Syriac ↔ Arabic)

Places from *The Syriac Gazetteer* (Syriaca.org): towns, monasteries, dioceses, regions and natural features relevant to Syriac Christianity in the Middle East. Many records give the place's name both in Syriac and in Arabic, attested in historical sources. This makes it a historical Syriac ↔ Arabic matching set with ground truth.

- Source: https://github.com/srophe/syriaca-data (`data/places/tei`), commit `fefe80f5aabebeef5ee3cef66d3d344cf573f173` (23 April 2026)
- Website: http://syriaca.org/geo
- Licence: CC BY 3.0 (some records incorporate CC BY material from cited works; see each TEI header)

## Files

| File | Content |
|---|---|
| `syriaca_places.tsv` | One row per place, all attributes flattened from the TEI records (3,485 places) |

The original TEI files are not kept here. See [Rebuilding](#rebuilding) for how to get them.

## Size and ground truth

| | Count |
|---|---|
| Places | 3,485 |
| Places with at least one Syriac name | 954 |
| Places with at least one Arabic name | 801 |
| **Places with both (ground truth pairs)** | **547** |

**Ground truth:** a place's Syriac and Arabic names describe the same place, because they sit in the same record. Split the records into a Syriac side and an Arabic side to get 547 matched pairs. The other places only serve as distractors on one side. Most matched places have 1–3 names per language (Syriac: mostly 2, often an unvocalised and a vocalised form; Arabic: mostly 1–2), so the task can be run at place level or name level (split `names_syr` / `names_ar` on `|`).

Types of the 547 matched places: settlement 300, monastery 107, region 48, diocese 21, mountain 13, island 10, province 8, river 8, other 32.

Syriaca records also link to each other (`same_as_syriaca`) and to Pleiades (`pleiades_id`, 580 places). These give extra cross-dataset ground truth, e.g. Syriaca ↔ Pleiades.

## Columns in `syriaca_places.tsv`

Filled percentages over all 3,485 places; in brackets over the 547 matched places.

| Column | Content | Filled |
|---|---|---|
| `place_id`, `uri` | Syriaca place ID and URI | 100 % |
| `type` | Place type (settlement, church, monastery, diocese, region, river, …) | 100 % |
| `deprecated` | 1 if the record is deprecated (one record) | – |
| `headword_en`, `headword_syr` | Editorial headword in English and Syriac | 100 % / 27 % |
| `names_syr` | All Syriac names, `\|`-separated (`syr`, vocalised `syr-Syrj`, `syr-Syrn`) | 27 % |
| `names_ar` | All Arabic names | 23 % |
| `names_en` | English and romanised names (incl. Syriaca's own romanisation `en-x-srp1`) | 100 % |
| `names_other` | Other languages as `name@lang` (French, Greek, German, Latin) | 2 % |
| `abstract_en` | Short editorial description in English | 35 % (74 %) |
| `quotes_syr`, `quotes_ar`, `quotes_en` | Descriptions quoted from sources, per language | 7 % each (≈ 45 %) |
| `lat`, `lon` | Coordinate (preferred GPS location, otherwise the first) | 27 % (44 %) |
| `n_gps_locations` | Number of GPS locations on the record | – |
| `relative_location` | Text location, e.g. "five day journey eastward from Aleppo" | 0.1 % |
| `existence_from`, `existence_to` | Years the place existed as this type (editorial estimate) | 20 % (80 %) |
| `n_attestations`, `attestations` | Dated attestations of names in sources, as `start–end: description` | 14 % (40 %) |
| `wikipedia`, `dbpedia` | Wikipedia and DBpedia URLs | 25 % / 13 % |
| `pleiades_id` | Pleiades place ID(s) | 17 % (39 %) |
| `other_uris` | Other gazetteers and sites (csc.org.il, gazetteer.dainst.org, vici.org, …) | 8 % |
| `same_as_syriaca` | Other Syriaca IDs for the same place | 1 % |
| `sources` | Titles of the cited sources | 91 % |

## Which names belong together

`place_id` is the ground truth key. All names on the same row are names of the same place, so a Syriac name and an Arabic name match if they come from the same `place_id`.

| place_id | names_syr | names_ar |
|---|---|---|
| 88 | ܓܙܪܬܐ ܕܒܪ ܥܘܡܪ\|ܓܳܙܰܪܬܐ ܕܒܰܪ ܥܘܡܪ\|ܓܙܪܬܐ ܙܒܕܝܬܐ | جزيرة ابن عمر |

To build a matching task, split the table into a Syriac side and an Arabic side and keep `place_id` only for scoring:

```python
import csv
csv.field_size_limit(10**9)

with open("syriaca_places.tsv", encoding="utf-8") as f:
    places = [r for r in csv.DictReader(f, delimiter="\t") if r["deprecated"] == "0"]

syr_side = [{"id": r["place_id"], "names": r["names_syr"].split("|")} for r in places if r["names_syr"]]
ar_side  = [{"id": r["place_id"], "names": r["names_ar"].split("|")}  for r in places if r["names_ar"]]

ar_ids = {a["id"] for a in ar_side}
ground_truth = {s["id"] for s in syr_side if s["id"] in ar_ids}
print(len(syr_side), len(ar_side), len(ground_truth))   # 954 801 547
```

This gives 547 matched places, plus 407 Syriac-only and 254 Arabic-only places that have no match on the other side. A proposed pair (Syriac record, Arabic record) is correct if both have the same `place_id`. Never show `place_id` to the matching method.

## Coverage by data category

| Category | Fields |
|---|---|
| Name | `names_syr`, `names_ar`, `names_en`, `names_other` |
| Geography | `lat`/`lon`, `type`, `relative_location`; relations to broader places in the TEI (`listRelation`) |
| Time and source | `existence_from`/`_to`, `attestations`, `sources` |
| Text context | `abstract_en`, `quotes_syr`, `quotes_ar`, `quotes_en` |

## Avoiding leakage

- **All non-name attributes are shared.** Coordinates, type, existence dates and links belong to the one record that both names come from. Give them to one side only, or take them from another source (e.g. via `pleiades_id`).
- **The Syriac and Arabic quotes are often the same text.** Many come from Barsoum's *Scattered Pearls* in its Syriac and Arabic editions, i.e. translations of the same entry. They are fair as text context, but similar content across the two sides is partly a translation artefact.
- **The Arabic names often come from those same sources.** For example, Yāqūt's *Muʿjam al-buldān* is cited for Arabic attestations.

## Known issues

- **Coordinates are sparse.** Only 27 % of all places (44 % of matched places) have coordinates.
- **Not all types are toponyms in the narrow sense.** Churches, monasteries and dioceses are included; filter on `type` if needed.
- **One record is deprecated** (`deprecated = 1`).
- **Multiple Syriaca IDs for one place** occur for 31 places (`same_as_syriaca`).

## Rebuilding

`syriaca_places.tsv` was built from the TEI records with a small Python script (standard library `xml.etree.ElementTree`, not kept in this folder). To get the TEI records again:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/srophe/syriaca-data.git
cd syriaca-data && git sparse-checkout set data/places
# one TEI file per place in data/places/tei/<id>.xml
```

Each column comes from `TEI/text/body/listPlace/place`:

| Column | TEI source |
|---|---|
| `type` | `place/@type` |
| `names_*`, `headword_*` | `placeName` grouped by `@xml:lang`; headword = `@srophe:tags` contains `syriaca-headword` |
| `abstract_en` | `desc[@type="abstract"][@xml:lang="en"]` |
| `quotes_*` | `desc/quote`, grouped by the `desc/@xml:lang` |
| `lat`, `lon` | `location[@type="gps"]/geo`, `@subtype="preferred"` first |
| `relative_location` | `location[@type="relative"]` |
| `existence_from`, `existence_to` | `state[@type="existence"]/@from`, `@to` (or `@notBefore`/`@notAfter`) |
| `attestations` | `event[@type="attestation"]` with `@notBefore`/`@notAfter` and its `desc` |
| `wikipedia`, `pleiades_id`, `dbpedia`, `other_uris`, `same_as_syriaca` | `idno[@type="URI"]` |
| `sources` | `bibl/title` |
| `deprecated` | `idno[@type="deprecated"]` present |

Unused elements worth mining are `listRelation` (broader places, e.g. the diocese a monastery belongs to) and the `@source` links from each name and quote to the `bibl` that attests it.
