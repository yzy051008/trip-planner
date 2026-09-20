"""Evaluation report aggregation."""

import math
from collections import Counter, defaultdict


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build_report(results: list[dict], generated_at: str) -> dict:
    total = len(results)
    latencies = sorted(int(item.get("latency_ms", 0)) for item in results)
    budget_results = [item for item in results if item.get("budget_configured", True)]
    p95 = latencies[max(math.ceil(len(latencies) * 0.95) - 1, 0)] if latencies else 0
    category_buckets = defaultdict(list)
    for item in results:
        category_buckets[item.get("category", "unknown")].append(item)
    category_stats = {}
    for category, items in sorted(category_buckets.items()):
        category_total = len(items)
        category_passed = sum(bool(item.get("passed")) for item in items)
        category_stats[category] = {
            "total_cases": category_total,
            "passed_cases": category_passed,
            "failed_cases": category_total - category_passed,
            "pass_rate": _rate(category_passed, category_total),
        }
    error_counts = dict(sorted(Counter(
        item["error_type"] for item in results if item.get("error_type")
    ).items()))
    semantic_scores = [
        float(item["semantic_score"])
        for item in results
        if isinstance(item.get("semantic_score"), (int, float))
        and not isinstance(item.get("semantic_score"), bool)
    ]
    return {
        "generated_at": generated_at,
        "total_cases": total,
        "passed_cases": sum(bool(item.get("passed")) for item in results),
        "failed_cases": sum(not item.get("passed", False) for item in results),
        "valid_plan_rate": _rate(sum(bool(item.get("valid_plan")) for item in results), total),
        "hard_constraint_pass_rate": _rate(sum(bool(item.get("hard_rule_passed")) for item in results), total),
        "budget_pass_rate": _rate(sum(bool(item.get("budget_passed")) for item in budget_results), len(budget_results)),
        "average_latency_ms": round(sum(latencies) / total, 2) if total else 0,
        "p95_latency_ms": p95,
        "average_retry_count": round(sum(item.get("retry_count", 0) for item in results) / total, 2) if total else 0,
        "final_failure_rate": _rate(sum(not item.get("valid_plan", False) for item in results), total),
        "average_semantic_score": (
            round(sum(semantic_scores) / len(semantic_scores), 2)
            if semantic_scores else None
        ),
        "category_stats": category_stats,
        "error_counts": error_counts,
        "cases": results,
    }
