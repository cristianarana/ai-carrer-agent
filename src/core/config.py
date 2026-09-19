import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LLM_MODEL = "~deepseek/deepseek-flash-latest"
DEFAULT_SEARCH_TOP_N = 5
DEFAULT_SEARCH_MAX_WORKERS = 4
DEFAULT_MAX_RESUME_CHARS = 60_000
DEFAULT_MAX_CV_BYTES = 5 * 1024 * 1024
DEFAULT_OUTPUT_DIR = "reports"

DEFAULT_OPENROUTER_MAX_TOKENS = 8000
DEFAULT_OPENROUTER_TIMEOUT = 60.0
DEFAULT_OPENROUTER_RETRIES = 3
DEFAULT_OPENROUTER_BACKOFF = 1.0

DEFAULT_ANALYZER_MAX_ATTEMPTS = 3
DEFAULT_ANALYZER_REPAIR_MAX_PREVIOUS_CHARS = 4_000
DEFAULT_ANALYZER_REPAIR_MAX_ERRORS_CHARS = 4_000
DEFAULT_ANALYZER_LOG_SAMPLE_CHARS = 300

DEFAULT_SEARCH_MIN_MATCH = 0.85
DEFAULT_SEARCH_KEYWORD_WEIGHT = 0.65
DEFAULT_SEARCH_RANK_WEIGHT = 0.35
DEFAULT_SEARCH_CATEGORY_WEIGHTS = [1.0, 0.8, 1.0, 0.6]
DEFAULT_SEARCH_FIELD_WEIGHTS = [1.0, 1.0, 1.0]
DEFAULT_SEARCH_MAX_RANK = 20

DEFAULT_SEARCH_PROVIDER_TIMEOUT = 15.0
DEFAULT_SEARCH_PROVIDER_RETRIES = 3
DEFAULT_SEARCH_PROVIDER_BACKOFF = 1.0
DEFAULT_SEARCH_PROVIDER_MIN_INTERVAL = 0.0

DEFAULT_ADZUNA_RESULTS_PER_PAGE = 20
DEFAULT_ADZUNA_MIN_INTERVAL = 0.5
DEFAULT_OPEN_NINJA_NUM_PAGES = 1


@dataclass(frozen=True)
class Settings:
    log_level: str = DEFAULT_LOG_LEVEL
    llm_model: str = DEFAULT_LLM_MODEL
    search_top_n: int = DEFAULT_SEARCH_TOP_N
    search_max_workers: int = DEFAULT_SEARCH_MAX_WORKERS
    search_min_match: float = DEFAULT_SEARCH_MIN_MATCH
    search_keyword_weight: float = DEFAULT_SEARCH_KEYWORD_WEIGHT
    search_rank_weight: float = DEFAULT_SEARCH_RANK_WEIGHT
    search_category_weights: list[float] = field(
        default_factory=lambda: list(DEFAULT_SEARCH_CATEGORY_WEIGHTS)
    )
    search_field_weights: list[float] = field(
        default_factory=lambda: list(DEFAULT_SEARCH_FIELD_WEIGHTS)
    )
    search_max_rank: int = DEFAULT_SEARCH_MAX_RANK
    search_provider_timeout: float = DEFAULT_SEARCH_PROVIDER_TIMEOUT
    search_provider_retries: int = DEFAULT_SEARCH_PROVIDER_RETRIES
    search_provider_backoff: float = DEFAULT_SEARCH_PROVIDER_BACKOFF
    search_provider_min_interval: float = DEFAULT_SEARCH_PROVIDER_MIN_INTERVAL
    adzuna_results_per_page: int = DEFAULT_ADZUNA_RESULTS_PER_PAGE
    adzuna_min_interval: float = DEFAULT_ADZUNA_MIN_INTERVAL
    open_ninja_num_pages: int = DEFAULT_OPEN_NINJA_NUM_PAGES
    openrouter_max_tokens: int = DEFAULT_OPENROUTER_MAX_TOKENS
    openrouter_timeout: float = DEFAULT_OPENROUTER_TIMEOUT
    openrouter_retries: int = DEFAULT_OPENROUTER_RETRIES
    openrouter_backoff: float = DEFAULT_OPENROUTER_BACKOFF
    analyzer_max_attempts: int = DEFAULT_ANALYZER_MAX_ATTEMPTS
    analyzer_repair_max_previous_chars: int = (
        DEFAULT_ANALYZER_REPAIR_MAX_PREVIOUS_CHARS
    )
    analyzer_repair_max_errors_chars: int = (
        DEFAULT_ANALYZER_REPAIR_MAX_ERRORS_CHARS
    )
    analyzer_log_sample_chars: int = DEFAULT_ANALYZER_LOG_SAMPLE_CHARS
    max_resume_chars: int = DEFAULT_MAX_RESUME_CHARS
    max_cv_bytes: int = DEFAULT_MAX_CV_BYTES
    output_dir: str = DEFAULT_OUTPUT_DIR


def _env_str(name: str, default: str) -> str:
    return os.getenv(name) or default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _env_floats(name: str, default: list[float]) -> list[float]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def load_settings() -> Settings:
    return Settings(
        log_level=_env_str("LOG_LEVEL", DEFAULT_LOG_LEVEL),
        llm_model=_env_str("OPENROUTER_MODEL", DEFAULT_LLM_MODEL),
        search_top_n=_env_int("SEARCH_TOP_N", DEFAULT_SEARCH_TOP_N),
        search_max_workers=_env_int(
            "SEARCH_MAX_WORKERS", DEFAULT_SEARCH_MAX_WORKERS
        ),
        search_min_match=_env_float(
            "SEARCH_MIN_MATCH", DEFAULT_SEARCH_MIN_MATCH
        ),
        search_keyword_weight=_env_float(
            "SEARCH_KEYWORD_WEIGHT", DEFAULT_SEARCH_KEYWORD_WEIGHT
        ),
        search_rank_weight=_env_float(
            "SEARCH_RANK_WEIGHT", DEFAULT_SEARCH_RANK_WEIGHT
        ),
        search_category_weights=_env_floats(
            "SEARCH_CATEGORY_WEIGHTS", DEFAULT_SEARCH_CATEGORY_WEIGHTS
        ),
        search_field_weights=_env_floats(
            "SEARCH_FIELD_WEIGHTS", DEFAULT_SEARCH_FIELD_WEIGHTS
        ),
        search_max_rank=_env_int("SEARCH_MAX_RANK", DEFAULT_SEARCH_MAX_RANK),
        search_provider_timeout=_env_float(
            "SEARCH_PROVIDER_TIMEOUT", DEFAULT_SEARCH_PROVIDER_TIMEOUT
        ),
        search_provider_retries=_env_int(
            "SEARCH_PROVIDER_RETRIES", DEFAULT_SEARCH_PROVIDER_RETRIES
        ),
        search_provider_backoff=_env_float(
            "SEARCH_PROVIDER_BACKOFF", DEFAULT_SEARCH_PROVIDER_BACKOFF
        ),
        search_provider_min_interval=_env_float(
            "SEARCH_PROVIDER_MIN_INTERVAL", DEFAULT_SEARCH_PROVIDER_MIN_INTERVAL
        ),
        adzuna_results_per_page=_env_int(
            "ADZUNA_RESULTS_PER_PAGE", DEFAULT_ADZUNA_RESULTS_PER_PAGE
        ),
        adzuna_min_interval=_env_float(
            "ADZUNA_MIN_INTERVAL", DEFAULT_ADZUNA_MIN_INTERVAL
        ),
        open_ninja_num_pages=_env_int(
            "OPEN_NINJA_NUM_PAGES", DEFAULT_OPEN_NINJA_NUM_PAGES
        ),
        openrouter_max_tokens=_env_int(
            "OPENROUTER_MAX_TOKENS", DEFAULT_OPENROUTER_MAX_TOKENS
        ),
        openrouter_timeout=_env_float(
            "OPENROUTER_TIMEOUT", DEFAULT_OPENROUTER_TIMEOUT
        ),
        openrouter_retries=_env_int(
            "OPENROUTER_RETRIES", DEFAULT_OPENROUTER_RETRIES
        ),
        openrouter_backoff=_env_float(
            "OPENROUTER_BACKOFF", DEFAULT_OPENROUTER_BACKOFF
        ),
        analyzer_max_attempts=_env_int(
            "ANALYZER_MAX_ATTEMPTS", DEFAULT_ANALYZER_MAX_ATTEMPTS
        ),
        analyzer_repair_max_previous_chars=_env_int(
            "ANALYZER_REPAIR_MAX_PREVIOUS_CHARS",
            DEFAULT_ANALYZER_REPAIR_MAX_PREVIOUS_CHARS,
        ),
        analyzer_repair_max_errors_chars=_env_int(
            "ANALYZER_REPAIR_MAX_ERRORS_CHARS",
            DEFAULT_ANALYZER_REPAIR_MAX_ERRORS_CHARS,
        ),
        analyzer_log_sample_chars=_env_int(
            "ANALYZER_LOG_SAMPLE_CHARS", DEFAULT_ANALYZER_LOG_SAMPLE_CHARS
        ),
        max_resume_chars=_env_int("MAX_RESUME_CHARS", DEFAULT_MAX_RESUME_CHARS),
        max_cv_bytes=_env_int("MAX_CV_BYTES", DEFAULT_MAX_CV_BYTES),
        output_dir=_env_str("OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
    )