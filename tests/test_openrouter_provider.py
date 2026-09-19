import pytest

from analyzer_agent.errors import AnalysisProviderError
from analyzer_agent.providers.openrouter import OpenRouterProvider
from analyzer_agent.providers import openrouter as orm


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}
        self.reason = "?"

    def json(self):
        return self._payload


_CHAT_OK = {
    "id": "gen-1",
    "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
    "usage": {"total_tokens": 10},
}


def _post_requests(monkeypatch, responses):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr("requests.post", fake_post)
    return calls


def test_generate_json_sends_expected_request(monkeypatch):
    calls = _post_requests(monkeypatch, [FakeResponse(payload=_CHAT_OK)])
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")

    result = provider.generate_json("Analyze CV")

    assert result == '{"ok": true}'
    url, kwargs = calls[0]
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    body = kwargs["json"]
    assert body["model"] == "deepseek/fake"
    assert body["messages"] == [{"role": "user", "content": "Analyze CV"}]
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 8000


def test_generate_json_retries_on_429_and_honors_retry_after(monkeypatch):
    sleeps = []
    monkeypatch.setattr(orm.time, "sleep", sleeps.append)
    calls = _post_requests(
        monkeypatch,
        [
            FakeResponse(
                status_code=429,
                payload={"error": {"message": "Rate limited"}},
                headers={"Retry-After": "2"},
            ),
            FakeResponse(payload=_CHAT_OK),
        ],
    )
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")

    result = provider.generate_json("Analyze CV")

    assert result == '{"ok": true}'
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_generate_json_fails_fast_on_401(monkeypatch):
    sleeps = []
    monkeypatch.setattr(orm.time, "sleep", sleeps.append)
    calls = _post_requests(
        monkeypatch,
        [
            FakeResponse(
                status_code=401,
                payload={"error": {"message": "Invalid API key"}},
                text="Invalid API key",
            )
        ],
    )
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.generate_json("Analyze CV")

    assert exc_info.value.status_code == 401
    assert exc_info.value.transient is False
    assert len(calls) == 1
    assert sleeps == []


def test_generate_json_exhausts_retries_on_transient_5xx(monkeypatch):
    sleeps = []
    monkeypatch.setattr(orm.time, "sleep", sleeps.append)
    calls = _post_requests(
        monkeypatch,
        [FakeResponse(status_code=502, text="upstream failed")] * 3,
    )
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")
    provider.retries = 2

    with pytest.raises(AnalysisProviderError) as exc_info:
        provider.generate_json("Analyze CV")

    assert exc_info.value.status_code == 502
    assert exc_info.value.transient is True
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_generate_json_raises_on_missing_content(monkeypatch):
    calls = _post_requests(
        monkeypatch, [FakeResponse(payload={"choices": [{"message": {}}]})]
    )
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")

    with pytest.raises(AnalysisProviderError):
        provider.generate_json("Analyze CV")
    assert len(calls) == 1


def test_missing_api_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_KEY"):
        OpenRouterProvider(api_key=None, model="deepseek/fake")


def test_http_date_retry_after_parsed(monkeypatch):
    import datetime

    sleeps = []
    monkeypatch.setattr(orm.time, "sleep", sleeps.append)
    retry_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(seconds=5)
    ).strftime("%a, %d %b %Y %H:%M:%S GMT")
    calls = _post_requests(
        monkeypatch,
        [
            FakeResponse(
                status_code=429,
                payload={"error": {"message": "Rate limited"}},
                headers={"Retry-After": retry_at},
            ),
            FakeResponse(payload=_CHAT_OK),
        ],
    )
    provider = OpenRouterProvider(api_key="sk-test", model="deepseek/fake")

    result = provider.generate_json("Analyze CV")

    assert result == '{"ok": true}'
    assert len(calls) == 2
    assert len(sleeps) == 1 and 0.0 <= sleeps[0] <= 6.0