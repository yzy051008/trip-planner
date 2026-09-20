from datetime import date, timedelta
from langchain_core.runnables import RunnableLambda

from app.agents.trip_planner_agent import (
    GraphState,
    MultiAgentTripPlanner,
    PlanningResult,
    calculate_budget,
    route_after_review,
    validate_trip_plan_hard_rules,
)
from app.models.schemas import (
    Attraction,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripRequest,
)


def make_request(traveler_count=1, budget_limit=None):
    return TripRequest(
        city="测试城市",
        start_date="2026-09-01",
        end_date="2026-09-03",
        travel_days=3,
        traveler_count=traveler_count,
        budget_limit=budget_limit,
        transportation="公共交通",
        accommodation="舒适型酒店",
        preferences=["美食"],
        free_text_input="",
    )


def make_plan():
    days = []
    for index in range(3):
        current = date(2026, 9, 1) + timedelta(days=index)
        days.append(
            DayPlan(
                date=current.isoformat(),
                day_index=index,
                description="当天行程",
                transportation="公共交通",
                accommodation="舒适型酒店",
                hotel=Hotel(name="测试酒店", estimated_cost=300),
                attractions=[
                    Attraction(
                        name="测试景点",
                        address="测试地址",
                        location=Location(longitude=121.4, latitude=31.2),
                        visit_duration=120,
                        description="测试介绍",
                        ticket_price=50,
                    )
                ],
                meals=[
                    Meal(type="breakfast", name="早餐", estimated_cost=20),
                    Meal(type="lunch", name="午餐", estimated_cost=40),
                    Meal(type="dinner", name="晚餐", estimated_cost=60),
                ],
            )
        )
    return TripPlan(
        city="测试城市",
        start_date="2026-09-01",
        end_date="2026-09-03",
        days=days,
        overall_suggestions="建议",
    )


def test_calculate_budget_uses_travelers_rooms_and_nights():
    budget = calculate_budget(make_plan(), make_request(traveler_count=3))

    assert budget.total_attractions == 450
    assert budget.total_meals == 1080
    assert budget.total_hotels == 1200
    assert budget.total_transportation == 450
    assert budget.total == 3180


def test_validate_trip_plan_reports_per_person_budget_over_limit():
    issues = validate_trip_plan_hard_rules(
        make_plan(), make_request(traveler_count=2, budget_limit=500)
    )

    assert any("人均预算" in issue for issue in issues)


def test_validate_trip_plan_allows_twenty_percent_budget_tolerance():
    issues = validate_trip_plan_hard_rules(
        make_plan(), make_request(traveler_count=2, budget_limit=800)
    )

    assert not any("人均预算" in issue for issue in issues)


def test_validate_trip_plan_reports_missing_daily_meal():
    plan = make_plan()
    plan.days[1].meals = []

    issues = validate_trip_plan_hard_rules(plan, make_request())

    assert any("第2天" in issue and "餐饮" in issue for issue in issues)


def test_review_route_ends_when_review_passes():
    state: GraphState = {
        "review_result": {
            "level": "A",
            "passed": True,
            "hard_rule_passed": True,
            "semantic_rule_passed": True,
        },
        "retry_count": 0,
        "max_retries": 3,
    }

    assert route_after_review(state) == "end"


def test_review_route_regenerates_until_three_retries():
    state: GraphState = {
        "review_result": {
            "level": "C",
            "passed": False,
            "hard_rule_passed": False,
            "semantic_rule_passed": True,
        },
        "retry_count": 2,
        "max_retries": 3,
    }

    assert route_after_review(state) == "regenerate"
    state["retry_count"] = 3
    assert route_after_review(state) == "end"


def test_planner_query_contains_budget_and_review_feedback():
    planner = object.__new__(MultiAgentTripPlanner)
    request = make_request(traveler_count=2, budget_limit=5000)
    query = planner._build_planner_query(
        request,
        {
            "attraction_pois": [],
            "hotel_pois": [],
            "weather_info": [],
            "review_feedback": "预算超出，请降低住宿费用",
        },
    )

    assert "2人" in query
    assert "5000" in query
    assert "预算超出" in query


def test_semantic_review_accepts_escaped_json_example():
    planner = object.__new__(MultiAgentTripPlanner)
    planner.llm = RunnableLambda(
        lambda _: '{"passed": true, "semantic_score": 88, "issues": [], "suggestions": [], "summary": "符合需求"}'
    )

    review = planner._semantic_review(make_request(), make_plan())

    assert review.passed is True
    assert review.semantic_score == 88
    assert review.summary == "符合需求"


def test_semantic_review_prompt_explains_per_person_budget():
    captured = {}
    planner = object.__new__(MultiAgentTripPlanner)

    def fake_review(messages):
        captured["prompt"] = "\n".join(message.content for message in messages.messages)
        return '{"passed": true, "issues": [], "suggestions": [], "summary": "符合需求"}'

    planner.llm = RunnableLambda(fake_review)
    planner._semantic_review(make_request(traveler_count=4, budget_limit=2000), make_plan())

    assert "人均预算" in captured["prompt"]
    assert "总预算 ÷ 出行人数" in captured["prompt"]
    assert "不要仅因为总预算高于人均预算上限而判定超预算" in captured["prompt"]
