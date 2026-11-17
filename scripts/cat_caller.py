import pandas as pd

PATHS = {
    "kima":         "datasets\minimzed datasets\minimized_mehdie_db_kima_flat.tsv",
    "thurayya":     "datasets\minimzed datasets\minimized_mehdie_db_thurayya_flat.tsv",
    "yaqut":        "datasets\minimzed datasets\minimized_mehdie_db_yaqut_flat.tsvv",
    "pleiades":     "datasets\minimzed datasets\minimized_pleiades.tsv",
    "trismegistos": "datasets\minimzed datasets\minimized_trismegistos.tsv",
    "wikidata_ru":  "datasets\minimzed datasets\minimized_wikidata_ru.tsv",
    "wikidata_zh":  "datasets\minimzed datasets\minimized_wikidata_zh.tsv",
}

_BASE = {
    "id":       ["id"],
    "names":    ["title_ipa", "name_variants"],
    "geo":      ["lat", "lon"],
    "relation": ["country"],
    "temporal": ["begin_date", "end_date"],
}
_WIKI = {
    "id":       ["id"],
    "names":    ["title_ipa", "name_variants", "wiki_title"],
    "geo":      ["lat", "lon"],
    "relation": ["country", "capital", "neighbors", "population"],
    "temporal": ["inception", "dissolved"],
    "type":     ["instance_of_label"],
    "desc":     ["description", "described_by"],
}

CATEGORIES = {
    "kima":         {**_BASE, "type": ["types"], "desc": ["description"]},
    "thurayya":     {**_BASE, "type": ["types"], "desc": ["description"]},
    "yaqut":        {**_BASE, "type": ["types"], "desc": ["description"]},
    "pleiades":     {**_BASE, "desc": ["details", "description"]},
    "trismegistos": {**_BASE, "type": ["types"], "desc": ["text_snippets"]},
    "wikidata_ru":  _WIKI,
    "wikidata_zh":  _WIKI,
}

DEFAULT_COLS = ["id", "title"]

def load(dataset, *categories):
    cols = DEFAULT_COLS + [c for cat in categories for c in CATEGORIES[dataset][cat]]
    cols = list(dict.fromkeys(cols))   # drop duplicates, keep order
    return pd.read_csv(PATHS[dataset], sep="\t", dtype=str,
                       keep_default_na=False, usecols=cols)

kima_cat_names_df = load("wikidata_ru", "names")
print(kima_cat_names_df)