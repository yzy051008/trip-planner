from app.models.schemas import (
    Attraction,
    Budget,
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
