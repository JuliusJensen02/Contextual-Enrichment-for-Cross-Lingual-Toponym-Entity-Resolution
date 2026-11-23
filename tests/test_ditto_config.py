import pytest

from third_party.ditto.ditto_light.config import resolve_task_config


def test_custom_task_uses_supplied_dataset_paths():
    paths = {
        "trainset": "data/train.txt",
        "validset": "data/valid.txt",
        "testset": "data/test.txt",
    }

    config = resolve_task_config({}, "toponym_experiment", paths, tuple(paths))

    assert config["name"] == "toponym_experiment"
    assert {key: config[key] for key in paths} == paths


def test_supplied_paths_override_configured_task_paths():
    configs = {
        "existing": {
            "name": "existing",
            "trainset": "old-train.txt",
            "validset": "old-valid.txt",
            "testset": "old-test.txt",
        }
    }

    config = resolve_task_config(
        configs,
        "existing",
        {"trainset": "new-train.txt", "validset": None, "testset": None},
        ("trainset", "validset", "testset"),
    )

    assert config["trainset"] == "new-train.txt"
    assert config["validset"] == "old-valid.txt"
    assert config["testset"] == "old-test.txt"


def test_custom_task_requires_all_dataset_paths():
    with pytest.raises(ValueError, match="--validset, --testset"):
        resolve_task_config(
            {},
            "toponym_experiment",
            {"trainset": "train.txt", "validset": None, "testset": None},
            ("trainset", "validset", "testset"),
        )
