# Cross-matching datasets

This directory contains inputs and results for evaluating place matching across
Pleiades and Trismegistos. The `em.tsv` files are gold alignments: each row
connects a `pleiades_id` to a `trismegistos_id`.

## Greek Pleiades vs Latin Trismegistos

The Greek-to-Latin subset is a **cross-lingual diagnostic**: Pleiades records
are selected for Greek-script names, while Trismegistos records are selected
for Latin-script names. It is not a same-language comparison.

First create the partitioned combined Trismegistos table, then build the subset
from the repository root:

```powershell
python scripts\trismegistos\combine_trismegistos.py
python scripts\trismegistos\build_greek_latin_crosslingual.py
```

By default, the script reads:

- `final_datasets/Pleades_Trismegistos/pleiades.tsv`
- partitions in `final_datasets/Pleades_Trismegistos/trismegistos_texts_combined_parts/`
- `final_datasets/Pleades_Trismegistos/em.tsv`

`combine_trismegistos.py` writes 10,000 rows per TSV partition by default,
along with a `manifest.json` listing the partition files, row counts, and
columns. Change the partition size with `--rows-per-partition`; change the
partition directory with `--output-dir`.

The Greek–Latin builder calls `load_trismegistos_partitions.py` to validate and
reassemble the manifest-listed partitions into a temporary TSV. It then writes
the following files to
`final_datasets/Pleades_Trismegistos/pleiades_greek_trismegistos_latin/`:

| File | Contents |
|---|---|
| `pleiades.tsv` | Pleiades places with a non-blank `names_greek` value. All original Pleiades columns are retained. |
| `trismegistos.tsv` | Trismegistos places with a non-blank `names_latin` value, one row per place. Place attributes and aggregated text information are retained. |
| `em.tsv` | Gold links from the source EM table for which both place IDs occur in the filtered Pleiades and Trismegistos files. |

### Trismegistos text aggregation

The combined input has one row per place-text link, so a place can appear on
many rows. The script groups rows by `trismegistos_id` to keep the Trismegistos
entity file at one row per place, matching the granularity of the gold links.
For each text-related column (`tm_text_id`, `relation`, `title`, `material`,
`text_lang`, `year_from`, `year_to`, `keywords`, `snippet`, `edition_text`, and
`translation_en`), non-empty distinct values are joined with ` | ` in source
order. The aggregated `mentions_name` is `1` if any linked text has
`mentions_name` equal to `1`; otherwise it is `0`.

### Gold links and interpretation

The output `em.tsv` retains the source EM columns and rows only when the
Pleiades ID survived the Greek-name filter **and** the Trismegistos ID survived
the Latin-name filter. The script does not infer or create matches; it filters
the existing gold links. Since Trismegistos places without linked text are not
present in the combined input, they cannot appear in this subset.

On the current source data, the generated files contain 2,909 Pleiades places,
252 Trismegistos places, and 100 gold links. Re-running the scripts refreshes
these outputs from the input TSVs. The partition loader can also be run
directly:

```powershell
python scripts\trismegistos\load_trismegistos_partitions.py `
  final_datasets\Pleades_Trismegistos\trismegistos_texts_combined_parts `
  path\to\trismegistos_texts_combined.tsv
```

Optional arguments let you override the input files or output directory:

```powershell
python scripts\trismegistos\build_greek_latin_crosslingual.py `
  --pleiades path\to\pleiades.tsv `
  --trismegistos path\to\partition-directory `
  --em path\to\em.tsv `
  --output-dir path\to\output
```

`--trismegistos` may also point directly to an already combined TSV instead of
a partition directory.

## Language-pair interpretation

For primary same-language comparisons, the intended pairings are Greek vs
Greek, Latin vs Latin, and Romanized vs Romanized. Greek Pleiades vs Latin
Trismegistos should be treated as a cross-lingual diagnostic, not as one of
those same-language results.
