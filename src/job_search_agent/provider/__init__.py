import logging

from core.config import Settings
from ..interface.search_report import SearchReport
from .adzuna_provider import AdzunaProvider
from .base_provider import JobProvider, ProviderError
from .open_ninja_provider import OpenNinjaProvider
from .remotive_provider import RemotiveProvider

logger = logging.getLogger(__name__)


def build_providers(settings: Settings | None = None) -> list[JobProvider]:
    if settings is None:
        return [OpenNinjaProvider(), AdzunaProvider(), RemotiveProvider()]
    network = {
        "timeout": settings.search_provider_timeout,
        "retries": settings.search_provider_retries,
        "backoff": settings.search_provider_backoff,
    }
    return [
        OpenNinjaProvider(
            num_pages=settings.open_ninja_num_pages,
            min_interval_seconds=settings.search_provider_min_interval,
            **network,
        ),
        AdzunaProvider(
            results_per_page=settings.adzuna_results_per_page,
            min_interval_seconds=settings.adzuna_min_interval,
            **network,
        ),
        RemotiveProvider(
            min_interval_seconds=settings.search_provider_min_interval,
            **network,
        ),
    ]


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
            logger.info(
                "job search ok provider=%s role=%r location=%s jobs=%d discarded=%d",
                provider.name,
                role,
                location,
                len(result.jobs),
                len(result.discarded_jobs),
            )
        except ProviderError as e:
            logger.error("%s failed: %s", provider.name, e)
            report.errors[provider.name] = str(e)
            logger.info(
                "job search failed provider=%s role=%r location=%s error=%s",
                provider.name,
                role,
                location,
                e,
            )
        except Exception as e:
            logger.exception("%s unexpected error: %s", provider.name, e)
            report.errors[provider.name] = f"Unexpected: {e}"
            logger.info(
                "job search unexpected provider=%s role=%r location=%s error=%s",
                provider.name,
                role,
                location,
                e,
            )
    logger.info(
        "job search end role=%r location=%s providers=%s failed=%s skipped=%s",
        role,
        location,
        list(report.attempted_providers),
        list(report.errors),
        list(report.skipped_providers),
    )
    return report