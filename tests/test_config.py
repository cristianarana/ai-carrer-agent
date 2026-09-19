from core.config import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_SEARCH_CATEGORY_WEIGHTS,
    DEFAULT_SEARCH_MIN_MATCH,
    Settings,
    load_settings,
)


def test_load_settings_defaults(monkeypatch):
    for key in (
        "LOG_LEVEL",
        "SEARCH_MIN_MATCH",
        "SEARCH_KEYWORD_WEIGHT",
        "SEARCH_RANK_WEIGHT",
        "SEARCH_MAX_RANK",
        "SEARCH_PROVIDER_TIMEOUT",
        "SEARCH_PROVIDER_RETRIES",
        "SEARCH_PROVIDER_BACKOFF",
        "ADZUNA_RESULTS_PER_PAGE",
        "OPEN_NINJA_NUM_PAGES",
        "OPENROUTER_TIMEOUT",
        "OPENROUTER_RETRIES",
        "OPENROUTER_BACKOFF",
        "OPENROUTER_MAX_TOKENS",
        "ANALYZER_MAX_ATTEMPTS",
        "MAX_RESUME_CHARS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = load_settings()

    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert settings.search_min_match == DEFAULT_SEARCH_MIN_MATCH
    assert settings.search_keyword_weight == 0.65
    assert settings.search_rank_weight == 0.35
    assert settings.search_max_rank == 20
    assert settings.search_provider_timeout == 15.0
    assert settings.search_provider_retries == 3
    assert settings.open_ninja_num_pages == 1
    assert settings.adzuna_results_per_page == 20
    assert settings.openrouter_max_tokens == 8000
    assert settings.analyzer_max_attempts == 3
    assert settings.max_resume_chars == 60_000


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SEARCH_MIN_MATCH", "0.5")
    monkeypatch.setenv("SEARCH_CATEGORY_WEIGHTS", "0.4, 0.9, 0.2")
    monkeypatch.setenv("SEARCH_MAX_RANK", "10")
    monkeypatch.setenv("SEARCH_PROVIDER_RETRIES", "5")

    settings = load_settings()

    assert settings.log_level == "DEBUG"
    assert settings.search_min_match == 0.5
    assert settings.search_category_weights == [0.4, 0.9, 0.2]
    assert settings.search_max_rank == 10
    assert settings.search_provider_retries == 5


def test_settings_is_frozen():
    settings = Settings()
    try:
        settings.log_level = "DEBUG"
    except Exception:
        pass
    assert settings.log_level == DEFAULT_LOG_LEVEL

    for cat_weight, default in zip(
        Settings().search_category_weights, DEFAULT_SEARCH_CATEGORY_WEIGHTS
    ):
        assert cat_weight == default