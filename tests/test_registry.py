import pytest

from job_search_agent.interface.job_opportunity import JobOpportunity
from job_search_agent.provider import PROVIDERS, get_provider, get_providers, search_all
from job_search_agent.provider.base_provider import ProviderError


def test_get_providers_returns_three():
    names = [p.name for p in get_providers()]
    assert names == ["open_ninja", "adzuna", "remotive"]


def test_get_provider_by_name():
    assert get_provider("remotive").name == "remotive"
    assert get_provider("adzuna").name == "adzuna"


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nope")


def _opportunity(title):
    return JobOpportunity(
        title=title,
        description="desc",
        requirements=[],
        location="Remote",
        company="Acme",
        apply_url="https://example.com/jobs/1",
    )


def test_search_all_failover_with_structured_errors(monkeypatch):
    by_name = {p.name: p for p in PROVIDERS}

    def ok(*args, **kwargs):
        return [_opportunity("Job A")]

    def boom(*args, **kwargs):
        raise ProviderError("open_ninja", "simulated network failure", status_code=500, transient=True)

    def unexpected(*args, **kwargs):
        raise RuntimeError("mapping exploded")

    monkeypatch.setattr(by_name["open_ninja"], "search_jobs", boom)
    monkeypatch.setattr(by_name["adzuna"], "search_jobs", ok)
    monkeypatch.setattr(by_name["remotive"], "search_jobs", unexpected)

    report = search_all("developer")

    assert report.role == "developer"
    assert report.location is None
    assert report.attempted_providers == ["open_ninja", "adzuna", "remotive"]
    assert len(report.jobs) == 1
    assert report.jobs[0].title == "Job A"
    assert "open_ninja" in report.errors
    assert "remotive" in report.errors
    assert "simulated network failure" in report.errors["open_ninja"]
    assert report.errors["remotive"].startswith("Unexpected: mapping exploded")


def test_search_all_harvests_discarded_jobs(monkeypatch):
    by_name = {p.name: p for p in PROVIDERS}

    def fail(provider_name):
        def _fn(*a, **k):
            raise ProviderError(provider_name, "down")

        return _fn

    for name, p in by_name.items():
        if name != "adzuna":
            monkeypatch.setattr(p, "search_jobs", fail(name))

    adzuna = by_name["adzuna"]
    payload = {
        "results": [
            {"title": "", "description": "x", "company": {"display_name": ""},
             "location": {"display_name": "Glasgow"}},
            {"title": "Valid Role", "description": "x", "company": {"display_name": "ACME"},
             "location": {"display_name": "Glasgow"}},
        ]
    }
    monkeypatch.setattr(
        adzuna,
        "_get_json",
        lambda url, params=None, headers=None: payload,
    )

    report = search_all("python developer")

    assert len(report.jobs) == 1
    assert report.jobs[0].title == "Valid Role"
    discarded = report.discarded_jobs["adzuna"]
    assert len(discarded) == 1
    assert discarded[0].provider == "adzuna"
    assert discarded[0].source_title == "unknown"
    assert discarded[0].raw == {"title": "", "description": "x", "company": {"display_name": ""},
                                 "location": {"display_name": "Glasgow"}}
    assert report.errors["open_ninja"].startswith("open_ninja")