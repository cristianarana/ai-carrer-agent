from ..interface.search_report import SearchReport
from .adzuna_provider import AdzunaProvider
from .base_provider import JobProvider, ProviderError
from .open_ninja_provider import OpenNinjaProvider
from .remotive_provider import RemotiveProvider

PROVIDERS: list[JobProvider] = [
    OpenNinjaProvider(),
    AdzunaProvider(),
    RemotiveProvider(),
]


def get_providers() -> list[JobProvider]:
    return list(PROVIDERS)


def get_provider(name: str) -> JobProvider:
    for provider in PROVIDERS:
        if provider.name == name:
            return provider
    raise ValueError(f"Unknown provider: {name}")


def search_all(role: str, location: str | None = None, **kwargs) -> SearchReport:
    report = SearchReport(role=role, location=location)
    for provider in PROVIDERS:
        report.attempted_providers.append(provider.name)
        try:
            report.jobs.extend(provider.search_jobs(role, location, **kwargs))
            report.discarded_jobs[provider.name] = list(provider.discarded_jobs)
        except ProviderError as e:
            print(f"{provider.name} failed: {e}")
            report.errors[provider.name] = str(e)
        except Exception as e:
            print(f"{provider.name} unexpected error: {e}")
            report.errors[provider.name] = f"Unexpected: {e}"
    return report