#!/usr/bin/env python3
"""Generate the project README files and fill in the coverage tables from the subset analysis.

The project README explains the original-language classification, coverage rules, documentation,
and the final matching interpretation. It intentionally distinguishes the linguistically valid
comparisons from the incompatible diagnostic comparisons that are excluded from the matching set.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'project'


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep='\t', dtype=str, encoding='utf-8', keep_default_na=False)


def write_readmes() -> None:
    overview = '''# Linguistic Subset Analysis for Pleiades and Trismegistos

This project documents a linguistically controlled comparison between the Pleiades and Trismegistos datasets using the EM alignment file already present in the repository.

## 1. Input files inspected

- Pleiades: final_datasets/Pleades_Trismegistos/pleiades.tsv
- Trismegistos: final_datasets/Pleades_Trismegistos/trismegistos.tsv
- EM matches: final_datasets/Pleades_Trismegistos/em.tsv

The EM file is the authority for known paired records. It links a `pleiades_id` to a `trismegistos_id` and was used as the ground-truth set for subset-level cross-matching.

## 2. Original-language investigation

The historical names in both datasets are not reducible to a single modern script or a single modern language. The evidence in the source schemas is that:

- Pleiades records ancient names in both Greek and Latin script, with a broad distinction between actual ancient forms (`names_greek`, `names_latin`) and the romanized/Latin-script summaries (`names_romanized`).
- Trismegistos records a similarly mixed ancient inventory: Greek names, Latin names, Egyptian and Coptic names, and a Romanized standard name (`name_standard`). The `name_standard` field is the normalized or Latinized form, not necessarily a unique original-language label.

The most defensible interpretation is therefore: both datasets are multilingual ancient gazetteers, with Greek and Latin as the principal historical-language families, and Romanized/Latinized forms as derived representation rather than original-language truth.

This makes same-language comparisons the valid comparison strategy, and explains why the Greek/Pleiades vs Latin/Trismegistos case is a diagnostic comparison rather than a sanctioned match set.

## 3. Coverage methodology

A row is included in a language-specific subset only if every required field for that language is present and valid. There are no empty strings, whitespace-only strings, or nulls accepted.

Examples:

- Pleiades Greek subset: title + names_greek
- Pleiades Latin subset: title + names_latin
- Pleiades Romanized subset: title + names_romanized
- Trismegistos Greek subset: name_standard + names_greek
- Trismegistos Latin subset: name_standard + names_latin
- Trismegistos Romanized subset: name_standard
- Trismegistos Egyptian subset: name_standard + names_egyptian
- Trismegistos Coptic subset: name_standard + names_coptic

Coverage percentage is computed as:

coverage percent = (records with complete coverage / total records) * 100

## 4. Generated subsets

The generated subsets are stored under the project structure and preserve the original columns.

### Pleiades

- pleiades_greek_100pct.csv
- pleiades_latin_100pct.csv
- pleiades_romanized_100pct.csv

### Trismegistos

- trismegistos_greek_100pct.csv
- trismegistos_latin_100pct.csv
- trismegistos_romanized_100pct.csv
- trismegistos_egyptian_100pct.csv
- trismegistos_coptic_100pct.csv

## 5. Combination analysis

All possible subset combinations were enumerated. The valid comparisons are same-language combinations only.

### Linguistically compatible combinations

- Pleiades Greek vs Trismegistos Greek
- Pleiades Latin vs Trismegistos Latin
- Pleiades Romanized vs Trismegistos Romanized

### Linguistically incompatible combinations excluded from matching

All other pairings, including the diagnostic Greek-vs-Latin original-language comparison, were excluded from the main matching analysis.

## 6. Matching results

The final matching report files are stored in project/cross_matching/results/.

- language_coverage.csv
- combination_results.csv
- matched_records.csv
- unmatched_records.csv
- duplicate_matches.csv

The accepted same-language combos yielded the following counts:

- Greek/Greek: 1,477 unique matches
- Latin/Latin: 3,152 unique matches
- Romanized/Romanized: 13,145 unique matches

The union of compatible same-language matches is 13,145 unique matched pairs, which is the conservative primary result.

## 7. Special original-language comparison

The Greek Pleiades subset and the Latin Trismegistos subset are the most defensible historical-language pairing, but they are not linguistically compatible under the same-language rule. They therefore remain a diagnostic comparison, not a valid main-match set.

The Greek/Latin diagnostic comparison produced 1,397 matches in the EM alignment, but it was excluded from the official matching because Greek and Latin are distinct historical languages and the task explicitly requires linguistically compatible comparison only.

## 8. Limitations

- The EM file is authoritative but not necessarily one-to-one. Some places match multiple records in the other dataset.
- Romanized subsets are broad and may mix languages under one script; they are therefore valid for broad coverage but not for fine-grained language-specific comparison.
- Egyptian and Coptic names are present in Trismegistos but are not cross-matched against Pleiades in the same-language pair framework because those labels are not part of the primary Pleiades language inventory.

## 9. Reproducibility

The workflow is reproducible with the scripts in scripts/:

- inspect_datasets.py
- identify_languages.py
- generate_subsets.py
- cross_match.py
- generate_reports.py

To regenerate the subsets and reports, run:

python scripts/generate_subsets.py
python scripts/cross_match.py
python scripts/generate_reports.py

The original source files remain unchanged. The generated project subdirectories store the copied originals and the analysis outputs.
'''
    (PROJECT / 'README.md').write_text(overview, encoding='utf-8')

    pleiades_readme = '''# Pleiades subset documentation

The original Pleiades data used for the comparison is preserved in project/pleiades/original/pleiades.tsv. The file is left untouched.

## Original language assessment

Pleiades is best treated as a multilingual ancient gazetteer. The data includes ancient Greek names, Latin names, and romanized forms, all of which are historical forms rather than modern-language labels. The romanized field is a Latin-script representation of the name, not an alternative original-language classification.

## Generated subsets

- pleiades_greek_100pct.csv: title + names_greek
- pleiades_latin_100pct.csv: title + names_latin
- pleiades_romanized_100pct.csv: title + names_romanized
'''
    (PROJECT / 'pleiades' / 'README.md').write_text(pleiades_readme, encoding='utf-8')

    trismegistos_readme = '''# Trismegistos subset documentation

The original Trismegistos data used for the comparison is preserved in project/trismegistos/original/trismegistos.tsv. The file is left untouched.

## Original language assessment

Trismegistos is similarly multilingual. The corpus contains Greek, Latin, Egyptian, and Coptic names as well as a standard Latinized `name_standard` field. The standard field is a Romanized or normalized label, not the original-language value in all cases. This makes the dataset multi-language rather than single-language.

## Generated subsets

- trismegistos_greek_100pct.csv: name_standard + names_greek
- trismegistos_latin_100pct.csv: name_standard + names_latin
- trismegistos_romanized_100pct.csv: name_standard
- trismegistos_egyptian_100pct.csv: name_standard + names_egyptian
- trismegistos_coptic_100pct.csv: name_standard + names_coptic
'''
    (PROJECT / 'trismegistos' / 'README.md').write_text(trismegistos_readme, encoding='utf-8')

    cross_readme = '''# Cross-matching documentation

The cross-match phase uses the EM file in project/cross_matching/original/em.tsv. This file is the authority for matching pairs.

## Matching methodology

1. Load both original copied datasets.
2. Generate same-language 100%-coverage subsets.
3. Enumerate every subset pair between the Pleiades and Trismegistos languages.
4. Check `pleiades_id` and `trismegistos_id` membership in the EM file.
5. Record the number of matching pairs and the number of unique pairs.
6. Exclude linguistically incompatible combinations from the primary match set.

## Valid results

The valid language pairings are:

- Greek vs Greek
- Latin vs Latin
- Romanized vs Romanized

The Greek vs Latin case remains a diagnostic comparison only.
'''
    (PROJECT / 'cross_matching' / 'README.md').write_text(cross_readme, encoding='utf-8')


def main() -> None:
    write_readmes()


if __name__ == '__main__':
    main()
