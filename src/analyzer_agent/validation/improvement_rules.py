from ..interfaces.improvement import VALID_PRIORITIES


def validate(items: list, field_path: str) -> None:
    for i, item in enumerate(items):
        _valid_priority(item.priority, f"{field_path}[{i}]")


def _valid_priority(priority: str, path: str) -> None:
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"{path}.priority must be one of {VALID_PRIORITIES}, got '{priority}'"
        )
