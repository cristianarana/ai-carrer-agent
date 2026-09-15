from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from requests import HTTPError, Timeout

from job_search_agent.interface.job_opportunity import JobOpportunity
from job_search_agent.interface.provider_result import ProviderSearchResult
from job_search_agent.provider import base_provider as base
from job_search_agent.provider.base_provider import JobProvider, ProviderError


class DummyProvider(JobProvider):
    name = "dummy"
    base_url = "https://dummy.test/api"

    def search_jobs(self, role, location=None, **kwargs):
        jobs, discarded = self._map_items([])
        return ProviderSearchResult(
            provider=self.name, jobs=jobs, discarded_jobs=discarded
        )

    def _map_job(self, item: dict) -> JobOpportunity:
        return JobOpportunity(
            title=item["title"],
            description=item.get("description", ""),
            requirements=item.get("requirements", []),
            location=item.get("location", ""),
            company=item.get("company", ""),
            apply_url=item.get("apply_url"),
        )


def _resp(payload, status_code=200):
    response = SimpleNamespace()
    response.status_code = status_code
    if status_code >= 400:
        response.raise_for_status = lambda: (_ for _ in ()).throw(
            HTTPError(f"{status_code} Client Error", response=response)
        )
    else:
        response.raise_for_status = lambda: None
    response.json = lambda: payload
    return response


# --------------------------------------------------------------------------- #
# _map_items
# --------------------------------------------------------------------------- #

def test_map_items_valid_job():
    provider = DummyProvider()
    jobs, discarded = provider._map_items(
        [{"title": "Dev", "description": "desc", "company": "Acme", "location": "London"}]
    )
    assert len(jobs) == 1
    assert jobs[0].title == "Dev"
    assert discarded == []


def test_map_items_discards_invalid_keeps_valid():
    provider = DummyProvider()
    items = [
        {"title": "", "description": "desc", "company": "Acme", "location": "London"},
        {"title": "Dev", "description": "desc", "company": "Acme", "location": "London"},
    ]
    jobs, discarded = provider._map_items(items)
    assert len(jobs) == 1
    assert jobs[0].title == "Dev"
    assert len(discarded) == 1
    discarded_job = discarded[0]
    assert discarded_job.provider == "dummy"
    assert discarded_job.source_title == "unknown"
    assert discarded_job.reasons
    assert discarded_job.raw == items[0]


# --------------------------------------------------------------------------- #
# _get_json: retries / errors
# --------------------------------------------------------------------------- #

def test_get_json_success(monkeypatch):
    monkeypatch.setattr(base.requests, "get", lambda url, **kw: _resp({"ok": 1}))
    assert DummyProvider()._get_json("https://dummy.test") == {"ok": 1}


def test_get_json_retries_transient_then_success(monkeypatch):
    attempts = {"n": 0}

    def fake_get(url, **kw):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise Timeout("simulated timeout")
        return _resp({"ok": 2})

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    provider = DummyProvider()
    provider.timeout, provider.retries, provider.backoff = 0.001, 3, 0.01
    assert provider._get_json("https://dummy.test") == {"ok": 2}
    assert attempts["n"] == 2


def test_get_json_raises_provider_error_after_retries(monkeypatch):
    attempts = {"n": 0}
    calls = []

    def fake_get(url, **kw):
        attempts["n"] += 1
        raise Timeout("always down")

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda s: calls.append(s))
    provider = DummyProvider()
    provider.timeout, provider.retries, provider.backoff = 0.001, 3, 0.5

    with pytest.raises(ProviderError) as exc_info:
        provider._get_json("https://dummy.test")

    assert attempts["n"] == 4
    assert calls == [0.5, 1.0, 2.0]
    assert exc_info.value.provider == "dummy"
    assert exc_info.value.transient is False


def test_get_json_4xx_fails_immediately_no_retries(monkeypatch):
    attempts = {"n": 0}

    def fake_get(url, **kw):
        attempts["n"] += 1
        return _resp({"error": "forbidden"}, status_code=403)

    monkeypatch.setattr(base.requests, "get", fake_get)
    provider = DummyProvider()
    provider.retries = 3

    with pytest.raises(ProviderError) as exc_info:
        provider._get_json("https://dummy.test")

    assert attempts["n"] == 1
    assert exc_info.value.status_code == 403
    assert exc_info.value.transient is False


def test_get_json_5xx_retries_then_provider_error(monkeypatch):
    attempts = {"n": 0}

    def fake_get(url, **kw):
        attempts["n"] += 1
        return _resp({"error": "boom"}, status_code=500)

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    provider = DummyProvider()
    provider.retries = 2

    with pytest.raises(ProviderError):
        provider._get_json("https://dummy.test")

    assert attempts["n"] == 3


# --------------------------------------------------------------------------- #
# _build_salary_range
# --------------------------------------------------------------------------- #

def test_salary_range_none_when_no_values():
    assert JobProvider._build_salary_range(None, None) is None


def test_salary_range_only_minimum():
    assert JobProvider._build_salary_range(50000, None) == "50000"


def test_salary_range_full():
    result = JobProvider._build_salary_range(50000, 55000, "GBP", "YEAR")
    assert result == "50000 - 55000 GBP YEAR"


# --------------------------------------------------------------------------- #
# is_configured
# --------------------------------------------------------------------------- #

def test_is_configured_true_without_required_vars():
    assert DummyProvider().is_configured() is True


def test_is_configured_false_when_env_missing(monkeypatch):
    class ConfiguredProvider(DummyProvider):
        config_required = ("FAKE_APP_ID", "FAKE_API_KEY")

    monkeypatch.delenv("FAKE_APP_ID", raising=False)
    monkeypatch.delenv("FAKE_API_KEY", raising=False)
    assert ConfiguredProvider().is_configured() is False


def test_is_configured_true_when_env_present(monkeypatch):
    class ConfiguredProvider(DummyProvider):
        config_required = ("FAKE_API_KEY",)

    monkeypatch.setenv("FAKE_API_KEY", "secret")
    assert ConfiguredProvider().is_configured() is True