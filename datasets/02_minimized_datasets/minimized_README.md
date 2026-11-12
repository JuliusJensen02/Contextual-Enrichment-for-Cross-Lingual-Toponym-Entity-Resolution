# Minimized datasets

These TSVs retain the source rows and order while keeping the requested fields.
When multiple source columns are combined into one output cell, their values
are joined with ` | `. Empty source values are omitted; other values are kept
as-is. Output files use UTF-8.

For the minimized MEHDIE files, multi-values carried over from the flattened
sources are normalized from `; ` to ` | ` in `name_variants`, `lat`, `lon`,
`country`, `types`, and `description`.

Regenerate the files from the repository root with:

```powershell
python scripts\minimize_datasets.py
```

| Output | Source | Field mappings |
|---|---|---|
| `Pleades_Trismegistos/pleiades.tsv` | `01_cleaned_datasets/Pleades_Trismegistos/pleiades.tsv` | `id` maps to `pleiades_id`; `name_variants` combines `names_by_language`, `names_romanized`, `names_greek`, and `names_latin`; `country` is empty because no country field is available; `begin_date` / `end_date` map to `year_from` / `year_to`; `types` maps to `place_types`. |
| `Pleades_Trismegistos/trismegistos.tsv` | `01_cleaned_datasets/Pleades_Trismegistos/trismegistos.tsv` | `id` maps to `trismegistos_id`; `title` maps to `name_standard`; `title_ipa` maps to `names_latin_ipa`; `name_variants` combines `name_standard` and available Greek, Latin, Egyptian, Coptic, and modern names (IPA fields are excluded); `country` combines `country`, `region`, `nomos_code`, and `provincia`; dates map directly; `types` maps to `status`; `text_snippets` maps directly. |
| `MEHDIE/yaqut.tsv` | `01_cleaned_datasets/MEHDIE/yaqut.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `MEHDIE/kima.tsv` | `01_cleaned_datasets/MEHDIE/kima.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `MEHDIE/thurayya.tsv` | `01_cleaned_datasets/MEHDIE/thurayya.tsv` | `country` combines `ccodes` and `relation`; dates, `name_variants`, `types`, and `description` map directly. |
| `Wikidata-zh-ru/wikidata_ru.tsv` | `00_original_datasets/Wikidata-zh-ru/wikidata_ru.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |
| `Wikidata-zh-ru/wikidata_zh.tsv` | `00_original_datasets/Wikidata-zh-ru/wikidata_zh.tsv` | `name_variants` combines `variants`, `replaces`, and `replaced_by`; `country` combines `country`, `admin_unit`, and `part_of`; wiki-specific fields map directly. |

`id` is the first column of every file: the source's record id, which the
ground truth files in `datasets/em/` refer to. It is there for linking and
scoring only and must not be shown to the LLM. `title`, `title_ipa`,
coordinates, and available descriptions map directly.
`title_ipa` is copied from the same-named source column when present; until
that column is added to a source, its minimized value is blank. Wiki-specific
fields include `wiki_title`, `capital`, `neighbours`, `population`,
`inception`, `dissolved`, `instance_of_label`, and `described_by`.
`details` is retained for Pleiades only. Fields that do not exist in a source
are not added to that source's output.
