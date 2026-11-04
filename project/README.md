# Linguistic Subset Analysis for Pleiades and Trismegistos

This project documents a linguistically controlled comparison between the Pleiades and Trismegistos datasets using the EM alignment file already present in the repository.

## Work completed

The requested analysis was carried through from source inspection to reproducible outputs:

1. Inspected the Pleiades, Trismegistos, and EM alignment tables and their relevant name and identifier fields.
2. Defined a strict complete-coverage rule for each language subset; every required name field must be non-empty, and the original source tables were left unchanged.
3. Preserved copies of the input tables and generated eight full-coverage subsets: three Pleiades subsets and five Trismegistos subsets.
4. Enumerated all 15 Pleiades–Trismegistos language-subset combinations, marking only Greek/Greek, Latin/Latin, and Romanized/Romanized as compatible for the primary analysis.
5. Used EM identifier pairs to generate matched, unmatched, duplicate, combination, and coverage reports, then generated dataset- and analysis-level README documentation.

The three compatible combinations have 1,477 Greek/Greek, 3,152 Latin/Latin, and 13,145 Romanized/Romanized unique matches individually. Their combination-level counts sum to 17,774 rows in the [matched-record report](cross_matching/results/matched_records.csv), which can repeat an identifier pair found in more than one language combination. Deduplicating that report on (`pleiades_id`, `trismegistos_id`) gives **13,145 unique pairs overall**. These are existing EM alignments selected by subset membership, not newly inferred matches.

The complete-coverage subset sizes were: Pleiades Greek 2,909, Latin 3,915, and Romanized 27,355; Trismegistos Greek 14,721, Latin 13,509, Romanized 64,507, Egyptian 1,969, and Coptic 659. Detailed percentages and all combination counts are in the CSV reports below.

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

The three combination-level counts sum to 17,774 rows in `matched_records.csv`. Since a pair may occur in multiple language combinations, deduplicating by `pleiades_id` and `trismegistos_id` yields 13,145 unique pairs overall. The Romanized/Romanized combination also has 13,145 unique matches on its own; its count happens to equal the deduplicated overall total.

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
