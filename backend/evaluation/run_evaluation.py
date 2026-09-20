"""CLI for deterministic offline and explicit live Agent evaluation."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from app.agents.trip_planner_agent import MultiAgentTripPlanner, get_trip_planner_agent
    from app.core.logging_config import configure_logging
except ModuleNotFoundError:
    from backend.app.agents.trip_planner_agent import MultiAgentTripPlanner, get_trip_planner_agent
    from backend.app.core.logging_config import configure_logging

from .case_loader import load_cases
from .evaluators import evaluate_case
from .mocks import MockAmapService, MockLLM, MockRagService, plan_json, review_json
from .report import build_report


def _make_agent(case, live: bool):
    if live:
        return get_trip_planner_agent()
    llm = MockLLM(
        plan_response=plan_json(case.request),
        review_response=review_json(True),
    )
    return MultiAgentTripPlanner(
        llm=llm, amap_service=MockAmapService(), rag_service=MockRagService()
    )


def run(
    cases_path: Path,
    output_path: Path,
    live: bool = False,
    case_delay_seconds: float = 0,
) -> dict:
    configure_logging()
    cases = load_cases(cases_path)
    results = []
    for index, case in enumerate(cases):
        if index and case_delay_seconds > 0:
            time.sleep(case_delay_seconds)
        results.append(evaluate_case(case, _make_agent(case, live)))
    report = build_report(results, datetime.now(timezone.utc).isoformat())
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run trip Agent evaluation")
    parser.add_argument("--live", action="store_true", help="use real external services")
    parser.add_argument("--case-delay", type=float, default=0, help="案例之间等待秒数")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(__file__).with_name(
        "evaluation_report_live.json" if args.live else "evaluation_report_mock.json"
    )
    report = run(args.cases, output, args.live, args.case_delay)
    print(json.dumps({key: report[key] for key in ("total_cases", "passed_cases", "failed_cases", "valid_plan_rate", "average_latency_ms")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
