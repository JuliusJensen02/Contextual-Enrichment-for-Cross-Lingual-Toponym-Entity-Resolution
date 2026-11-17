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

for name, p in PATHS.items():
    try:
        cols = pd.read_csv(p, sep="\t", nrows=0, encoding="utf-8-sig").columns.tolist()
        print(name, "->", cols)
    except Exception as e:
        print(name, "-> ERROR:", e)