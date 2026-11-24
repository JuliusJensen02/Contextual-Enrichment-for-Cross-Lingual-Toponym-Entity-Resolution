"""Entrypoints for running matching methods on prepared candidate pairs."""

import re
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path

from Methods.llm_integration.create_prompt import SYSTEM_PROMPT, create_prompt
from Methods.llm_integration.llm_calls import LLMClient


def match_with_llm(
    query,
    candidates,
    provider: str = "llama",
) -> int:
    """Ask an LLM to select one candidate, or return 0 when no candidate matches."""
    attributes = _infer_record_attributes(query, candidates)
    prompt = create_prompt(attributes, query, candidates)
    client = LLMClient(prompt, SYSTEM_PROMPT)

    if provider == "llama":
        response = client.call_llama()["choices"][0]["message"]["content"]
    elif provider == "openai":
        response = client.call_openai().output_text
    elif provider == "anthropic":
        response = client.call_anthropic().content[0].text
    else:
        raise ValueError("provider must be 'llama', 'openai', or 'anthropic'")

    found = re.search(r'"match"\s*:\s*(\d+)', response)
    return int(found.group(1)) if found else 0


def match_with_bi_encoder(classifier, query, candidate, threshold: float):
    """Run the bi-encoder classifier for one query/candidate pair."""
    # Load the trained XGBoost classifier before this method is called,
    # for example with load_classifier("path/to/gradientboost-model.json").
    from Methods.bi_encoder.bi_encoder import is_match

    return is_match(
        classifier,
        _record_to_bi_encoder_entity(query),
        _record_to_bi_encoder_entity(candidate),
        threshold,
    )


def match_with_deeper(classifier, query, candidate, threshold: float):
    """Run the DeepER classifier for one query/candidate pair."""
    from Methods.deepER.deeper import is_match

    return is_match(classifier, query, candidate, threshold)


def load_ditto_model(
    checkpoint_path: str,
    task: str,
    lm: str = "distilbert",
    use_gpu: bool = False,
):
    """Load a Ditto checkpoint trained by Methods/ditto/train_ditto.py."""
    # This is the integration point for a trained Ditto checkpoint:
    # checkpoint_path/task/model.pt, created by the training script.
    ditto_root = Path(__file__).resolve().parents[1] / "Methods" / "ditto"
    if str(ditto_root) not in sys.path:
        sys.path.insert(0, str(ditto_root))

    import torch
    from ditto_light.ditto import DittoModel  # pyright: ignore[reportMissingImports]

    checkpoint = ditto_root / checkpoint_path / task / "model.pt"
    if not checkpoint.exists():
        raise FileNotFoundError(f"Ditto checkpoint not found: {checkpoint}")

    device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
    model = DittoModel(device=device, lm=lm)
    saved_state = torch.load(checkpoint, map_location=device)
    model.load_state_dict(saved_state["model"])
    model = model.to(device)
    model.eval()
    return model


def match_with_ditto(
    model,
    query,
    candidates,
    lm: str = "distilbert",
    max_len: int = 256,
    threshold: float = 0.5,
    fp16: bool = False,
) -> list[dict]:
    """Score query/candidate pairs with a loaded Ditto model."""
    ditto_root = Path(__file__).resolve().parents[1] / "Methods" / "ditto"
    if str(ditto_root) not in sys.path:
        sys.path.insert(0, str(ditto_root))

    from matcher import to_str  # pyright: ignore[reportMissingImports]
    from torch.utils import data
    from ditto_light.dataset import DittoDataset  # pyright: ignore[reportMissingImports]
    import torch

    sentence_pairs = [
        to_str(
            _record_to_ditto_entity(query),
            _record_to_ditto_entity(candidate),
        )
        for candidate in candidates
    ]
    dataset = DittoDataset(sentence_pairs, max_len=max_len, lm=lm)
    iterator = data.DataLoader(
        dataset=dataset,
        batch_size=len(dataset),
        shuffle=False,
        num_workers=0,
        collate_fn=DittoDataset.pad,
    )

    probabilities = []
    with torch.no_grad():
        for batch in iterator:
            x, _ = batch
            with torch.autocast(
                device_type=model.device,
                dtype=torch.float16,
                enabled=fp16,
            ):
                logits = model(x)
            probabilities.extend(logits.softmax(dim=1)[:, 1].cpu().numpy().tolist())

    return [
        {"candidate": candidate.id, "match": probability >= threshold, "probability": probability}
        for candidate, probability in zip(candidates, probabilities)
    ]


def call_matching_methods(
    pairs,
    methods: tuple[str, ...] = ("llm", "bi_encoder"),
    *,
    classifier=None,
    deeper_classifier=None,
    ditto_model=None,
    bi_encoder_threshold: float = 0.5,
    deeper_threshold: float = 0.5,
    ditto_threshold: float = 0.5,
    llm_provider: str = "llama",
    ditto_lm: str = "distilbert",
    ditto_max_len: int = 256,
) -> dict[str, list]:
    """Call each requested matching method for every prepared pair."""
    results = {method: [] for method in methods}

    for pair in pairs:
        if "llm" in methods:
            results["llm"].append(
                match_with_llm(
                    query=pair.query,
                    candidates=pair.candidates,
                    provider=llm_provider,
                )
            )

        if "bi_encoder" in methods:
            if classifier is None:
                raise ValueError("classifier is required when using the bi_encoder method")
            results["bi_encoder"].append(
                [
                    match_with_bi_encoder(
                        classifier,
                        pair.query,
                        candidate,
                        bi_encoder_threshold,
                    )
                    for candidate in pair.candidates
                ]
            )

        if "deeper" in methods:
            if deeper_classifier is None:
                raise ValueError("deeper_classifier is required when using the deeper method")
            from Methods.deepER.deeper import get_default_extractor

            get_default_extractor().prepare_pairs(pairs)
            results["deeper"].append(
                [
                    match_with_deeper(
                        deeper_classifier,
                        pair.query,
                        candidate,
                        deeper_threshold,
                    )
                    | {"candidate": candidate.id}
                    for candidate in pair.candidates
                ]
            )

        if "ditto" in methods:
            if ditto_model is None:
                raise ValueError("ditto_model is required when using the ditto method")
            results["ditto"].append(
                match_with_ditto(
                    ditto_model,
                    pair.query,
                    pair.candidates,
                    lm=ditto_lm,
                    max_len=ditto_max_len,
                    threshold=ditto_threshold,
                )
            )

    return results


def _infer_record_attributes(query, candidates) -> list[str]:
    """Infer loaded fields from the filtered project records."""
    records = [query, *candidates]
    attributes = []

    for record in records:
        if is_dataclass(record):
            for field in fields(record):
                if field.name not in {"dataset", "id"} and getattr(record, field.name, "") not in (None, ""):
                    if field.name not in attributes:
                        attributes.append(field.name)
        else:
            for name, value in vars(record).items():
                if name not in {"dataset", "id"} and value not in (None, "") and name not in attributes:
                    attributes.append(name)

    return attributes


def _record_to_ditto_entity(record) -> dict[str, str]:
    """Serialize a project Record as Ditto attribute/value fields."""
    if isinstance(record, dict):
        values = record
    elif is_dataclass(record):
        values = {
            field.name: getattr(record, field.name)
            for field in fields(record)
            if field.name not in {"dataset", "id"}
        }
    else:
        values = vars(record)

    return {
        name: str(value)
        for name, value in values.items()
        if name not in {"dataset", "id"} and value not in (None, "")
    }


def _record_to_bi_encoder_entity(record) -> dict:
    lat, lon = _coordinates(record)
    start, end = _temporal_range(record)
    entity = {
        "id": record.id,
        "name": record.title,
        "name_variants": record.name_variants,
        "ipa": getattr(record, "title_ipa", ""),
        "relational_geography": getattr(record, "country", ""),
        "classification": getattr(record, "types", "")
        or getattr(record, "instance_of_label", ""),
        "description": getattr(record, "description", "")
        or getattr(record, "details", "")
        or getattr(record, "text_snippets", ""),
    }
    if lat is not None and lon is not None:
        entity["coordinates"] = {"lat": lat, "lon": lon}
    if start is not None and end is not None:
        entity["temporal"] = {"start": start, "end": end}
    return entity


def _coordinates(record) -> tuple[float | None, float | None]:
    try:
        lat = float(record.lat)
        lon = float(record.lon)
        return lat, lon
    except (AttributeError, TypeError, ValueError):
        return None, None


def _temporal_range(record) -> tuple[float | None, float | None]:
    for start_field, end_field in (("begin_date", "end_date"), ("inception", "dissolved")):
        try:
            start = float(getattr(record, start_field))
            end = float(getattr(record, end_field))
            return start, end
        except (AttributeError, TypeError, ValueError):
            continue
    return None, None
