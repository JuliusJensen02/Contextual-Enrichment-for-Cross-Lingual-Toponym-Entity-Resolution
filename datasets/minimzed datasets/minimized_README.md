# Minimized datasets

These TSVs retain the source rows and order while keeping the requested fields.
When multiple source columns are combined into one output cell, their values
are joined with ` | `. Empty source values are omitted; other values are kept
as-is. Output files use UTF-8.

Regenerate the files from the repository root with:

```powershell
python scripts\minimize_datasets.py
```

| Output | Source | Field mappings |
|---|---|---|
| `minimized_pleiades.tsv` | `Pleades_Trismegistos/pleiades_greek_trismegistos_latin/pleiades.tsv` | `name_variants` combines `names_by_language`, `names_romanized`, `names_greek`, and `names_latin`; `country` is empty because no country field is available; `begin_date` / `end_date` map to `year_from` / `year_to`; `types` maps to `place_types`. |
| `minimized_trismegistos.tsv` | `Pleades_Trismegistos/pleiades_greek_trismegistos_latin/trismegistos.tsv` | `title` maps to `name_standard`; `name_variants` combines `name_standard` and available Greek, Latin, Egyptian, Coptic, and modern names and their IPA forms; `country` combines `country`, `region`, `nomos_code`, and `provincia`; dates map directly; `types` maps to `status`; `text_snippets` maps directly. This source currently has no `title_ipa` column, so the minimized `title_ipa` values are blank. |
| `minimized_mehdie_db_yaqut_flat.tsv` | `MEHDIE/flattened/mehdie_db_yaqut_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_mehdie_db_kima_flat.tsv` | `MEHDIE/flattened/mehdie_db_kima_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_mehdie_db_thurayya_flat.tsv` | `MEHDIE/flattened/mehdie_db_thurayya_flat.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `minimized_wikidata_ru.tsv` | `Wikidata-zh-ru/wikidata_ru.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |
| `minimized_wikidata_zh.tsv` | `Wikidata-zh-ru/wikidata_zh.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |

`title`, `title_ipa`, coordinates, and available descriptions map directly.
`title_ipa` is copied from the same-named source column when present; until
that column is added to a source, its minimized value is blank. Wiki-specific
fields include `wiki_title`, `capital`, `neighbours`, `population`,
`inception`, `dissolved`, `instance_of_label`, and `described_by`.
`details` is retained for Pleiades only. Fields that do not exist in a source
are not added to that source's output.
