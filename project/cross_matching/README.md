# Cross-matching datasets

This directory contains inputs and results for evaluating place matching across
Pleiades and Trismegistos. The `em.tsv` files are gold alignments: each row
connects a `pleiades_id` to a `trismegistos_id`.

## Greek Pleiades vs Latin Trismegistos

The Greek-to-Latin subset is a **cross-lingual diagnostic**: Pleiades records
are selected for Greek-script names, while Trismegistos records are selected
for Latin-script names. It is not a same-language comparison.

Build the subset directly from the source TSVs with one command:

```powershell
python scripts\trismegistos\build_crosslingual.py
```

The default is Greek Pleiades vs Latin Trismegistos. To build the reverse
direction:

```powershell
python scripts\trismegistos\build_crosslingual.py `
  --pleiades-language latin `
  --trismegistos-language greek
```

The single script reads `datasets/Pleades_Trismegistos/pleiades.tsv`,
`trismegistos.tsv`, `trismegistos_texts.tsv`, and `em.tsv`. It joins text rows
to Trismegistos places, aggregates text fields by place, filters each gazetteer
to places with the requested language name, replaces `title` with that name,
derives the IPA columns, and filters the gold links to the retained IDs. No
separate combine, partition load, title-swap, or phonetic-encoding step is
needed.

By default, results go to a direction-named folder such as
`datasets/Pleades_Trismegistos/pleiades_greek_trismegistos_latin/`:

| File | Contents |
|---|---|
| `pleiades.tsv` | Pleiades places with the selected language name. The other language-name column is omitted. |
| `trismegistos.tsv` | Trismegistos places with the selected language name, one row per place. The other language-name column is omitted; place attributes and aggregated text information are retained. |
| `em.tsv` | Gold links from the source EM table for which both place IDs occur in the filtered Pleiades and Trismegistos files. |

Pleiades gets a derived `title_ipa` column. Trismegistos gets derived IPA
columns for the selected name language, Egyptian, Coptic, and modern names.
These use the shared phonetics module; install `anyascii` from
`candidate_generation/requirements.txt` with `pip install anyascii`.
Arabic-script values also require Epitran, as described in
`scripts/phonetic_encoding.py`.

### Trismegistos text aggregation

The source has one row per place-text link, so a place can appear many times.
Rows are grouped by `trismegistos_id`; distinct values in text fields are
joined with ` | ` in source order. The aggregated `mentions_name` is `1` if any
linked text has `mentions_name` equal to `1`; otherwise it is `0`.

### Gold links and interpretation

The output `em.tsv` retains the source EM columns and rows only when both IDs
survive their selected-language filters. The script does not infer or create
matches; it filters the existing gold links. Since Trismegistos places without
linked text are not present in the text input, they cannot appear in this
subset.

The language choices are `greek` and `latin`. Optional arguments let you
override the source files and output directory:

```powershell
python scripts\trismegistos\build_crosslingual.py `
  --pleiades path\to\pleiades.tsv `
  --trismegistos path\to\trismegistos.tsv `
  --texts path\to\trismegistos_texts.tsv `
  --em path\to\em.tsv `
  --output-dir path\to\output
```

## Language-pair interpretation

For primary same-language comparisons, the intended pairings are Greek vs
Greek, Latin vs Latin, and Romanized vs Romanized. Greek Pleiades vs Latin
Trismegistos should be treated as a cross-lingual diagnostic, not as one of
those same-language results.
