import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_loader import DatasetName
from experiments.data_preparation import Pair
from experiments.matching import (
    _record_to_bi_encoder_entity,
    _record_to_ditto_entity,
    call_matching_methods,
    load_ditto_model,
    match_with_bi_encoder,
    match_with_ditto,
    match_with_llm,
)


def record(record_id, title="Test place", lat="", lon="", country=""):
    return SimpleNamespace(
        dataset=DatasetName.KIMA,
        id=record_id,
        title=title,
        title_ipa="",
        name_variants="",
        lat=lat,
        lon=lon,
        country=country,
        begin_date="",
        end_date="",
        inception="",
        dissolved="",
        types="",
        instance_of_label="",
        description="",
        details="",
        text_snippets="",
    )


@pytest.fixture
def pair():
    return Pair(
        query=record("k1", "Cairo", "30.0444", "31.2357", "Egypt"),
        candidates=[
            record("y1", "Al-Qahira", "30.0444", "31.2357", "Egypt"),
            record("y2", "Alexandria", "31.2001", "29.9187", "Egypt"),
        ],
    )


@pytest.mark.parametrize(
    ("provider", "client_method"),
    [
        ("llama", "call_llama"),
        ("openai", "call_openai"),
        ("anthropic", "call_anthropic"),
    ],
)
def test_match_with_llm_supports_each_provider(monkeypatch, pair, provider, client_method):
    class FakeClient:
        def __init__(self, prompt, instructions):
            self.prompt = prompt
            self.instructions = instructions

        def call_llama(self):
            return {"choices": [{"message": {"content": '{"match": 2}'}}]}

        def call_openai(self):
            return SimpleNamespace(output_text='{"match": 2}')

        def call_anthropic(self):
            return SimpleNamespace(content=[SimpleNamespace(text='{"match": 2}')])

    monkeypatch.setattr("experiments.matching.LLMClient", FakeClient)

    assert match_with_llm(
        pair.query,
        pair.candidates,
        provider,
    ) == 2
    assert provider in {"llama", "openai", "anthropic"}


def test_match_with_llm_returns_zero_for_unparseable_response(monkeypatch, pair):
    class FakeClient:
        def __init__(self, prompt, instructions):
            pass

        def call_llama(self):
            return {"choices": [{"message": {"content": "No match"}}]}

    monkeypatch.setattr("experiments.matching.LLMClient", FakeClient)

    assert match_with_llm(
        pair.query,
        pair.candidates,
    ) == 0


def test_match_with_llm_rejects_unknown_provider(pair):
    with pytest.raises(ValueError, match="llama.*openai.*anthropic"):
        match_with_llm(pair.query, pair.candidates, "unknown")


def test_record_conversion_includes_coordinates_and_temporal_fields():
    query = record("k1", lat="30.0444", lon="31.2357", country="Egypt")
    query.begin_date = "641"
    query.end_date = "1798"

    entity = _record_to_bi_encoder_entity(query)

    assert entity["id"] == "k1"
    assert entity["name"] == "Test place"
    assert entity["coordinates"] == {"lat": 30.0444, "lon": 31.2357}
    assert entity["relational_geography"] == "Egypt"
    assert entity["temporal"] == {"start": 641.0, "end": 1798.0}


def test_record_conversion_handles_missing_coordinates():
    entity = _record_to_bi_encoder_entity(record("k1"))

    assert "coordinates" not in entity
    assert "temporal" not in entity


def test_match_with_bi_encoder_calls_is_match(monkeypatch, pair):
    calls = []

    def fake_is_match(classifier, query, candidate, threshold):
        calls.append((classifier, query["id"], candidate["id"], threshold))
        return {"match": True, "probability": 0.8}

    fake_module = ModuleType("Methods.bi_encoder.bi_encoder")
    fake_module.is_match = fake_is_match
    monkeypatch.setitem(sys.modules, "Methods.bi_encoder.bi_encoder", fake_module)

    result = match_with_bi_encoder(
        classifier="classifier",
        query=pair.query,
        candidate=pair.candidates[0],
        threshold=0.7,
    )

    assert result == {"match": True, "probability": 0.8}
    assert calls == [("classifier", "k1", "y1", 0.7)]


def test_record_conversion_for_ditto_excludes_empty_fields(pair):
    entity = _record_to_ditto_entity(pair.query)

    assert entity["title"] == "Cairo"
    assert entity["lat"] == "30.0444"
    assert entity["lon"] == "31.2357"
    assert "dataset" not in entity
    assert "id" not in entity
    assert "description" not in entity


def test_call_matching_methods_runs_ditto(monkeypatch, pair):
    threshold_values = []
    monkeypatch.setattr(
        "experiments.matching.match_with_ditto",
        lambda model, query, candidates, **kwargs: (
            threshold_values.append(kwargs["threshold"])
            or [
                {"candidate": candidate.id, "match": candidate.id == "y1", "probability": 0.8}
                for candidate in candidates
            ]
        ),
    )

    results = call_matching_methods(
        [pair],
        methods=("ditto",),
        ditto_model="ditto-model",
        ditto_threshold=0.81,
    )

    assert threshold_values == [0.81]
    assert results["ditto"][0][0] == {
        "candidate": "y1",
        "match": True,
        "probability": 0.8,
    }


def test_call_matching_methods_requires_ditto_model(pair):
    with pytest.raises(ValueError, match="ditto_model is required"):
        call_matching_methods(
            [pair],
            methods=("ditto",),
        )


def test_call_matching_methods_runs_llm(monkeypatch, pair):
    monkeypatch.setattr(
        "experiments.matching.match_with_llm",
        lambda query, candidates, provider: 1,
    )

    results = call_matching_methods(
        [pair],
        methods=("llm",),
    )

    assert results == {"llm": [1]}


def test_call_matching_methods_runs_bi_encoder(monkeypatch, pair):
    thresholds = []
    monkeypatch.setattr(
        "experiments.matching.match_with_bi_encoder",
        lambda classifier, query, candidate, threshold: (
            thresholds.append(threshold)
            or {
                "candidate": candidate.id,
                "match": candidate.id == "y1",
            }
        ),
    )

    results = call_matching_methods(
        [pair],
        methods=("bi_encoder",),
        classifier="classifier",
        bi_encoder_threshold=0.73,
    )

    assert thresholds == [0.73, 0.73]
    assert results["bi_encoder"] == [
        [
            {"candidate": "y1", "match": True},
            {"candidate": "y2", "match": False},
        ]
    ]


def test_call_matching_methods_requires_classifier(pair):
    with pytest.raises(ValueError, match="classifier is required"):
        call_matching_methods(
            [pair],
            methods=("bi_encoder",),
        )


def test_call_matching_methods_runs_deeper(monkeypatch, pair):
    thresholds = []
    prepared_pairs = []
    monkeypatch.setattr(
        "experiments.matching.match_with_deeper",
        lambda classifier, query, candidate, threshold: (
            thresholds.append(threshold)
            or {"match": candidate.id == "y1", "probability": 0.8}
        ),
    )
    monkeypatch.setattr(
        "Methods.deepER.deeper.get_default_extractor",
        lambda: SimpleNamespace(prepare_pairs=lambda pairs: prepared_pairs.extend(pairs)),
    )

    results = call_matching_methods(
        [pair],
        methods=("deeper",),
        deeper_classifier="deeper-model",
        deeper_threshold=0.73,
    )

    assert thresholds == [0.73, 0.73]
    assert prepared_pairs == [pair]
    assert results["deeper"][0] == [
        {"match": True, "probability": 0.8, "candidate": "y1"},
        {"match": False, "probability": 0.8, "candidate": "y2"},
    ]


def test_call_matching_methods_requires_deeper_classifier(pair):
    with pytest.raises(ValueError, match="deeper_classifier is required"):
        call_matching_methods(
            [pair],
            methods=("deeper",),
        )
