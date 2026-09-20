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


def test_agent_parses_structured_llm_json():
    from app.agents.trip_planner_agent import MultiAgentTripPlanner

    content = '{"city":"北京","start_date":"2026-09-04","end_date":"2026-09-04","days":[],"overall_suggestions":"注意预约"}'

    plan = MultiAgentTripPlanner._parse_json_response(content)

    assert plan.city == "北京"
    assert plan.days == []
