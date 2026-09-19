import logging
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(
    *, level: int | str | None = None, log_dir: Path | None = None
) -> None:
    if level is None:
        level = logging.INFO
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logs_dir = log_dir or _LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(logs_dir / "api.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        handlers=handlers,
        force=True,
    )