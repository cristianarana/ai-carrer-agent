from job_search_agent.provider.adzuna_provider import AdzunaProvider
from job_search_agent.provider.open_ninja_provider import OpenNinjaProvider
from job_search_agent.provider.remotive_provider import RemotiveProvider

ADZUNA_ITEM = {
    "salary_min": 50000,
    "salary_max": 55000,
    "currency": "GBP",
    "location": {"display_name": "Marlow, Buckinghamshire"},
    "description": "JavaScript Developer snippet",
    "created": "2013-11-08T18:07:39Z",
    "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/129698749",
    "title": "Javascript Developer",
    "id": "129698749",
    "company": {"display_name": "Corporate Project Solutions"},
    "contract_time": "full_time",
    "contract_type": "permanent",
}

NINJA_ITEM = {
    "job_title": "Senior Front-End Developer",
    "employer_name": "TEKsystems",
    "employer_website": "https://www.teksystems.com/",
    "job_employment_type": "Full-time",
    "job_apply_link": "https://careers.teksystems.com/us/en/job/JP-006039510/apply",
    "job_description": "One North is a digital experience agency.",
    "job_is_remote": True,
    "job_posted_at_datetime_utc": "2026-05-19T00:00:00.000Z",
    "job_city": "Chicago",
    "job_state": "Illinois",
    "job_country": "US",
    "job_min_salary": 91700,
    "job_max_salary": 138000,
    "job_salary_period": "YEAR",
    "job_salary_currency": "USD",
    "job_highlights": {"Qualifications": ["3+ years experience", "Advanced React"]},
}

REMOTIVE_ITEM = {
    "id": 123,
    "url": "https://remotive.com/remote-jobs/product/lead-developer-123",
    "title": "Lead Developer",
    "company_name": "Remotive",
    "company_logo": "https://remotive.com/job/123/logo",
    "category": "Software Development",
    "tags": ["python", "fastapi"],
    "job_type": "full_time",
    "publication_date": "2020-02-15T10:23:26",
    "candidate_required_location": "Worldwide",
    "salary": "$40,000 - $50,000",
    "description": "<p>Full <b>HTML</b> description</p>",
}


def test_adzuna_maps_item():
    job = AdzunaProvider()._map_job(ADZUNA_ITEM)
    assert job.title == "Javascript Developer"
    assert job.company == "Corporate Project Solutions"
    assert job.location == "Marlow, Buckinghamshire"
    assert job.salary_range == "50000 - 55000 GBP"
    assert job.employment_type == "full_time"
    assert job.posted_date == "2013-11-08T18:07:39Z"
    assert job.apply_url == "https://www.adzuna.co.uk/jobs/land/ad/129698749"
    assert job.requirements == []


def test_adzuna_employment_type_falls_back_to_contract_type():
    item = {k: v for k, v in ADZUNA_ITEM.items() if k != "contract_time"}
    assert AdzunaProvider()._map_job(item).employment_type == "permanent"


def test_ninja_maps_item():
    job = OpenNinjaProvider()._map_job(NINJA_ITEM)
    assert job.title == "Senior Front-End Developer"
    assert job.company == "TEKsystems"
    assert job.location == "Chicago, Illinois, US"
    assert job.requirements == ["3+ years experience", "Advanced React"]
    assert job.salary_range == "91700 - 138000 USD YEAR"
    assert job.employment_type == "Full-time"
    assert job.posted_date == "2026-05-19T00:00:00.000Z"
    assert job.company_url == "https://www.teksystems.com/"
    assert job.apply_url == "https://careers.teksystems.com/us/en/job/JP-006039510/apply"


def test_ninja_remote_without_city():
    item = {k: v for k, v in NINJA_ITEM.items() if k in ("job_is_remote",)}
    assert OpenNinjaProvider._build_location(item) == "Remote"


def test_ninja_requirements_fallback_to_required_skills():
    item = {k: v for k, v in NINJA_ITEM.items() if k != "job_highlights"}
    item["job_required_skills"] = ["react", "typescript"]
    assert OpenNinjaProvider()._map_job(item).requirements == ["react", "typescript"]


def test_remotive_maps_item():
    job = RemotiveProvider()._map_job(REMOTIVE_ITEM)
    assert job.title == "Lead Developer"
    assert job.company == "Remotive"
    assert job.location == "Worldwide"
    assert job.requirements == ["python", "fastapi"]
    assert job.salary_range == "$40,000 - $50,000"
    assert job.employment_type == "full_time"
    assert job.posted_date == "2020-02-15T10:23:26"
    assert job.apply_url == "https://remotive.com/remote-jobs/product/lead-developer-123"
    assert job.description == "Full HTML description"
    assert job.company_url == "https://remotive.com/job/123/logo"


def test_remotive_strips_html():
    assert (
        RemotiveProvider._html_to_text("<p>Hello <b>World</b> &amp; more</p>")
        == "Hello World & more"
    )


# --------------------------------------------------------------------------- #
# Request construction (parámetros según documentación oficial)
# --------------------------------------------------------------------------- #

def test_adzuna_request_params(monkeypatch):
    provider = AdzunaProvider()
    captured = {}

    def fake_get_json(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return {"results": []}

    monkeypatch.setattr(provider, "_get_json", fake_get_json)
    provider.search_jobs(
        "javascript developer", location="London", country="us", page=2, full_time=1
    )

    assert captured["url"] == "https://api.adzuna.com/v1/api/jobs/us/search/2"
    params = captured["params"]
    assert params["what"] == "javascript developer"
    assert params["where"] == "London"
    assert params["full_time"] == 1
    assert params["content-type"] == "application/json"
    assert captured["headers"]["Accept"] == "application/json"


def test_ninja_request_params(monkeypatch):
    provider = OpenNinjaProvider()
    captured = {}

    def fake_get_json(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return {"data": {"jobs": [NINJA_ITEM]}}

    monkeypatch.setattr(provider, "_get_json", fake_get_json)
    jobs = provider.search_jobs("developer", location="chicago", work_from_home=True)

    assert captured["url"] == "https://api.openwebninja.com/jsearch/search-v2"
    assert captured["params"]["query"] == "developer in chicago"
    assert captured["params"]["work_from_home"] == "true"
    assert captured["params"]["country"] == "us"
    assert captured["headers"]["x-api-key"] == provider.api_key
    assert len(jobs) == 1


def test_remotive_request_params(monkeypatch):
    provider = RemotiveProvider()
    captured = {}

    def fake_get_json(url, params=None):
        captured["url"] = url
        captured["params"] = params
        return {"jobs": [REMOTIVE_ITEM]}

    monkeypatch.setattr(provider, "_get_json", fake_get_json)
    jobs = provider.search_jobs("python", category="software-dev", limit=10)

    assert captured["url"] == "https://remotive.com/api/remote-jobs"
    assert captured["params"] == {"search": "python", "category": "software-dev", "limit": "10"}
    assert len(jobs) == 1