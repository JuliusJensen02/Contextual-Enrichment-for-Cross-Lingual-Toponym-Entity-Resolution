




import json
from types import SimpleNamespace

SYSTEM_PROMPT = """
You are an expert in entity resolution and your task is to identify if the records refer to the same entity or not. 
You will receive one query record describing a historical place (toponym) and a numbered list of candidate records from another gazetteer.
Names may be written in different languages and scripts.
"""


# Order of attributes determine order of json values. Kan ændres når der er lidt mere struktur om attribute_categories i koden.
def create_prompt(attributes: list, record, candidates) -> str:
    query = {}
    for attribute in attributes:
        query[attribute] = getattr(record, attribute, None)

    candidate_list = []
    for number, candidate in enumerate(candidates, start=1):
        candidate_json = {"candidate": number}
        for attribute in attributes:
            candidate_json[attribute] = getattr(candidate, attribute, None)
        candidate_list.append(candidate_json)

    query_text = json.dumps(query, ensure_ascii=False, indent=2)
    candidates_text = json.dumps(candidate_list, ensure_ascii=False, indent=2)

    prompt = f"""Query record:
{query_text}

Candidate records:
{candidates_text}

Which candidate refers to the same place as the query record? At most one candidate matches. If none of them refer to the same place, answer 0. A null value means the attribute is unknown.
Return ONLY strictly JSON (no markdown, no extra text) in the form: {{"match": <candidate number or 0>}}"""

    return prompt


if __name__ == "__main__":
    attributes = ["name", "name_variants", "transliteration", "lat", "lon", "feature_type"]

    record = SimpleNamespace(
        name="القدس",
        name_variants=("بيت المقدس",),
        transliteration=("al-Quds", "Bayt al-Maqdis"),
        lat=31.778,
        lon=35.235,
        feature_type="city",
    )

    candidates = [
        SimpleNamespace(
            name="ירושלים",
            name_variants=("ירושלם",),
            transliteration=("Yerushalayim", "Yerushalem"),
            lat=31.7767,
            lon=35.2345,
            feature_type="settlement",
        ),
        SimpleNamespace(
            name="קודס",
            name_variants=(),
            transliteration=("Qods",),
            lat=None,
            lon=None,
            feature_type=None,
        ),
        SimpleNamespace(
            name="בית לחם",
            name_variants=(),
            transliteration=("Beit Lehem",),
            lat=31.7054,
            lon=35.2024,
            feature_type="settlement",
        ),
    ]

    print(SYSTEM_PROMPT)
    print(create_prompt(attributes, record, candidates))

