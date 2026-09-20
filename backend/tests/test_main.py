from fastapi.testclient import TestClient

from app.api.main import app


def test_main_registers_history_route():
    response = TestClient(app).get("/api/history/999999999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "历史记录不存在"
    assert body["error_code"] == "BUSINESS_ERROR"
    assert body["trace_id"] == response.headers["X-Trace-Id"]
