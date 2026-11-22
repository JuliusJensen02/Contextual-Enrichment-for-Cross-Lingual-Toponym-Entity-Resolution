from typing import Any


def resolve_task_config(
    configs: dict[str, dict[str, Any]],
    task: str,
    overrides: dict[str, str | None],
    required: tuple[str, ...],
) -> dict[str, Any]:
    config = dict(configs.get(task, {"name": task}))
    config.update({key: value for key, value in overrides.items() if value is not None})

    missing = [key for key in required if not config.get(key)]
    if missing:
        required_paths = ", ".join(f"--{key}" for key in missing)
        raise ValueError(
            f"Task {task!r} has no configured dataset path for {required_paths}"
        )

    return config
