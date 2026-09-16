import logging

from ..interface.search_report import SearchReport
from .adzuna_provider import AdzunaProvider
from .base_provider import JobProvider, ProviderError
from .open_ninja_provider import OpenNinjaProvider
from .remotive_provider import RemotiveProvider

logger = logging.getLogger(__name__)


def build_providers() -> list[JobProvider]:
    return [OpenNinjaProvider(), AdzunaProvider(), RemotiveProvider()]


def get_providers() -> list[JobProvider]:
    return build_providers()


def get_provider(name: str) -> JobProvider:
    for provider in build_providers():
        if provider.name == name:
            return provider
    raise ValueError(f"Unknown provider: {name}")


def search_all(
    role: str,
    location: str | None = None,
    *,
    skip_unconfigured: bool = True,
    providers: list[JobProvider] | None = None,
    **kwargs,
) -> SearchReport:
    report = SearchReport(role=role, location=location)
    if providers is None:
        providers = build_providers()
    for provider in providers:
        if skip_unconfigured and not provider.is_configured():
            report.skipped_providers[provider.name] = (
                "missing credentials: " + ", ".join(provider.config_required)
            )
            continue
        report.attempted_providers.append(provider.name)
        try:
            result = provider.search_jobs(role, location, **kwargs)
            report.jobs.extend(result.jobs)
            report.discarded_jobs[provider.name] = result.discarded_jobs
        except ProviderError as e:
            logger.error("%s failed: %s", provider.name, e)
            report.errors[provider.name] = str(e)
        except Exception as e:
            logger.exception("%s unexpected error: %s", provider.name, e)
            report.errors[provider.name] = f"Unexpected: {e}"
    return report