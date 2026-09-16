import pytest
from pydantic import ValidationError

from job_search_agent.interface.discarded_job import DiscardedJob
from job_search_agent.interface.job_opportunity import JobOpportunity

VALID = dict(
    title="Senior Python Developer",
    description="Backend role",
    requirements=["python", "fastapi"],
    location="London, UK",
    company="Acme Corp",
)


def make(**overrides):
    data = dict(VALID)
    data.update(overrides)
    return JobOpportunity(**data)


def test_valid_opportunity():
    job = make()
    assert job.title == "Senior Python Developer"
    assert job.requirements == ["python", "fastapi"]
    assert job.salary_range is None
    assert job.apply_url is None
    assert job.source_provider is None


def test_source_provider_preserved():
    job = make(source_provider="adzuna")
    assert job.source_provider == "adzuna"


@pytest.mark.parametrize("field", ["title", "description", "location", "company"])
def test_required_non_empty(field):
    with pytest.raises(ValidationError, match="cannot be empty"):
        make(**{field: ""})


@pytest.mark.parametrize("field", ["title", "description", "location", "company"])
def test_required_strips_whitespace_only(field):
    with pytest.raises(ValidationError, match="cannot be empty"):
        make(**{field: "   "})


def test_values_are_stripped():
    job = make(title="  Senior Python Dev  ", company="  Acme  ")
    assert job.title == "Senior Python Dev"
    assert job.company == "Acme"


def test_requirements_none_becomes_empty():
    assert make(requirements=None).requirements == []


def test_requirements_as_string_rejected():
    with pytest.raises(ValidationError, match="list of strings"):
        make(requirements="python")


def test_requirements_wrong_item_type_rejected():
    with pytest.raises(ValidationError):
        make(requirements=["python", 42])


@pytest.mark.parametrize("field", ["apply_url", "company_url"])
def test_url_accepted(field):
    assert make(**{field: "https://example.com/job"}).model_dump()[field] == "https://example.com/job"


@pytest.mark.parametrize("field", ["apply_url", "company_url"])
def test_url_invalid_rejected(field):
    with pytest.raises(ValidationError, match="http"):
        make(**{field: "ftp://not-allowed"})


@pytest.mark.parametrize("field", ["apply_url", "company_url"])
def test_url_empty_normalized_to_none(field):
    assert make(**{field: ""}).model_dump()[field] is None


def test_discarded_job_raw_preserved():
    raw = {"title": "", "company": {"display_name": ""}}
    discarded = DiscardedJob(provider="adzuna", source_title="unknown", reasons=["empty"], raw=raw)
    assert discarded.raw == raw
    assert discarded.provider == "adzuna"