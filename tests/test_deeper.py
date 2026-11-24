from types import SimpleNamespace

import numpy as np

from Methods.deepER.deeper import (
    FEATURE_NAMES,
    DeepERFeatureExtractor,
    compare_records,
    load_classifier,
    match_probability,
    train_classifier,
    training_data,
)
from experiments.data_preparation import Pair


class FakeMultilingualEncoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(tuple(texts))
        vectors = {
            "Babylon": [1.0, 0.0],
            "Bābili": [0.8, 0.6],
            "Egypt": [0.0, 1.0],
            "Aegyptus": [0.0, 1.0],
            "city": [1.0, 0.0],
        }
        return np.asarray([vectors[text] for text in texts], dtype=np.float32)


def record(record_id, title, *, variants="", country="", lat="", lon="", begin="", end="", ipa=""):
    return SimpleNamespace(
        id=record_id,
        title=title,
        name_variants=variants,
        wiki_title="",
        title_ipa=ipa,
        country=country,
        capital="",
        neighbours="",
        population="",
        types="city",
        instance_of_label="",
        details="",
        described_by="",
        description="",
        text_snippets="",
        lat=lat,
        lon=lon,
        begin_date=begin,
        end_date=end,
        inception="",
        dissolved="",
    )


def test_deeper_features_use_multilingual_vectors_and_toponym_attributes():
    encoder = FakeMultilingualEncoder()
    extractor = DeepERFeatureExtractor(encoder)
    source = record(
        "s1",
        "Babylon",
        country="Egypt",
        lat="30",
        lon="31",
        begin="-500",
        end="100",
        ipa="bæbɪlən",
    )
    target = record(
        "t1",
        "Bābili",
        country="Aegyptus",
        lat="30",
        lon="31",
        begin="-200",
        end="200",
        ipa="bæbɪlən",
    )

    features = compare_records(source, target, extractor)

    assert len(features) == len(FEATURE_NAMES)
    assert features[0] == np.float32(0.8)
    assert features[1] == 1.0
    assert features[2] == 1.0
    assert features[4] == 1.0
    assert features[5] == 0.0
    assert features[6:] == [1.0, 0.0]
    assert encoder.calls.count(("city",)) == 1


def test_training_data_flattens_pair_labels_and_rejects_misaligned_labels():
    extractor = DeepERFeatureExtractor(FakeMultilingualEncoder())
    query = record("s1", "Babylon")
    candidate = record("t1", "Bābili")
    pair = Pair(query=query, candidates=[candidate], labels=[True])

    features, labels = training_data([pair], extractor)

    assert features.shape == (1, len(FEATURE_NAMES))
    assert labels.tolist() == [1]

    invalid_pair = Pair(query=query, candidates=[candidate], labels=[])
    try:
        training_data([invalid_pair], extractor)
    except ValueError as error:
        assert "candidates but 0 labels" in str(error)
    else:
        raise AssertionError("Mismatched candidate labels must be rejected.")


def test_prepare_pairs_batches_unique_attribute_texts():
    encoder = FakeMultilingualEncoder()
    extractor = DeepERFeatureExtractor(encoder, batch_size=2)
    pairs = [
        Pair(
            query=record("s1", "Babylon", country="Egypt"),
            candidates=[record("t1", "Bābili", country="Aegyptus")],
            labels=[True],
        ),
        Pair(
            query=record("s2", "Babylon", country="Egypt"),
            candidates=[record("t2", "city", country="Aegyptus")],
            labels=[False],
        ),
    ]

    extractor.prepare_pairs(pairs)
    features, labels = training_data(pairs, extractor)

    assert labels.tolist() == [1, 0]
    assert features.shape == (2, len(FEATURE_NAMES))
    assert len(encoder.calls) == 4
    assert sum(len(call) for call in encoder.calls) == 6


def test_classifier_trains_saves_and_scores_project_pairs(tmp_path):
    extractor = DeepERFeatureExtractor(FakeMultilingualEncoder())
    query = record("s1", "Babylon")
    positive = record("t1", "Bābili")
    negative = record("t2", "city")
    pair = Pair(query=query, candidates=[positive, negative], labels=[True, False])

    classifier = train_classifier([pair], extractor, n_estimators=10)
    model_path = tmp_path / "deeper.joblib"

    import joblib

    joblib.dump(classifier, model_path)
    loaded = load_classifier(model_path)

    assert loaded.n_features_in_ == len(FEATURE_NAMES)
    assert 0.0 <= match_probability(loaded, query, positive, extractor) <= 1.0


def test_model_loader_uses_hf_token_from_environment(monkeypatch, tmp_path):
    import sys
    import types

    calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name, *, token):
            calls.append((model_name, token))

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setenv("HF_TOKEN", "test-token")

    model = DeepERFeatureExtractor()._get_model()

    assert isinstance(model, FakeSentenceTransformer)
    assert calls == [("sentence-transformers/LaBSE", "test-token")]


def test_model_loader_reads_project_env_file_when_token_is_not_exported(monkeypatch, tmp_path):
    import sys
    import types
    import Methods.deepER.deeper as deeper

    calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name, *, token):
            calls.append((model_name, token))

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    env_file = tmp_path / ".env"
    env_file.write_text("HF_TOKEN: project-token\n", encoding="utf-8")
    monkeypatch.setattr(deeper, "__file__", str(tmp_path / "Methods" / "deepER" / "deeper.py"))
    monkeypatch.delenv("HF_TOKEN", raising=False)

    model = DeepERFeatureExtractor()._get_model()

    assert isinstance(model, FakeSentenceTransformer)
    assert calls == [("sentence-transformers/LaBSE", "project-token")]
