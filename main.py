"""The entity resolution pipeline: candidates -> prompt -> LLM -> evaluation.

Change the settings below, then run:  python main.py
"""
import random
import re
import sys

from data_loader import CATEGORIES, TestSetLoader, TestSetName
from llm_integration.create_prompt import SYSTEM_PROMPT, create_prompt

# ------------------------------------------------------------------ settings
TEST_SET = TestSetName.MEHDIE
USED_CATEGORIES = ["names", "physical_geography"]   # see CATEGORIES in data_loader/record.py
LLM = "llama"                                       # "llama", "openai" or "anthropic"
MAX_CANDIDATES = 10                                 # candidates shown per query record, best first
RECORDS_PER_PAIR = 20                               # query records per dataset pair; None = all
SEED = 13
DRY_RUN = True                                      # True = only print the prompts, no LLM calls


def main():
    attributes = [attribute for category in USED_CATEGORIES for attribute in CATEGORIES[category]]
    results = []  # (predicted target id or None, true target ids) per query record

    for candidate_set in TestSetLoader().load_candidates(TEST_SET):
        for record, candidates in pick_query_records(candidate_set):
            candidates = candidates[:MAX_CANDIDATES]
            prompt = create_prompt(attributes, record, candidates)
            if DRY_RUN:
                print(prompt, "\n")
                continue

            number = ask_llm(prompt) if candidates else 0
            predicted = candidates[number - 1].id if 0 < number <= len(candidates) else None
            true_matches = [target for source, target in candidate_set.links if source == record.id]
            results.append((predicted, true_matches))

    if not DRY_RUN:
        evaluate(results)


def pick_query_records(candidate_set):
    """RECORDS_PER_PAIR random (record, candidates) pairs, or all of them."""
    queries = list(candidate_set)
    if RECORDS_PER_PAIR is None:
        return queries
    return random.Random(SEED).sample(queries, min(RECORDS_PER_PAIR, len(queries)))


def ask_llm(prompt: str) -> int:
    """The number of the candidate the LLM picks; 0 if it picks none."""
    from llm_integration.llm_calls import LLMClient  # only needed when the LLM is called

    client = LLMClient(prompt, SYSTEM_PROMPT)
    if LLM == "llama":
        answer = client.call_llama()["choices"][0]["message"]["content"]
    elif LLM == "openai":
        answer = client.call_openai().output_text
    else:
        answer = client.call_anthropic().content[0].text

    found = re.search(r'"match"\s*:\s*(\d+)', answer)  # the answer looks like {"match": 2}
    return int(found.group(1)) if found else 0


def evaluate(results):
    correct = sum(predicted in true_matches for predicted, true_matches in results)
    predicted = sum(predicted is not None for predicted, _ in results)
    true = sum(len(true_matches) for _, true_matches in results)

    precision = correct / predicted if predicted else 0
    recall = correct / true if true else 0
    f1 = 2 * precision * recall / (precision + recall) if correct else 0
    print(f"{len(results)} query records, {true} true matches, {predicted} predicted, {correct} correct")
    print(f"precision {precision:.3f}   recall {recall:.3f}   F1 {f1:.3f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # the records are in many scripts
    main()
