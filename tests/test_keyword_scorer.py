from analyzer_agent.interfaces.ats_keywords import ATSKeywords
from analyzer_agent.interfaces.job_position import JobPosition
from job_search_agent.helper.keyword_scorer import KeywordScorer
from job_search_agent.interface.job_opportunity import JobOpportunity


def _keywords():
    return ATSKeywords(
        technical_skills=[],
        tools_and_technologies=[],
        professional_skills=[],
        ai_data_keywords=[],
    )


def _position(rank: int = 1):
    return JobPosition(position="Role", rank=rank, match_explanation="x")


def _job(title: str = "Role", description: str = "generic developer", requirements=None):
    return JobOpportunity(
        title=title,
        description=description,
        requirements=requirements or [],
        location="Remote",
        company="Acme",
    )


def _keyword_match(job, *keywords: str) -> float:
    kw = _keywords()
    kw.technical_skills = list(keywords)
    return KeywordScorer()._keyword_match(job, kw)


def test_technical_skill_single_token_no_substring_match():
    assert _keyword_match(_job(title="Pythonista"), "python") == 0.0
    assert _keyword_match(_job(description="a pythonista workflow"), "python") == 0.0


def test_ai_does_not_match_common_words():
    assert _keyword_match(_job(title="Said Al-Chairman"), "ai") == 0.0
    assert _keyword_match(_job(title="AI Engineer"), "ai") == 1.0


def test_phrase_matches_adjacent_tokens():
    kw = _keywords()
    kw.ai_data_keywords = ["machine learning"]
    job = _job(description="we hire machine learning engineers")
    assert KeywordScorer()._best_field_weight("machine learning", KeywordScorer._tokenized_fields(job)) > 0.0


def test_phrase_fallback_when_tokens_not_adjacent():
    kw = _keywords()
    kw.ai_data_keywords = ["machine learning"]
    job = _job(description="machine engineering and learning")
    assert KeywordScorer()._best_field_weight("machine learning", KeywordScorer._tokenized_fields(job)) > 0.0


def test_phrase_no_match_when_token_missing():
    job = _job(description="machine engineering and analysis")
    assert KeywordScorer()._best_field_weight("machine learning", KeywordScorer._tokenized_fields(job)) == 0.0


def test_company_and_location_do_not_count_for_match():
    in_title = _job(title="docker")
    only_company = _job(description="base work", requirements=[])
    only_company.company = "docker corp"
    only_location = _job(description="base work", requirements=[])
    only_location.location = "docker city"

    assert _keyword_match(in_title, "docker") == 1.0
    assert _keyword_match(only_company, "docker") == 0.0
    assert _keyword_match(only_location, "docker") == 0.0


def test_requirements_and_description_count_full():
    in_requirements = _job(description="base work", requirements=["docker"])
    in_description = _job(description="docker expertise")
    assert _keyword_match(in_requirements, "docker") == 1.0
    assert _keyword_match(in_description, "docker") == 1.0


def test_token_with_plus_and_dot():
    assert _keyword_match(_job(title="We use c++"), "c++") > 0.0
    assert _keyword_match(_job(title="We use node.js"), "node.js") > 0.0
    assert _keyword_match(_job(title="We use c++"), "c") == 0.0
    assert _keyword_match(_job(title="We use node.js"), "node") == 0.0


def test_rank_match_conserved():
    assert KeywordScorer._rank_match(_position(rank=10)) == 0.55