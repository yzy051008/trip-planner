import logging

from app.core.logging_config import configure_logging
from tools.view_logs import read_log_entries


def test_http_clients_do_not_emit_info_request_urls():
    configure_logging()

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpx2").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING


def test_log_viewer_returns_latest_event_first(tmp_path):
    path = tmp_path / "app.log"
    path.write_text(
        "2026-09-07 10:00:00,000 INFO old event\n"
        "2026-09-07 10:01:00,000 INFO new event\n",
        encoding="utf-8",
    )

    entries = read_log_entries(path)

    assert entries[0].endswith("new event")
    assert entries[1].endswith("old event")
