from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.api.main import app


def test_trip_plan_route_calls_agent_and_returns_plan(monkeypatch):
    from app.api.routes import trip

    class FakeAgent:
        def plan_trip(self, request, trace_id=None):
            return {
                "city": request.city,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "days": [],
                "weather_info": [],
                "overall_suggestions": "测试建议",
                "budget": {"total": 0},
            }

    class FakeRag:
        def add_history_plan(self, record_id, request, plan):
            return True

    monkeypatch.setattr(trip, "get_trip_planner_agent", lambda: FakeAgent())
    monkeypatch.setattr(trip, "get_rag_service", lambda: FakeRag())

    payload = {
        "city": "测试城市",
        "start_date": "2026-09-04",
        "end_date": "2026-09-04",
        "travel_days": 1,
        "transportation": "步行",
        "accommodation": "酒店",
        "preferences": [],
        "free_text_input": "",
    }
    response = TestClient(app).post("/api/trip/plan", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["id"] > 0
    assert response.json()["data"]["segments"][0]["city"] == "测试城市"
    assert response.json()["review"]["level"] == "A"


def test_history_persistence_failure_still_returns_plan_with_null_id(monkeypatch):
    from app.api.routes import trip

    class FakeAgent:
        def plan_trip(self, request, trace_id=None):
            return {"city": request.city, "days": []}

    def fail_persist(db, request, plan):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(trip, "get_trip_planner_agent", lambda: FakeAgent())
    monkeypatch.setattr(trip.history_service, "create_trip_record", fail_persist)

    response = TestClient(app).post(
        "/api/trip/plan",
        json={
            "city": "测试城市", "start_date": "2026-09-04", "end_date": "2026-09-04",
            "travel_days": 1, "transportation": "步行", "accommodation": "酒店",
            "preferences": [], "free_text_input": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] is None
    assert response.json()["data"]["segments"][0]["city"] == "测试城市"


def test_rag_sync_failure_still_returns_persisted_plan(monkeypatch):
    from app.api.routes import trip

    class FakeAgent:
        def plan_trip(self, request, trace_id=None):
            return {"city": request.city, "days": []}

    class FailingRag:
        def add_history_plan(self, record_id, request, plan):
            raise RuntimeError("rag unavailable")

    monkeypatch.setattr(trip, "get_trip_planner_agent", lambda: FakeAgent())
    monkeypatch.setattr(
        trip.history_service,
        "create_trip_record",
        lambda db, request, plan: SimpleNamespace(id=42),
    )
    monkeypatch.setattr(trip, "get_rag_service", lambda: FailingRag())

    response = TestClient(app).post(
        "/api/trip/plan",
        json={
            "city": "测试城市", "start_date": "2026-09-04", "end_date": "2026-09-04",
            "travel_days": 1, "transportation": "步行", "accommodation": "酒店",
            "preferences": [], "free_text_input": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == 42
    assert response.json()["data"]["segments"][0]["city"] == "测试城市"
