from types import SimpleNamespace

from app.models.schemas import TripRequest


def test_agent_accepts_injected_external_dependencies(monkeypatch):
    from app.agents import trip_planner_agent

    llm = object()
    amap = object()
    rag = object()
    monkeypatch.setattr(trip_planner_agent, "get_llm", lambda: (_ for _ in ()).throw(AssertionError("factory called")))
    monkeypatch.setattr(trip_planner_agent, "get_amap_service", lambda: (_ for _ in ()).throw(AssertionError("factory called")))

    planner = trip_planner_agent.MultiAgentTripPlanner(
        llm=llm, amap_service=amap, rag_service=rag
    )

    assert planner.llm is llm
    assert planner.amap_service is amap
    assert planner.rag_service is rag


def test_agent_graph_does_not_contain_fallback_node(monkeypatch):
    from app.agents import trip_planner_agent

    monkeypatch.setattr(trip_planner_agent, "get_llm", lambda: object())
    monkeypatch.setattr(
        trip_planner_agent,
        "get_amap_service",
        lambda: SimpleNamespace(),
    )

    planner = trip_planner_agent.MultiAgentTripPlanner()

    assert "fallback_plan" not in planner.get_agent_info()["nodes"]
    assert not hasattr(planner, "_fallback_plan")


def test_agent_collects_data_and_transport_for_three_destinations():
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import CityRequest, Location, POIInfo, WeatherInfo

    class FakeAmap:
        def search_poi(self, keywords, city):
            return [POIInfo(
                id=city,
                name=f"{city}景点",
                type="景点",
                address=f"{city}地址",
                location=Location(longitude=121.4, latitude=31.2),
            )]

        def get_weather(self, city, start_date, end_date):
            return [WeatherInfo(date=start_date, day_weather="晴")]

        def plan_route(self, origin, destination, **kwargs):
            return {"duration": 3600, "cost": 100}

    class FakeRag:
        def get_knowledge_attractions(self, city):
            return []

    request = TripRequest(
        destinations=[
            CityRequest(city="上海", start_date="2026-10-01", end_date="2026-10-02"),
            CityRequest(city="杭州", start_date="2026-10-02", end_date="2026-10-03"),
            CityRequest(city="南京", start_date="2026-10-03", end_date="2026-10-04"),
        ],
        transportation="公共交通",
        accommodation="酒店",
    )
    planner = MultiAgentTripPlanner(llm=object(), amap_service=FakeAmap(), rag_service=FakeRag())
    state = {"request": request, "trace_id": "trace-multi"}

    state.update(planner._search_attractions(state))
    state.update(planner._get_weather(state))
    state.update(planner._search_hotels(state))
    state.update(planner._search_intercity_transport(state))

    assert [item["city"] for item in state["city_data"]] == ["上海", "杭州", "南京"]
    assert len(state["transport_data"]) == 2


def test_agent_parses_structured_llm_json():
    from app.agents.trip_planner_agent import MultiAgentTripPlanner

    content = '{"city":"北京","start_date":"2026-09-04","end_date":"2026-09-04","days":[],"overall_suggestions":"注意预约"}'

    plan = MultiAgentTripPlanner._parse_json_response(content)

    assert plan.city == "北京"
    assert plan.days == []
