"""Deterministic external-service doubles used by offline evaluation."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

try:
    from app.models.schemas import Location, POIInfo, WeatherInfo
except ModuleNotFoundError:
    from backend.app.models.schemas import Location, POIInfo, WeatherInfo


@dataclass
class MockResponse:
    content: str


class MockAmapService:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> list[POIInfo]:
        self.calls.append(("search_poi", city))
        return [
            POIInfo(
                id=f"mock-{city}-1", name=f"{city}历史博物馆", type="景点",
                address=f"{city}人民路1号", location=Location(longitude=121.47, latitude=31.23),
            ),
            POIInfo(
                id=f"mock-{city}-2", name=f"{city}城市公园", type="景点",
                address=f"{city}中山路2号", location=Location(longitude=121.48, latitude=31.24),
            ),
        ]

    def get_weather(self, city: str) -> list[WeatherInfo]:
        self.calls.append(("get_weather", city))
        return [WeatherInfo(date="2026-10-01", day_weather="晴", night_weather="多云", day_temp=25, night_temp=17)]


class MockRagService:
    def get_knowledge_attractions(self, city: str, max_names: int = 5) -> list[str]:
        return [f"{city}历史博物馆"]

    def get_attraction_rag_text(self, name: str, city: str, max_chars: int = 320) -> str:
        return f"{name}为{city}的代表性景点。"

    def build_rag_context(self, request, top_k: int = 3) -> str:
        return f"## {request.city} 本地知识\n推荐安排城市文化景点。"


class MockLLM:
    def __init__(
        self,
        responses: Iterable[str] | None = None,
        plan_response: str | None = None,
        review_response: str | None = None,
    ):
        self.responses = list(responses or [])
        self.call_count = 0
        self._last_response = ""
        self.plan_response = plan_response
        self.review_response = review_response

    def _next_response(self) -> str:
        self.call_count += 1
        if not self.responses:
            return self._last_response
        self._last_response = self.responses[0]
        return self.responses.pop(0)

    def invoke(self, payload: Any) -> MockResponse:
        if self.plan_response is not None or self.review_response is not None:
            text = str(payload)
            content = self.review_response if "旅行计划审查员" in text else self.plan_response
            if content is None:
                raise RuntimeError("MockLLM 缺少阶段响应")
            self.call_count += 1
            return MockResponse(content)
        return MockResponse(self._next_response())

    def __call__(self, payload: Any) -> MockResponse:
        return self.invoke(payload)


def plan_json(request) -> str:
    days = []
    start = date.fromisoformat(request.start_date)
    for day_index in range(request.travel_days):
        day = {
        "date": (start + timedelta(days=day_index)).isoformat(),
        "day_index": day_index,
        "description": "城市文化漫游",
        "transportation": request.transportation,
        "accommodation": request.accommodation,
        "hotel": {
            "name": f"{request.city} Mock酒店", "address": f"{request.city}中心",
            "price_range": "300-400元", "rating": "4.5", "type": request.accommodation,
            "estimated_cost": 350,
        },
        "attractions": [{
            "name": f"{request.city}历史博物馆", "address": f"{request.city}人民路1号",
            "location": {"longitude": 121.47, "latitude": 31.23}, "visit_duration": 120,
            "description": "城市历史展览", "category": "历史文化", "ticket_price": 40,
        }],
        "meals": [
            {"type": "breakfast", "name": "本地早餐", "estimated_cost": 20},
            {"type": "lunch", "name": "本地午餐", "estimated_cost": 50},
            {"type": "dinner", "name": "本地晚餐", "estimated_cost": 60},
        ],
        }
        days.append(day)
    return json.dumps({
        "city": request.city, "start_date": request.start_date, "end_date": request.end_date,
        "days": days, "weather_info": [], "overall_suggestions": "合理安排休息。",
        "budget": {"total": 0},
    }, ensure_ascii=False)


def review_json(passed: bool = True) -> str:
    return json.dumps({
        "passed": passed,
        "semantic_score": 90 if passed else 45,
        "issues": [] if passed else ["Mock审查未通过"],
        "suggestions": [],
        "summary": "Mock审查",
    }, ensure_ascii=False)
