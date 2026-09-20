import json

from app.models.schemas import Budget, TripPlan, ReviewResult

from evaluation.case_loader import EvaluationCase
from evaluation.evaluators import evaluate_case, budget_passes_external_limit
import evaluation.evaluators as evaluators
from evaluation.report import build_report
from evaluation.merge_reports import merge_reports
import evaluation.run_evaluation as evaluation_runner


def make_case(case_id="case_001"):
    from app.models.schemas import TripRequest

    return EvaluationCase(
        case_id=case_id,
        category="normal",
        description="test",
        request=TripRequest(
            city="上海", start_date="2026-10-01", end_date="2026-10-01",
            travel_days=1, transportation="步行", accommodation="经济型酒店",
        ),
        expected={"days": 1, "must_have_meals": False},
    )


class ValidAgent:
    def plan_trip(self, request, trace_id=None):
        return TripPlan(city=request.city, days=[])


class FailingAgent:
    def plan_trip(self, request, trace_id=None):
        raise TimeoutError("mock timeout")


class ScoredAgent:
    def plan_trip(self, request, trace_id=None):
        return type("Output", (), {
            "plan": TripPlan(city=request.city, days=[]),
            "review": ReviewResult(
                passed=True, semantic_score=88, level="A", semantic_rule_passed=True
            ),
        })()


def test_evaluate_case_preserves_trace_and_handles_agent_failure():
    result = evaluate_case(make_case(), ValidAgent())
    failed = evaluate_case(make_case("case_002"), FailingAgent())

    assert result["trace_id"]
    assert result["latency_ms"] >= 0
    assert failed["passed"] is False
    assert failed["error_type"] == "TimeoutError"
    assert failed["trace_id"]


def test_report_rates_and_p95_are_recomputed_from_all_cases():
    results = [
        {"passed": True, "valid_plan": True, "hard_rule_passed": True, "budget_passed": True, "latency_ms": 10, "retry_count": 0},
        {"passed": False, "valid_plan": False, "hard_rule_passed": False, "budget_passed": False, "latency_ms": 100, "retry_count": 2},
    ]

    report = build_report(results, "2026-09-07T00:00:00+08:00")

    assert report["total_cases"] == 2
    assert report["passed_cases"] == 1
    assert report["failed_cases"] == 1
    assert report["valid_plan_rate"] == 0.5
    assert report["budget_pass_rate"] == 0.5
    assert report["p95_latency_ms"] == 100


def test_external_budget_allows_twenty_percent_tolerance():
    assert budget_passes_external_limit(600, traveler_count=1, budget_limit=500)
    assert not budget_passes_external_limit(601, traveler_count=1, budget_limit=500)


def test_external_budget_tolerance_is_per_person():
    assert budget_passes_external_limit(1200, traveler_count=2, budget_limit=500)
    assert not budget_passes_external_limit(1202, traveler_count=2, budget_limit=500)


def test_merge_reports_recalculates_summary_for_all_cases(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({"cases": [{
        "passed": True, "valid_plan": True, "hard_rule_passed": True,
        "budget_passed": True, "budget_configured": False,
        "latency_ms": 10, "retry_count": 0,
    }]}), encoding="utf-8")
    second.write_text(json.dumps({"cases": [{
        "passed": False, "valid_plan": False, "hard_rule_passed": False,
        "budget_passed": False, "budget_configured": True,
        "latency_ms": 20, "retry_count": 1,
    }]}), encoding="utf-8")

    merged = merge_reports([first, second], "2026-09-07T00:00:00+08:00")

    assert merged["total_cases"] == 2
    assert merged["passed_cases"] == 1
    assert merged["average_latency_ms"] == 15


def test_runner_waits_between_cases_when_delay_is_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(evaluation_runner, "load_cases", lambda _: [make_case("one"), make_case("two")])
    monkeypatch.setattr(evaluation_runner, "_make_agent", lambda case, live: ValidAgent())
    monkeypatch.setattr(evaluation_runner, "evaluate_case", lambda case, agent: {
        "case_id": case.case_id, "passed": True, "valid_plan": True,
        "hard_rule_passed": True, "budget_passed": True,
        "budget_configured": False, "latency_ms": 1, "retry_count": 0,
    })
    waits = []
    monkeypatch.setattr(evaluation_runner.time, "sleep", waits.append)

    evaluation_runner.run(tmp_path / "cases.jsonl", tmp_path / "report.json", case_delay_seconds=10)

    assert waits == [10]


def test_expected_negative_budget_case_passes_when_budget_is_exceeded(monkeypatch):
    case = make_case("budget_negative")
    case.request.budget_limit = 0
    case.expected.pop("days")
    case.expected.pop("must_have_meals")
    case.expected["budget_must_pass"] = False
    monkeypatch.setattr(evaluators, "calculate_budget", lambda plan, request: Budget(total=10))
    monkeypatch.setattr(
        evaluators,
        "validate_trip_plan_hard_rules",
        lambda plan, request: ["人均预算超过容差上限"],
    )

    result = evaluate_case(case, ValidAgent())

    assert result["budget_passed"] is False
    assert result["passed"] is True


def test_report_contains_category_and_error_summaries():
    results = [
        {"case_id": "a", "category": "normal", "passed": True, "valid_plan": True,
         "hard_rule_passed": True, "budget_passed": True, "budget_configured": False,
         "latency_ms": 10, "retry_count": 0, "error_type": None},
        {"case_id": "b", "category": "budget", "passed": False, "valid_plan": False,
         "hard_rule_passed": False, "budget_passed": False, "budget_configured": True,
         "latency_ms": 20, "retry_count": 1, "error_type": "TimeoutError"},
    ]

    report = build_report(results, "2026-09-07T00:00:00+08:00")

    assert report["category_stats"]["normal"]["passed_cases"] == 1
    assert report["category_stats"]["budget"]["passed_cases"] == 0
    assert report["error_counts"] == {"TimeoutError": 1}


def test_report_contains_average_semantic_score():
    results = [
        {"passed": True, "valid_plan": True, "hard_rule_passed": True,
         "budget_passed": True, "budget_configured": False, "latency_ms": 1,
         "retry_count": 0, "semantic_score": 80},
        {"passed": True, "valid_plan": True, "hard_rule_passed": True,
         "budget_passed": True, "budget_configured": False, "latency_ms": 1,
         "retry_count": 0, "semantic_score": 90},
        {"passed": False, "valid_plan": False, "hard_rule_passed": False,
         "budget_passed": True, "budget_configured": False, "latency_ms": 1,
         "retry_count": 0, "semantic_score": None},
    ]

    report = build_report(results, "2026-09-07T00:00:00+08:00")

    assert report["average_semantic_score"] == 85


def test_evaluation_copies_llm_semantic_score(monkeypatch):
    case = make_case("scored")
    case.expected.pop("days")
    case.expected.pop("must_have_meals")
    monkeypatch.setattr(evaluators, "validate_trip_plan_hard_rules", lambda plan, request: [])

    result = evaluate_case(case, ScoredAgent())

    assert result["semantic_score"] == 88
