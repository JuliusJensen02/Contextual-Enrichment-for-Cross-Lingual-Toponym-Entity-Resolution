# Datasets

Datasets for cross-lingual toponym entity resolution. Each folder has its own README with columns, statistics and known issues.

| Folder | Languages | Period | Records | Ground truth | Key | Text context |
|---|---|---|---|---|---|---|
| [`MEHDIE/`](MEHDIE/README.md) | Hebrew ↔ Arabic | Medieval (c. 800–1250) | 5 testsets, 291–2,241 places per source | 137 verified pairs | `em.tsv`: `id_1` ↔ `id_2` | Medium (Yāqūt entries, Tudela passages) |
| [`Syriaca/`](Syriaca/README.md) | Syriac ↔ Arabic | Late antique – medieval (c. 400–1500) | 3,485 places | 547 places with names in both languages | `place_id` | Medium (source quotes, attestations) |
| [`Pleiades/`](Pleiades/README.md) | Latin/Greek ↔ Hebrew/Arabic | Ancient (c. 750 BCE – 650 CE) | 42,399 places | 4,497 links to Wikidata labels | `pleiades_id` | Low (short description) |
| [`Wikidata-he-ar/`](Wikidata-he-ar/README.md) | Hebrew ↔ Arabic | Modern (present day) | 34,079 places | One pair per item (one-to-one) | `qid` | Low (none in the file; Wikipedia via URLs) |
| [`HIPE-2022/`](HIPE-2022/README.md) | German, English, French, Finnish, Swedish | 18th–20th century (c. 1780–2000) | 35,107 place-name mentions in newspapers and commentaries (5,378 unique places) | 23,355 mentions linked to Wikidata | `NEL-LIT` (QID) | High (full documents) |

Periods are approximate, based on the dates in each source:

- **MEHDIE:** al-Thurayya c. 800–1000, Benjamin of Tudela 1168, Yāqūt c. 1225, DAMAST c. 1000.
- **Syriaca:** the middle half of places existed from c. 400 to c. 1500; dated name attestations run from 201 to 1883.
- **Pleiades:** the middle half of places fall between c. 330 BCE and 640 CE. Places that continue to the present are marked with the end year 2100.

## In short

- **MEHDIE.** The project's core benchmark (Sagi et al. 2025): historical Hebrew and Arabic gazetteers and texts (Kima, Yāqūt, al-Thurayya, Benjamin of Tudela, DAMAST). Small but real, with expert-verified matches. Only positive pairs are listed.
- **Syriaca.** The Syriac Gazetteer. Each record holds a place's Syriac and Arabic names, so the record itself is the match. A second Semitic language pair, historical and with dated attestations.
- **Pleiades.** Ancient places with Latin/Greek names, linked via Wikidata (P1584) to modern Hebrew/Arabic labels. Also contains Arabic names for 553 places and Hebrew names for 82.
- **Wikidata-he-ar.** Large, synthetic set of modern Hebrew–Arabic place labels, filtered to toponyms. Good for volume, but the names are well known and likely in LLM training data.
- **HIPE-2022.** Place names as they occur in running historical text (often with historical spelling and OCR errors), each mention linked to a Wikidata item. The names have to be extracted from the token files (see its README). Not Hebrew or Arabic, but the only set with full document context. The `letemps` subset has no links.

## Overlaps between datasets

| Link | How |
|---|---|
| Syriaca ↔ Pleiades | `pleiades_id` in `Syriaca/syriaca_places.tsv` (580 places) |
| Pleiades ↔ Wikidata-he-ar | `qid` in `Pleiades/pleiades_wikidata_links.tsv` |
| MEHDIE (Kima) ↔ Wikidata | Wikidata URLs in Kima's `matches` column |
| HIPE-2022 ↔ Wikidata-he-ar | QID in `NEL-LIT` |

These links can serve as extra ground truth across datasets. They also mean the same place can appear in several sets, which matters when you report results per dataset.

## Things to keep in mind across all sets

- **Ground truth key.** It must never be shown to the matching method: no IDs, URIs, Wikidata/Pleiades IDs or Wikipedia links.
- **Shared attributes.** Coordinates and other attributes that come from the same record or item on both sides can give away the match. See the "Avoiding leakage" section in each README.
- **Time.** Time is the weakest data category in every set; it is often one fixed value per source.
