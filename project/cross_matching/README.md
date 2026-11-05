# Cross-matching documentation

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
