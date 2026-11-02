# Yāqūt (Andalus/Maghreb) ↔ Kima — testset10

Cross-lingual toponym matching: Arabic (`Yaqut_306.tsv`, 484 rows) vs. Hebrew (`Kima_303.tsv`, 559 rows). Ground truth in `em.tsv` (33 positive pairs). Tab-separated, UTF-8.

Keep? column: ✅ keep (carry forward in the project) · ⚠️ borderline · ❌ drop (irrelevant). Some ✅ columns (ids, URIs, `matches`) are kept only for joining or enrichment and must still be hidden from the matcher — see the leakage note.

## `Yaqut_306.tsv` — Arabic, from Yāqūt al-Ḥamawī's *Muʿjam al-buldān* (13th c.)

| Column | Content | Keep? |
|---|---|---|
| `id` | Internal entry id (`dig…`). | ✅ keep — join/link |
| `title` | Place name in Arabic. | ✅ keep — name |
| `title_source` | Source/author, constant: `ياقوت الحموي الرومي` (Yāqūt al-Ḥamawī). | ❌ drop — constant |
| `start` / `end` | Time span of the **source**, constant `632` / `1250`. | ✅ keep — time (compare against datasets dated outside this range) |
| `matches` | External IDs. Empty in this set. | ❌ drop — empty |
| `variants` | Arabic name variants. Rarely filled (~1%). | ✅ keep — specific spellings may match another text |
| `types` | Place type in Arabic (`مدينة` city, `حصن` fort, `قرية` village, …). Taken from the entry text (verbatim in 98%). | ✅ keep — geography, from source |
| `parent_name` | Historical region in Arabic (`الأندلس`, `المغرب`, `إفريقية`, …). Taken from the entry text (97%). | ✅ keep — geography, from source |
| `lat` / `lon` | Coordinates. Modern georeferencing (not from Yāqūt), ~47%. | ⚠️ keep — not from source text; for comparison, hide from matcher |
| `description` | Full Arabic dictionary entry (~99%). | ✅ keep — text context |
| `varified` (sic) | Undocumented georeferencing confidence, 1–4; filled only when coordinates exist. | ❌ drop — georeferencing metadata |

## `Kima_303.tsv` — Hebrew, from the Kima gazetteer (data.geo-kima.org)

| Column | Content | Keep? |
|---|---|---|
| `id` | Kima place id. | ✅ keep — join/link (hide from matcher) |
| `title` | Place name in Hebrew. | ✅ keep — name |
| `title_source` | Constant: `KimaGazetteer`. | ❌ drop — constant |
| `start` | Constant `2000` — placeholder, not a historical date. | ❌ drop — placeholder |
| `title_uri` | `http://data.geo-kima.org/Place/<id>`. | ✅ keep — enrichment source (hide from matcher) |
| `ccodes` | Modern country code (ES, MA, DZ, TN, …). | ⚠️ modern, not from a text — keep only as a coarse region hint |
| `matches` | Wikidata/GeoNames URLs. 100% filled. | ✅ keep — enrichment, esp. for Kima (hide from matcher) |
| `variants` | Name variants, Hebrew and Latin script. | ✅ keep — Hebrew; strip Latin script |
| `types` | Place type in English. Rarely filled (~11%). | ⚠️ too sparse |
| `aat_types` | Getty AAT code. Rarely filled. | ❌ drop — sparse metadata |
| `parent_name` | Modern country/region in English. | ⚠️ modern, not from a text |
| `lat` / `lon` | Coordinates. 100% filled. | ⚠️ keep — not from source text; for comparison, hide from matcher |
| `description` | Short description. Practically empty (~2%), not original text. | ❌ drop — empty / not original |

## `em.tsv` — ground truth

| Column | Content | Keep? |
|---|---|---|
| `id_1` / `title_1` | Record id and name in `Yaqut_306.tsv`. | ✅ eval only — never a feature |
| `id_2` / `title_2` | Record id and name in `Kima_303.tsv`. | ✅ eval only — never a feature |
| `judgement` | Always `true` (only positive pairs are listed). | ✅ eval only |

**Leakage note:** keys and resolved attributes must not be shown to a matcher — Kima `id`/`title_uri`/`matches` (kept for joining and enrichment only). Coordinates (`lat`/`lon`, plus Yāqūt `varified`) are modern georeferencing, not part of the source texts — kept for comparison/analysis but must not be a matcher feature. For `variants`, keep own-script spellings but strip cross-script (Latin) ones.
