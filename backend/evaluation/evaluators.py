"""Per-case evaluation rules."""

import time

try:
    from app.agents.trip_planner_agent import (
        budget_passes_limit,
        calculate_budget,
        validate_trip_plan_hard_rules,
    )
    from app.models.schemas import TripPlan
    from app.core.trace import new_trace_id
except ModuleNotFoundError:
    from backend.app.agents.trip_planner_agent import (
        budget_passes_limit,
        calculate_budget,
        validate_trip_plan_hard_rules,
    )
    from backend.app.models.schemas import TripPlan
    from backend.app.core.trace import new_trace_id


def budget_passes_external_limit(
    total_budget: int, traveler_count: int, budget_limit: int
) -> bool:
    """兼容旧调用名，使用与 Agent 相同的预算口径。"""
    return budget_passes_limit(total_budget, traveler_count, budget_limit)


def _is_budget_issue(issue: str) -> bool:
    return "预算" in issue or "budget" in issue.lower()


def evaluate_case(case, agent) -> dict:
    trace_id = new_trace_id()
    started = time.perf_counter()
    result = {
        "case_id": case.case_id,
        "category": case.category,
        "passed": False,
        "valid_plan": False,
        "hard_rule_passed": False,
        "budget_passed": case.request.budget_limit is None,
        "budget_configured": case.request.budget_limit is not None,
        "budget_expected": case.expected.get("budget_must_pass"),
        "semantic_score": None,
        "latency_ms": 0,
        "retry_count": 0,
        "llm_call_count": None,
        "trace_id": trace_id,
        "review_level": None,
        "issues": [],
        "error_type": None,
    }
    try:
        output = agent.plan_trip(case.request, trace_id=trace_id)
        plan = output.plan if hasattr(output, "plan") else TripPlan.model_validate(output)
        result["valid_plan"] = True
        plan.budget = calculate_budget(plan, case.request)
        hard_issues = validate_trip_plan_hard_rules(plan, case.request)
        expected = case.expected
        if expected.get("city") and plan.city != expected["city"]:
            hard_issues.append(f"城市不符合 expected: {expected['city']}")
        if expected.get("days") is not None and len(plan.days) != expected["days"]:
            hard_issues.append(f"天数不符合 expected: {expected['days']}")
        if expected.get("must_have_meals"):
            for day in plan.days:
                if {"breakfast", "lunch", "dinner"} - {meal.type for meal in day.meals}:
                    hard_issues.append(f"第{day.day_index + 1}天餐饮不完整")
        actual_budget_passed = (
            case.request.budget_limit is None
            or budget_passes_external_limit(
                plan.budget.total,
                case.request.traveler_count,
                case.request.budget_limit,
            )
        )
        result["budget_passed"] = actual_budget_passed
        expected_budget_passed = case.expected.get("budget_must_pass")
        budget_expectation_passed = (
            expected_budget_passed is None
            or actual_budget_passed == expected_budget_passed
        )
        expected_negative_budget = expected_budget_passed is False
        if expected_negative_budget and not actual_budget_passed:
            hard_issues = [issue for issue in hard_issues if not _is_budget_issue(issue)]
        result["hard_rule_passed"] = not hard_issues
        review = output.review if hasattr(output, "review") else None
        review_passed = review is None or review.passed
        if review is not None:
            result["retry_count"] = review.retry_count
            result["review_level"] = review.level
            result["semantic_score"] = review.semantic_score
            result["issues"].extend(review.issues)
            if (
                expected_negative_budget
                and not actual_budget_passed
                and not review.passed
                and review.issues
                and all(_is_budget_issue(issue) for issue in review.issues)
            ):
                review_passed = True
        result["issues"] = hard_issues + result["issues"]
        result["passed"] = (
            result["valid_plan"]
            and result["hard_rule_passed"]
            and budget_expectation_passed
            and review_passed
        )
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["issues"].append(str(exc))
    finally:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        call_count = getattr(getattr(agent, "llm", None), "call_count", None)
        result["llm_call_count"] = call_count
    return result
