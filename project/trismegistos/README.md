# Trismegistos subset documentation

The original Trismegistos data used for the comparison is preserved in project/trismegistos/original/trismegistos.tsv. The file is left untouched.

## Original language assessment

Trismegistos is similarly multilingual. The corpus contains Greek, Latin, Egyptian, and Coptic names as well as a standard Latinized `name_standard` field. The standard field is a Romanized or normalized label, not the original-language value in all cases. This makes the dataset multi-language rather than single-language.

## Generated subsets

- trismegistos_greek_100pct.csv: name_standard + names_greek
- trismegistos_latin_100pct.csv: name_standard + names_latin
- trismegistos_romanized_100pct.csv: name_standard
- trismegistos_egyptian_100pct.csv: name_standard + names_egyptian
- trismegistos_coptic_100pct.csv: name_standard + names_coptic
