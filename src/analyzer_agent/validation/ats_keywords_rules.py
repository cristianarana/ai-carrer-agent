from ..interfaces.ats_keywords import ATSKeywords


def validate(keywords: ATSKeywords) -> None:
    _min_per_list(keywords.technical_skills, "technical_skills")
    _min_per_list(keywords.tools_and_technologies, "tools_and_technologies")
    _min_per_list(keywords.professional_skills, "professional_skills")
    _min_per_list(keywords.ai_data_keywords, "ai_data_keywords")


def _min_per_list(items: list[str], field: str) -> None:
    if len(items) < 1:
        raise ValueError(
            f"ATS_KEYWORDS.{field} must contain at least 1 keyword, got {len(items)}"
        )
