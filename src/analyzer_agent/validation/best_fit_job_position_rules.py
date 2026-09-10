from ..interfaces.job_position import JobPosition


_EXACT_POSITIONS = 20


def validate(positions: list[JobPosition]) -> None:
    _count(positions)
    _ranks(positions)


def _count(positions: list[JobPosition]) -> None:
    if len(positions) != _EXACT_POSITIONS:
        raise ValueError(
            f"BEST_FIT_JOB_POSITIONS must contain exactly "
            f"{_EXACT_POSITIONS} items, got {len(positions)}"
        )


def _ranks(positions: list[JobPosition]) -> None:
    ranks = sorted(p.rank for p in positions)
    if ranks != list(range(1, _EXACT_POSITIONS + 1)):
        raise ValueError(
            f"BEST_FIT_JOB_POSITIONS ranks must be 1..{_EXACT_POSITIONS} "
            f"consecutive, got {ranks}"
        )
