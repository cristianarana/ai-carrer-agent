from ..interfaces.how_to_reach_10 import HowToReach10

from . import improvement_rules

_MINIMUMS = {
    "immediate_actions": 3,
    "technical_enhancements": 3,
    "ats_optimization": 3,
    "professional_and_structural_improvements": 2,
    "long_term_improvements": 2,
}


def validate(how: HowToReach10) -> None:
    for field, min_count in _MINIMUMS.items():
        items = getattr(how, field)
        _min_items(items, min_count, field)
        improvement_rules.validate(items, f"HOW_TO_REACH_10.{field}")


def _min_items(items: list, min_count: int, field: str) -> None:
    if len(items) < min_count:
        raise ValueError(
            f"HOW_TO_REACH_10.{field} must contain at least "
            f"{min_count} items, got {len(items)}"
        )
