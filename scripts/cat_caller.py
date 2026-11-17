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
    "names":            ["title_ipa", "name_variants"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country"],
    "temporal":         ["begin_date", "end_date"],
    "classification":   ["types"],
}
_WIKI = {
    "names":            ["title_ipa", "name_variants", "wiki_title"],
    "absolute":         ["lat", "lon"],
    "relation":         ["country", "capital", "neighbours", "population"],
    "temporal":         ["inception", "dissolved"],
    "classification":   ["instance_of_label"],
    "desc":             ["description", "described_by"],
}

CATEGORIES = {
    "kima":         {**_BASE, "desc": ["description"]},
    "thurayya":     {**_BASE, "desc": ["description"]},
    "yaqut":        {**_BASE, "desc": ["description"]},
    "pleiades":     {**_BASE, "desc": ["details", "description"]},
    "trismegistos": {**_BASE, "desc": ["text_snippets"]},
    "wikidata_ru":  _WIKI,
    "wikidata_zh":  _WIKI,
}
DEFAULT_COLS = ["id", "title"]

def load(dataset, *categories):
    cols = DEFAULT_COLS + [c for cat in categories for c in CATEGORIES[dataset][cat]]
    cols = list(dict.fromkeys(cols))
    df = pd.read_csv(PATHS[dataset], sep="\t", dtype=str,
                     keep_default_na=False, usecols=cols, encoding="utf-8-sig")

    if "desc" in categories:
        dcols = CATEGORIES[dataset]["desc"]
        desc = df[dcols[0]]
        for c in dcols[1:]:
            desc = (desc + " " + df[c]).str.strip()
        df = df.drop(columns=dcols)
        df["desc"] = desc
    return df

CATS = ["names", "absolute", "relation", "temporal", "classification", "desc"]

data = {ds: {cat: load(ds, cat) for cat in CATS} for ds in PATHS}

kima_experiment1 = pd.concat([data["kima"]["names"],data["kima"]["absolute"]])
