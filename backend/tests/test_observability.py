from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.api.main import app


def test_every_response_contains_trace_id_header():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Trace-Id")


def test_validation_error_contains_trace_id_and_error_code():
    response = TestClient(app).post("/api/trip/plan", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_business_error_contains_trace_id_and_error_code():
    response = TestClient(app).get("/api/history/999999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "BUSINESS_ERROR"
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_agent_receives_the_request_trace_id(monkeypatch):
    from app.agents import trip_planner_agent
    from app.models.schemas import ReviewResult, TripPlan, TripRequest

    captured = {}

    class FakeGraph:
        def invoke(self, state):
            captured.update(state)
            return {
                "trip_plan": TripPlan(city="测试", days=[]),
                "review_result": ReviewResult(level="A", passed=True),
            }

    planner = object.__new__(trip_planner_agent.MultiAgentTripPlanner)
    planner.graph = FakeGraph()
    monkeypatch.setattr(
        trip_planner_agent,
        "get_rag_service",
        lambda: SimpleNamespace(get_attraction_rag_text=lambda *args: None),
        raising=False,
    )

    request = TripRequest(
        city="测试", start_date="2026-09-07", end_date="2026-09-07",
        travel_days=1, transportation="步行", accommodation="酒店",
    )
    planner.plan_trip(request, trace_id="trace-fixed")

    assert captured["trace_id"] == "trace-fixed"


def test_failed_graph_node_logs_trace_node_and_elapsed(caplog):
    from app.agents.trip_planner_agent import MultiAgentTripPlanner

    class FailingAmap:
        def get_weather(self, city):
            raise TimeoutError("weather timeout")

    planner = object.__new__(MultiAgentTripPlanner)
    planner.amap_service = FailingAmap()

    with caplog.at_level("INFO"):
        try:
            planner._get_weather({"request": SimpleNamespace(city="测试"), "trace_id": "trace-node"})
        except TimeoutError:
            pass

    messages = [record.getMessage() for record in caplog.records]
    assert any("node_started" in message and "trace-node" in message for message in messages)
    assert any("node_failed" in message and "get_weather" in message and "TimeoutError" in message for message in messages)
    assert any("elapsed_ms=" in message for message in messages)


def test_weather_prompt_does_not_invent_unavailable_forecast():
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import WeatherInfo

    text = MultiAgentTripPlanner._weather_to_text([
        WeatherInfo(date="2026-09-10", forecast_available=False, day_weather="暂无预报")
    ])

    assert text == "2026-09-10: 暂无预报，不要推测天气"


def test_llm_parse_retry_and_completion_are_logged(caplog):
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import TripRequest

    class Response:
        def __init__(self, content):
            self.content = content

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def invoke(self, payload):
            self.calls += 1
            if self.calls == 1:
                return Response("not json")
            return Response('{"city":"测试","days":[]}')

        def __call__(self, payload):
            return self.invoke(payload)

    planner = object.__new__(MultiAgentTripPlanner)
    planner.llm = FakeLLM()
    planner._build_planner_query = lambda request, state: "query"
    request = TripRequest(
        city="测试", start_date="2026-09-07", end_date="2026-09-07",
        travel_days=1, transportation="步行", accommodation="酒店",
    )

    with caplog.at_level("INFO"):
        result = planner._generate_trip_plan({
            "request": request, "trace_id": "trace-llm"
        })

    messages = [record.getMessage() for record in caplog.records]
    assert result["trip_plan"].city == "测试"
    assert any("llm_parse_retry" in message and "trace-llm" in message for message in messages)
    assert any("llm_finished" in message and "attempt=2" in message for message in messages)


def test_review_completion_is_logged(caplog):
    from app.agents.trip_planner_agent import MultiAgentTripPlanner
    from app.models.schemas import ReviewResult, TripPlan, TripRequest

    planner = object.__new__(MultiAgentTripPlanner)
    planner._semantic_review = lambda request, plan: ReviewResult(
        level="A", passed=True, hard_rule_passed=True, semantic_rule_passed=True
    )
    request = TripRequest(
        city="测试", start_date="2026-09-07", end_date="2026-09-07",
        travel_days=1, transportation="步行", accommodation="酒店",
    )

    with caplog.at_level("INFO"):
        planner._review_trip_plan({
            "request": request,
            "trip_plan": TripPlan(city="测试", days=[]),
            "trace_id": "trace-review",
            "retry_count": 0,
            "max_retries": 3,
        })

    assert any(
        "review_finished" in record.getMessage() and "trace-review" in record.getMessage()
        for record in caplog.records
    )


def test_graph_state_declares_trace_id():
    from app.agents.trip_planner_agent import GraphState

    assert "trace_id" in GraphState.__annotations__
