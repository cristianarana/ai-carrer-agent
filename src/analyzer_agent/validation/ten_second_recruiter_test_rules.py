from ..interfaces.recruiter_10_sec_test import Recruiter10SecondTest

_MIN_ITEMS = 3


def validate(test: Recruiter10SecondTest) -> None:
    _min_items(test.positive, "positive")
    _min_items(test.unclear_or_weak, "unclear_or_weak")
    _min_items(test.could_cause_rejection, "could_cause_rejection")


def _min_items(items: list[str], field: str) -> None:
    if len(items) < _MIN_ITEMS:
        raise ValueError(
            f"TEN_SECOND_RECRUITER_TEST.{field} must contain at least "
            f"{_MIN_ITEMS} items, got {len(items)}"
        )
