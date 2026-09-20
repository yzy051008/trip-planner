"""Merge several per-batch evaluation reports into one report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .report import build_report


def merge_reports(report_paths: list[Path], generated_at: str | None = None) -> dict:
    cases: list[dict] = []
    seen_ids: set[str] = set()
    for path in report_paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for case in report.get("cases", []):
            case_id = case.get("case_id")
            if case_id and case_id in seen_ids:
                raise ValueError(f"重复的 case_id: {case_id}")
            if case_id:
                seen_ids.add(case_id)
            cases.append(case)
    return build_report(
        cases,
        generated_at or datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge evaluation reports")
    parser.add_argument("reports", nargs="+", type=Path, help="待合并的报告文件")
    parser.add_argument("--output", required=True, type=Path, help="合并后的报告文件")
    args = parser.parse_args()
    merged = merge_reports(args.reports)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        key: merged[key]
        for key in ("total_cases", "passed_cases", "failed_cases", "valid_plan_rate")
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
