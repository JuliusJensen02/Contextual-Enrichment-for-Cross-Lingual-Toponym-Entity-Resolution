# DAMAST ↔ Benjamin of Tudela — testset11

Cross-lingual toponym matching: Arabic (`damast_315.tsv`, 447 rows) vs. Hebrew (`Tudela_257.tsv`, 306 rows). Ground truth in `em.tsv` (32 positive pairs). Tab-separated, UTF-8. Periods differ per source: DAMAST c. 1000, Tudela 1168.

Keep? column: ✅ keep (carry forward in the project) · ⚠️ borderline · ❌ drop (irrelevant). Some ✅ columns (ids, `matches`) are kept only for joining or enrichment and must still be hidden from the matcher — see the leakage note.

## `damast_315.tsv` — Arabic, from the DAMAST project (Dhimmis & Muslims, c. 1000)

| Column | Content | Keep? |
|---|---|---|
| `id` | Running number 1–447. | ✅ keep — join/link |
| `title` | Place name in Arabic. | ✅ keep — name |
| `title_source` | Constant: `DAMAST`. | ❌ drop — constant |
| `start` | Constant `1000`. | ✅ keep — time (compare against datasets dated outside this range) |
| `matches` | Wikidata/GeoNames refs (`wd:…;gn:…`). Only ~2%. | ✅ keep — enrichment where present (hide from matcher) |
| `types` | Constant `settlement`. | ✅ keep — constant, but useful across datasets |
| `variants` | Many variants in Arabic, Syriac, Greek and Latin script. | ✅ keep — Arabic; strip other scripts |
| `lat` / `lon` | Coordinates (~96%). | ⚠️ keep — not from source text; for comparison, hide from matcher |
| `description` | English note on the place/coordinates (e.g. "The modern city of Mosul"). | ❌ drop — not original text |
| `geowkt` / `geo_source` / `geo_id` | Empty. | ❌ drop — empty |

## `Tudela_257.tsv` — Hebrew, from the *Itinerary of Benjamin of Tudela* (1170s)

| Column | Content | Keep? |
|---|---|---|
| `id` | Mixed: `K…` Kima, `Q…` Wikidata, `GN…` GeoNames, `PL…` Pleiades, `U…`/`BJ…` local. | ✅ keep — join/link (hide from matcher) |
| `title` | Place name in Hebrew. | ✅ keep — name |
| `description` | Hebrew passage from the travelogue where the place is mentioned (~87%). | ✅ keep — text context (from source) |
| `title_source` | Edition: Asher (most) or Adler. | ✅ keep — source/edition provenance |
| `lat` / `lon` | Coordinates (~57%). | ⚠️ keep — not from source text; for comparison, hide from matcher |
| `start` | Constant `1168`. | ✅ keep — time (compare against datasets dated outside this range) |
| `geowkt` | Geometry as WKT `MULTIPOINT` (~38%). | ❌ drop — modern geometry |
| `geo_source` / `geo_id` | Empty. | ❌ drop — empty |
| `variants` | Variants in Hebrew, Latin and sometimes Arabic. | ✅ keep — Hebrew; strip Latin/Arabic |
| `matches` | Links to Wikipedia/Wikidata/Kima/VIAF/GeoNames/… (~89%). | ✅ keep — enrichment (hide from matcher) |

## `em.tsv` — ground truth

| Column | Content | Keep? |
|---|---|---|
| `id_1` / `title_1` | Record id and name in `damast_315.tsv`. | ✅ eval only — never a feature |
| `id_2` / `title_2` | Record id and name in `Tudela_257.tsv`. | ✅ eval only — never a feature |
| `judgement` | Always `true` (only positive pairs are listed). | ✅ eval only |

**Leakage note:** keys and resolved attributes must not be shown to a matcher — Tudela `id` (contains Kima/Wikidata/GeoNames/Pleiades ids) and `matches`, DAMAST `matches` (kept for joining and enrichment only). Coordinates (`lat`/`lon`) are modern georeferencing, not part of the source texts — kept for comparison/analysis but must not be a matcher feature (`geowkt` dropped as redundant). For `variants`, keep own-script spellings but strip cross-script ones. Note the asymmetry: only Tudela carries real own-language text (`description`); DAMAST's `description` is a modern English note, so text context exists on the Hebrew side only.
