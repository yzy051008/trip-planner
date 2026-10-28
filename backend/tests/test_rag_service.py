from types import SimpleNamespace

from app.models.schemas import CitySegment, DayPlan, TripPlan, TripRequest
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


def test_plan_to_text_keeps_city_boundaries_for_multi_city_trip():
    request = TripRequest(
        destinations=[
            {"city": "上海", "start_date": "2026-09-04", "end_date": "2026-09-05"},
            {"city": "杭州", "start_date": "2026-09-05", "end_date": "2026-09-06"},
        ],
        transportation="高铁",
        accommodation="经济型酒店",
    )
    plan = TripPlan(
        segments=[
            CitySegment(
                city="上海",
                start_date="2026-09-04",
                end_date="2026-09-05",
                days=[
                    DayPlan(
                        date="2026-09-04",
                        day_index=0,
                        description="外滩行程",
                        transportation="地铁",
                        accommodation="酒店",
                    )
                ],
            ),
            CitySegment(
                city="杭州",
                start_date="2026-09-05",
                end_date="2026-09-06",
                days=[
                    DayPlan(
                        date="2026-09-05",
                        day_index=1,
                        description="西湖行程",
                        transportation="步行",
                        accommodation="酒店",
                    )
                ],
            ),
        ]
    )

    text = RagService._plan_to_text(request, plan)

    assert "上海、杭州 3天旅行计划" in text
    assert "## 上海" in text
    assert "## 杭州" in text
    assert "外滩行程" in text
    assert "西湖行程" in text


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


def test_build_rag_context_retrieves_knowledge_for_each_city(monkeypatch):
    service = RagService.__new__(RagService)
    service._embedding = object()
    calls = []

    def fake_retrieve(query, city=None, k=3):
        calls.append((query, city, k))
        return [f"{city}知识"] if city else []

    monkeypatch.setattr(service, "retrieve", fake_retrieve)
    request = TripRequest(
        destinations=[
            {"city": "上海", "start_date": "2026-09-04", "end_date": "2026-09-05"},
            {"city": "杭州", "start_date": "2026-09-05", "end_date": "2026-09-06"},
        ],
        transportation="高铁",
        accommodation="酒店",
    )

    context = service.build_rag_context(request)

    assert [call[1] for call in calls] == ["上海", "杭州"]
    assert "上海知识" in context
    assert "杭州知识" in context
