from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import history
from app.core.error import BizException, biz_exception_handler
from app.api.routes.history import router


def make_client():
    app = FastAPI()
    app.add_exception_handler(BizException, biz_exception_handler)
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_update_history_syncs_updated_plan_to_rag(monkeypatch):
    record = SimpleNamespace(
        id=12,
        city="上海",
        start_date="2026-09-01",
        end_date="2026-09-01",
        travel_days=1,
        transportation="步行",
        accommodation="酒店",
        preferences="[]",
        free_text_input="",
    )
    calls = []

    class FakeRag:
        def update_history_plan(self, record_id, request, plan):
            calls.append((record_id, request.city, plan.city))
            return True

    monkeypatch.setattr(history.history_service, "update_trip_record", lambda *args: record)
    monkeypatch.setattr(history, "get_rag_service", lambda: FakeRag())

    response = make_client().put(
        "/api/history/12",
        json={"city": "上海", "days": []},
    )

    assert response.status_code == 200
    assert calls == [(12, "上海", "上海")]


def test_delete_history_removes_plan_from_rag(monkeypatch):
    calls = []

    class FakeRag:
        def delete_history_plan(self, record_id):
            calls.append(record_id)
            return True

    monkeypatch.setattr(history.history_service, "delete_trip_record", lambda *args: True)
    monkeypatch.setattr(history, "get_rag_service", lambda: FakeRag())

    response = make_client().delete("/api/history/12")

    assert response.status_code == 200
    assert calls == [12]
