from app.models.schemas import (
    Attraction,
    Budget,
    CityRequest,
    CitySegment,
    DayPlan,
    Location,
    Meal,
    TripPlan,
    TripRequest,
    WeatherInfo,
)


def test_trip_plan_supports_reference_nested_data_model():
    plan = TripPlan(
        city="北京",
        start_date="2026-09-04",
        end_date="2026-09-05",
        days=[
            DayPlan(
                date="2026-09-04",
                day_index=0,
                description="历史文化之旅",
                transportation="公共交通",
                accommodation="经济型酒店",
                attractions=[
                    Attraction(
                        name="故宫",
                        address="北京市东城区",
                        location=Location(longitude=116.397, latitude=39.918),
                        visit_duration=120,
                        description="故宫博物院",
                    )
                ],
                meals=[Meal(type="lunch", name="北京菜")],
            )
        ],
        weather_info=[WeatherInfo(date="2026-09-04", day_temp="25°C")],
        overall_suggestions="提前预约",
        budget=Budget(total=500),
    )

    assert plan.days[0].attractions[0].location.longitude == 116.397
    assert plan.weather_info[0].day_temp == 25
    assert plan.budget.total == 500


def test_trip_request_has_reference_validation_rules():
    request = TripRequest(
        city="上海",
        start_date="2026-09-04",
        end_date="2026-09-05",
        travel_days=2,
        transportation="地铁",
        accommodation="酒店",
    )

    assert request.preferences == []


def test_planning_session_contracts_support_draft_versions_and_turn_types():
    from app.models.schemas import PlanningSessionResponse, PlanningTurnResponse

    response = PlanningSessionResponse(
        session_id="session-1",
        status="waiting_confirmation",
        draft_version=1,
        data=None,
    )
    turn = PlanningTurnResponse(
        type="clarify",
        message="你希望减少景点还是增加休息时间？",
        plan_changed=False,
        requires_confirmation=False,
    )

    assert response.draft_version == 1
    assert turn.type == "clarify"


def test_trip_request_accepts_multiple_city_destinations():
    request = TripRequest(
        destinations=[
            CityRequest(city="上海", start_date="2026-10-01", end_date="2026-10-03"),
            CityRequest(city="杭州", start_date="2026-10-03", end_date="2026-10-05"),
        ],
        transportation="公共交通",
        accommodation="经济型酒店",
    )

    assert [item.city for item in request.destinations] == ["上海", "杭州"]


def test_trip_plan_stores_city_segments():
    segment = CitySegment(
        city="上海",
        start_date="2026-10-01",
        end_date="2026-10-03",
    )
    plan = TripPlan(segments=[segment], start_date="2026-10-01", end_date="2026-10-03")

    assert plan.segments[0].city == "上海"
