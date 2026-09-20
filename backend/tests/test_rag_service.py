from types import SimpleNamespace

from app.models.schemas import DayPlan, TripPlan, TripRequest
from app.services.rag_service import RagService


def test_plan_to_text_creates_searchable_trip_summary():
    request = TripRequest(
        city="北京",
        start_date="2026-09-04",
        end_date="2026-09-05",
        travel_days=2,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化"],
    )
    plan = TripPlan(
        city="北京",
        days=[
            DayPlan(
                date="2026-09-04",
                day_index=0,
                description="历史文化之旅",
                transportation="公共交通",
                accommodation="经济型酒店",
            )
        ],
    )

    text = RagService._plan_to_text(request, plan)

    assert "北京 2天旅行计划" in text
    assert "交通: 公共交通" in text
    assert "第1天:" in text


def test_disabled_rag_returns_safe_empty_results():
    service = RagService.__new__(RagService)
    service._embedding = None

    request = SimpleNamespace(city="北京", travel_days=2, preferences=[], free_text_input="")

    assert service.enabled is False
    assert service.retrieve("故宫") == []
    assert service.build_rag_context(request) == ""
    assert service.get_knowledge_attractions("北京") == []
    assert service.get_attraction_rag_text("故宫", "北京") == ""
    assert service.add_history_plan(1, request, SimpleNamespace()) is False
