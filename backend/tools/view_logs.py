"""Display application logs with the newest event first."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


_LOG_START = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ")


def read_log_entries(path: Path) -> list[str]:
    """Read complete log events and return them newest-first.

    Continuation lines (for example, exception tracebacks) stay attached to
    the log record that produced them.
    """

    entries: list[str] = []
    current: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if _LOG_START.match(line):
            if current:
                entries.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
        elif line:
            # Preserve non-standard preamble lines rather than silently
            # dropping them.
            current = [line]
    if current:
        entries.append("\n".join(current))
    return list(reversed(entries))


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Show app.log newest-first")
    parser.add_argument(
        "--log-file",
        type=Path,
        default=project_root / "backend" / "logs" / "app.log",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多显示多少条事件，0 表示全部")
    args = parser.parse_args()

    entries = read_log_entries(args.log_file)
    if args.limit > 0:
        entries = entries[: args.limit]
    if entries:
        print("\n".join(entries))


if __name__ == "__main__":
    main()
