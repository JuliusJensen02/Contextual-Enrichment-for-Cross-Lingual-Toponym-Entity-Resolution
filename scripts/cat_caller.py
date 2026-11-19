import pandas as pd

PATHS = {
    "kima":         "datasets/minimzed datasets/minimized_mehdie_db_kima_flat.tsv",
    "thurayya":     "datasets/minimzed datasets/minimized_mehdie_db_thurayya_flat.tsv",
    "yaqut":        "datasets/minimzed datasets/minimized_mehdie_db_yaqut_flat.tsv",
    "pleiades":     "datasets/minimzed datasets/minimized_pleiades.tsv",
    "trismegistos": "datasets/minimzed datasets/minimized_trismegistos.tsv",
    "wikidata_ru":  "datasets/minimzed datasets/minimized_wikidata_ru.tsv",
    "wikidata_zh":  "datasets/minimzed datasets/minimized_wikidata_zh.tsv",
}

_BASE = {
    "name_variants":    ["title_ipa", "name_variants"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country"],
    "temporal":         ["begin_date", "end_date"],
    "classification":   ["types"],
}
_WIKI = {
    "name_variants":    ["title_ipa", "name_variants", "wiki_title"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country", "capital", "neighbours", "population"],
    "temporal":         ["inception", "dissolved"],
    "classification":   ["instance_of_label"],
    "description":      ["description", "described_by"],
}

CATEGORIES = {
    "kima":         {**_BASE, "description": ["description"]},
    "thurayya":     {**_BASE, "description": ["description"]},
    "yaqut":        {**_BASE, "description": ["description"]},
    "pleiades":     {**_BASE, "description": ["details", "description"]},
    "trismegistos": {**_BASE, "description": ["text_snippets"]},
    "wikidata_ru":  _WIKI,
    "wikidata_zh":  _WIKI,
}
DEFAULT_COLS = ["id", "title"]

def load(dataset, *categories):
    cols = DEFAULT_COLS + [c for cat in categories for c in CATEGORIES[dataset][cat]]
    cols = list(dict.fromkeys(cols))
    df = pd.read_csv(PATHS[dataset], sep="\t", dtype=str,
                     keep_default_na=False, usecols=cols, encoding="utf-8-sig")

    if "description" in categories:
        dcols = CATEGORIES[dataset]["description"]
        description = df[dcols[0]]
        for c in dcols[1:]:
            description = (description + " " + df[c]).str.strip()
        df = df.drop(columns=dcols)
        df["description"] = description
    return df

CATS = ["name_variants", "absolute", "relation", "temporal", "classification", "description"]

data = {ds: {cat: load(ds, cat) for cat in CATS} for ds in PATHS}

kima_experiment1 = data["kima"]["description"]

