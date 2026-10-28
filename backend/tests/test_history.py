from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.history import router
from app.core.error import BizException, biz_exception_handler
from app.db.database import SessionLocal, init_db
from app.models.schemas import CitySegment, TripPlan, TripRequest
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
        assert [(item.city, item.segment_order) for item in record.segments] == [
            ("测试城市", 0)
        ]

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


def test_create_trip_record_persists_ordered_multi_city_segments():
    init_db()
    request = TripRequest(
        destinations=[
            {"city": "上海", "start_date": "2026-10-01", "end_date": "2026-10-03"},
            {"city": "杭州", "start_date": "2026-10-03", "end_date": "2026-10-05"},
            {"city": "南京", "start_date": "2026-10-06", "end_date": "2026-10-07"},
        ],
        transportation="公共交通",
        accommodation="经济型酒店",
    )
    plan = TripPlan(
        segments=[
            CitySegment(city="上海", start_date="2026-10-01", end_date="2026-10-03"),
            CitySegment(city="杭州", start_date="2026-10-03", end_date="2026-10-05"),
            CitySegment(city="南京", start_date="2026-10-06", end_date="2026-10-07"),
        ]
    )

    with SessionLocal() as db:
        record = history_service.create_trip_record(db, request, plan)
        assert [(item.city, item.segment_order) for item in record.segments] == [
            ("上海", 0),
            ("杭州", 1),
            ("南京", 2),
        ]
        assert record.segments[1].start_date == "2026-10-03"


def test_list_history_matches_any_city_in_ordered_segments():
    init_db()
    request = TripRequest(
        destinations=[
            {"city": "上海", "start_date": "2026-11-01", "end_date": "2026-11-02"},
            {"city": "杭州", "start_date": "2026-11-02", "end_date": "2026-11-04"},
        ],
        transportation="高铁",
        accommodation="经济型酒店",
    )
    plan = TripPlan(
        segments=[
            CitySegment(city="上海", start_date="2026-11-01", end_date="2026-11-02"),
            CitySegment(city="杭州", start_date="2026-11-02", end_date="2026-11-04"),
        ]
    )

    with SessionLocal() as db:
        record = history_service.create_trip_record(db, request, plan)
        records, total = history_service.list_trip_records(db, city="杭州")

        assert total >= 1
        assert record.id in [item.id for item in records]


def test_update_trip_record_replaces_segment_metadata():
    init_db()
    request = TripRequest(
        destinations=[
            {"city": "苏州", "start_date": "2026-12-01", "end_date": "2026-12-02"},
            {"city": "无锡", "start_date": "2026-12-02", "end_date": "2026-12-03"},
        ],
        transportation="公共交通",
        accommodation="经济型酒店",
    )
    original_plan = TripPlan(
        segments=[
            CitySegment(city="苏州", start_date="2026-12-01", end_date="2026-12-02"),
            CitySegment(city="无锡", start_date="2026-12-02", end_date="2026-12-03"),
        ]
    )
    updated_plan = TripPlan(
        segments=[
            CitySegment(city="苏州", start_date="2026-12-01", end_date="2026-12-02"),
            CitySegment(city="无锡", start_date="2026-12-02", end_date="2026-12-03"),
            CitySegment(city="南京", start_date="2026-12-04", end_date="2026-12-05"),
        ]
    )

    with SessionLocal() as db:
        record = history_service.create_trip_record(db, request, original_plan)
        updated = history_service.update_trip_record(db, record.id, updated_plan)

        assert updated is not None
        assert [(item.city, item.segment_order) for item in updated.segments] == [
            ("苏州", 0),
            ("无锡", 1),
            ("南京", 2),
        ]


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
