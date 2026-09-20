from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.history import router
from app.core.error import BizException, biz_exception_handler
from app.db.database import SessionLocal, init_db
from app.models.schemas import TripPlan, TripRequest
from app.services import history_service


def test_history_service_supports_create_list_get_update_delete():
    init_db()
    request = TripRequest(
        city="测试城市",
        start_date="2026-09-04",
        end_date="2026-09-05",
        travel_days=2,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["美食"],
        free_text_input="测试记录",
    )
    plan = TripPlan(city="测试城市", days=[])

    with SessionLocal() as db:
        record = history_service.create_trip_record(db, request, plan)
        assert record.id is not None

        records, total = history_service.list_trip_records(db, city="测试城市")
        assert total >= 1
        assert any(item.id == record.id for item in records)
        assert history_service.get_trip_record(db, record.id).id == record.id

        updated = history_service.update_trip_record(
            db,
            record.id,
            TripPlan(
                city="测试城市",
                days=[
                    {
                        "date": "2026-09-04",
                        "day_index": 0,
                        "description": "更新后的行程",
                        "transportation": "公共交通",
                        "accommodation": "经济型酒店",
                    }
                ],
            ),
        )
        assert updated is not None
        assert '"date":"2026-09-04"' in updated.plan_json

        assert history_service.delete_trip_record(db, record.id) is True
        assert history_service.get_trip_record(db, record.id) is None


def test_history_detail_returns_404_for_missing_record():
    app = FastAPI()
    app.add_exception_handler(BizException, biz_exception_handler)
    app.include_router(router, prefix="/api")

    response = TestClient(app).get("/api/history/999999999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "历史记录不存在"
    assert body["error_code"] == "BUSINESS_ERROR"
    assert body["trace_id"]
