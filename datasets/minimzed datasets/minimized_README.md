# Minimized datasets

These TSVs retain the source rows and order while keeping the requested fields.
When multiple source columns are combined into one output cell, their values
are joined with ` | `. Empty source values are omitted; other values are kept
as-is. Output files use UTF-8.

| Output | Source | Field mappings |
|---|---|---|
| `minimized_pleiades.tsv` | `Pleades_Trismegistos/pleiades.tsv` | `name_variants` combines `names_by_language`, `names_romanized`, `names_greek`, and `names_latin`; `country` is empty because no country field is available; `begin_date` / `end_date` map to `year_from` / `year_to`; `types` maps to `place_types`. |
| `minimized_trismegistos.tsv` | `Pleades_Trismegistos/trismegistos.tsv` | `title` maps to `name_standard`; `name_variants` combines `name_standard`, Greek, Latin, Egyptian, Coptic, and modern names; `country` combines `country`, `region`, `nomos_code`, and `provincia`; dates map directly; `types` maps to `status`; `text_snippets` maps directly. |
| `minimized_mehdie_db_yaqut_flat.tsv` | `MEHDIE/flattened/mehdie_db_yaqut_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_mehdie_db_kima_flat.tsv` | `MEHDIE/flattened/mehdie_db_kima_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_mehdie_db_thurayya_flat.tsv` | `MEHDIE/flattened/mehdie_db_thurayya_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_wikidata_ru.tsv` | `Wikidata-zh-ru/wikidata_ru.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |
| `minimized_wikidata_zh.tsv` | `Wikidata-zh-ru/wikidata_zh.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |

`title`, coordinates, and available descriptions map directly. Wiki-specific
fields include `wiki_title`, `capital`, `neighbours`, `population`,
`inception`, `dissolved`, `instance_of_label`, and `described_by`.
`details` is retained for Pleiades only. Fields that do not exist in a source
are not added to that source's output.
