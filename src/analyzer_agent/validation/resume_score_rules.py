from ..interfaces.resume_score import ResumeScore


def validate(score: ResumeScore) -> None:
    _overall_range(score.overall_score)
    _breakdown_exists(score.breakdown)


def _overall_range(score: float) -> None:
    if score < 1:
        raise ValueError(
            f"RESUME_SCORE.overall_score must be >= 1, got {score}"
        )


def _breakdown_exists(breakdown) -> None:
    required = [
        "relevance_to_target_positions",
        "technical_skills",
        "professional_experience",
        "achievement_oriented_descriptions",
        "ats_optimization",
        "clarity_and_structure",
        "seniority_positioning",
    ]
    missing = [f for f in required if not hasattr(breakdown, f)]
    if missing:
        raise ValueError(
            f"RESUME_SCORE.breakdown is missing fields: {missing}"
        )
