import argparse
from pathlib import Path

from .cv_analyzer import CVAnalyzer
from .providers import OpenRouterProvider
from core.config import load_settings
from core.logging import setup_logging

setup_logging(level=load_settings().log_level)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-carrer-agent", description="Analyze a CV and generate a report."
    )
    parser.add_argument("resume", type=Path, help="Path to the CV file")
    args = parser.parse_args(argv)

    analysis = CVAnalyzer(provider=OpenRouterProvider()).analyze(
        args.resume.read_text(encoding="utf-8")
    )
    print(analysis.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())