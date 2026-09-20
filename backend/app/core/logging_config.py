"""Application logging configuration."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_trip_planner_configured", False):
        return

    # The HTTP clients log complete request URLs at INFO, which can expose
    # query-string credentials such as third-party API keys. Keep the
    # application's sanitized external_call_finished events instead.
    for logger_name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)
    root._trip_planner_configured = True
