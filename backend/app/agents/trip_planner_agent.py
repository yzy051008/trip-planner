"""基于 LangGraph 的旅行规划 Agent。"""

import json
import logging
import re
import time
from contextlib import contextmanager
from datetime import date, timedelta
from math import ceil
from dataclasses import dataclass
from typing import Optional, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from ..models.schemas import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    POIInfo,
    TripPlan,
    TripRequest,
    TransportSegment,
    WeatherInfo,
    ReviewResult,
)
from ..services.amap_service import get_amap_service
from ..services.llm_service import get_llm


logger = logging.getLogger(__name__)
BUDGET_TOLERANCE = 1.2


def budget_passes_limit(total_budget: int, traveler_count: int, budget_limit: int) -> bool:
    """统一按人均预算上限的 120% 判断预算是否通过。"""
    return total_budget / traveler_count <= budget_limit * BUDGET_TOLERANCE


PLANNER_SYSTEM_PROMPT = """你是专业的行程规划专家。根据用户提供的多个城市片段、景点、天气、酒店和城市间交通信息, 生成详细的旅行计划。

**输出要求:**
必须只输出一个 JSON 对象, 不要输出任何其他文字, JSON 结构严格如下:
{{
  "segments": [
    {{
      "city": "城市名称",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "transport_from_previous": null,
      "days": [
        {{
          "date": "YYYY-MM-DD",
          "day_index": 0,
          "description": "当天行程概述",
          "transportation": "交通方式",
          "accommodation": "住宿类型",
          "hotel": {{"name": "酒店名称", "address": "酒店地址", "price_range": "300-500元", "estimated_cost": 400}},
          "attractions": [],
          "meals": []
        }}
      ],
      "weather_info": []
    }}
  ],
  "overall_suggestions": "总体建议",
  "budget": {{
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }}
}}

**规则:**
1. segments 必须按照用户请求的城市顺序生成, 每个城市单独一个 segment
2. 每天安排2-3个景点, 考虑景点之间的距离和游览时间
3. 每天必须包含早中晚三餐(breakfast/lunch/dinner)
4. 每天推荐一个具体的酒店(从当前城市提供的酒店信息中选择)
5. 当前城市的 weather_info 中按日期填入对应天气；没有天气数据的日期保留“暂无预报”，不得编造天气
6. 景点的经纬度坐标必须使用提供的真实坐标
7. 所有费用字段填写合理估算值, budget 为所有城市各项费用汇总
"""



class GraphState(TypedDict, total=False):
    trace_id: str
    request: TripRequest
    city_data: list[dict]
    transport_data: list[TransportSegment]
    trip_plan: TripPlan
    retry_count: int
    max_retries: int
    review_result: ReviewResult
    review_feedback: str
    current_draft: TripPlan
    conversation_context: str


@dataclass
class PlanningResult:
    plan: TripPlan
    review: ReviewResult


def calculate_budget(plan: TripPlan, request: TripRequest) -> Budget:
    """根据行程明细统一计算多人旅行的总预算。"""
    travelers = request.traveler_count
    nights = max(request.travel_days - len(request.destinations), 0)
    rooms = ceil(travelers / 2)
    attractions = sum(
        attraction.ticket_price for day in plan.days for attraction in day.attractions
    ) * travelers
    meals = sum(meal.estimated_cost for day in plan.days for meal in day.meals) * travelers
    hotel_per_night = next(
        (
            day.hotel.estimated_cost
            for day in plan.days
            if day.hotel and day.hotel.estimated_cost
        ),
        0,
    )
    hotels = hotel_per_night * nights * rooms
    transportation = 50 * request.travel_days * travelers
    intercity_transport = sum(
        segment.estimated_cost for segment in plan.segments
        if segment.transport_from_previous
    ) * travelers
    transportation += intercity_transport
    return Budget(
        total_attractions=attractions,
        total_hotels=hotels,
        total_meals=meals,
        total_transportation=transportation,
        total=attractions + hotels + meals + transportation,
    )


def validate_trip_plan_hard_rules(plan: TripPlan, request: TripRequest) -> list[str]:
    """检查不应交给 LLM 判断的结构、日期和预算硬约束。"""
    issues: list[str] = []
    expected_cities = [destination.city for destination in request.destinations]
    actual_cities = [segment.city for segment in plan.segments]
    if actual_cities != expected_cities:
        issues.append(f"目的地城市顺序或数量不匹配，应为{expected_cities}")

    actual_unique_dates = {day.date for segment in plan.segments for day in segment.days}
    if len(actual_unique_dates) != request.travel_days:
        issues.append(f"行程天数不匹配，应为{request.travel_days}天")

    for index, destination in enumerate(request.destinations):
        if index >= len(plan.segments):
            issues.append(f"缺少{destination.city}的行程片段")
            continue
        segment = plan.segments[index]
        if segment.start_date != destination.start_date or segment.end_date != destination.end_date:
            issues.append(f"{destination.city}片段日期与用户请求不匹配")
        expected_start = date.fromisoformat(destination.start_date)
        expected_end = date.fromisoformat(destination.end_date)
        expected_days = (expected_end - expected_start).days + 1
        if len(segment.days) != expected_days:
            issues.append(f"{destination.city}行程天数不匹配，应为{expected_days}天")
        for day_index, day in enumerate(segment.days):
            expected_date = expected_start + timedelta(days=day_index)
            if day.date != expected_date.isoformat():
                issues.append(f"{destination.city}第{day_index + 1}天日期不连续")
            if not day.attractions:
                issues.append(f"{destination.city}第{day_index + 1}天没有景点")
            if day.hotel is None:
                issues.append(f"{destination.city}第{day_index + 1}天没有住宿")
            meal_types = {meal.type for meal in day.meals}
            missing_meals = {"breakfast", "lunch", "dinner"} - meal_types
            if missing_meals:
                issues.append(f"{destination.city}第{day_index + 1}天餐饮安排不完整")
            for attraction in day.attractions:
                if not attraction.name or not attraction.address:
                    issues.append(f"{destination.city}第{day_index + 1}天存在景点信息不完整")
                if not attraction.location:
                    issues.append(f"{destination.city}第{day_index + 1}天存在景点坐标缺失")

    for previous, current in zip(plan.segments, plan.segments[1:]):
        previous_end = date.fromisoformat(previous.end_date)
        current_start = date.fromisoformat(current.start_date)
        if current_start not in (previous_end, previous_end + timedelta(days=1)):
            issues.append(f"{previous.city}与{current.city}之间的日期不连续")

    if request.budget_limit is not None:
        budget = calculate_budget(plan, request)
        per_person = budget.total / request.traveler_count
        if not budget_passes_limit(
            budget.total, request.traveler_count, request.budget_limit
        ):
            issues.append(
                f"人均预算超过容差上限 {round(per_person - request.budget_limit * BUDGET_TOLERANCE)} 元"
            )
    return issues


def route_after_review(state: GraphState) -> str:
    review = state.get("review_result")
    passed = review.get("passed", False) if isinstance(review, dict) else bool(review and review.passed)
    if passed:
        return "end"
    if state.get("retry_count", 0) < state.get("max_retries", 3):
        return "regenerate"
    return "end"


class MultiAgentTripPlanner:
    def __init__(self, llm=None, amap_service=None, rag_service=None):
        self.llm = llm if llm is not None else get_llm()
        self.amap_service = amap_service if amap_service is not None else get_amap_service()
        self.rag_service = rag_service
        self.graph = self._build_graph()

    def _get_rag_service(self):
        if self.rag_service is None:
            from ..services.rag_service import get_rag_service

            self.rag_service = get_rag_service()
        return self.rag_service

    @staticmethod
    @contextmanager
    def _logged_node(node: str, trace_id: str):
        started = time.perf_counter()
        logger.info("node_started trace_id=%s node=%s", trace_id, node)
        try:
            yield
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            logger.exception(
                "node_failed trace_id=%s node=%s elapsed_ms=%s error_type=%s",
                trace_id, node, elapsed_ms, type(exc).__name__,
            )
            raise
        else:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            logger.info(
                "node_finished trace_id=%s node=%s elapsed_ms=%s",
                trace_id, node, elapsed_ms,
            )

    def _search_attractions(self, state: GraphState) -> dict:
        request = state["request"]
        trace_id = state.get("trace_id", "unknown")
        with self._logged_node("search_attractions", trace_id):
            self.amap_service.trace_id = trace_id
            city_data = []
            for destination in request.destinations:
                keywords = destination.preferences[0] if destination.preferences else (
                    request.preferences[0] if request.preferences else "景点"
                )
                pois = self.amap_service.search_poi(keywords, destination.city)
                try:
                    known_names = {poi.name for poi in pois if poi.name}
                    for name in self._get_rag_service().get_knowledge_attractions(destination.city):
                        if any(name in current_name for current_name in known_names):
                            continue
                        knowledge_pois = self.amap_service.search_poi(name, destination.city)
                        if knowledge_pois:
                            pois.append(knowledge_pois[0])
                            known_names.add(knowledge_pois[0].name)
                except Exception as exc:
                    logger.exception(
                        "rag_retrieve_failed trace_id=%s city=%s error_type=%s",
                        trace_id, destination.city, type(exc).__name__,
                    )
                city_data.append({"city": destination.city, "attraction_pois": pois})
            return {"city_data": city_data}

    def _get_weather(self, state: GraphState) -> dict:
        with self._logged_node("get_weather", state.get("trace_id", "unknown")):
            self.amap_service.trace_id = state.get("trace_id", "unknown")
            request = state["request"]
            city_data = list(state.get("city_data", []))
            if not hasattr(request, "destinations"):
                weather = self.amap_service.get_weather(request.city)
                return {"weather_info": weather}
            for item, destination in zip(city_data, request.destinations):
                item["weather_info"] = self.amap_service.get_weather(
                    destination.city, destination.start_date, destination.end_date
                )
            return {"city_data": city_data}

    def _search_hotels(self, state: GraphState) -> dict:
        request = state["request"]
        with self._logged_node("search_hotels", state.get("trace_id", "unknown")):
            self.amap_service.trace_id = state.get("trace_id", "unknown")
            city_data = list(state.get("city_data", []))
            for item, destination in zip(city_data, request.destinations):
                item["hotel_pois"] = self.amap_service.search_poi(
                    request.accommodation, destination.city
                )
            return {"city_data": city_data}

    def _search_intercity_transport(self, state: GraphState) -> dict:
        request = state["request"]
        trace_id = state.get("trace_id", "unknown")
        with self._logged_node("search_intercity_transport", trace_id):
            self.amap_service.trace_id = trace_id
            transport_data = []
            for previous, current in zip(request.destinations, request.destinations[1:]):
                route = self.amap_service.plan_route(
                    previous.city,
                    current.city,
                    origin_city=previous.city,
                    destination_city=current.city,
                    route_type="transit" if request.transportation == "公共交通" else "driving",
                )
                transport_data.append(
                    TransportSegment(
                        from_city=previous.city,
                        to_city=current.city,
                        method=request.transportation,
                        estimated_cost=int(route.get("cost", 0)),
                        duration_minutes=int(route.get("duration", 0)) // 60,
                    )
                )
            return {"transport_data": transport_data}

    def _generate_trip_plan(self, state: GraphState) -> dict:
        request = state["request"]
        trace_id = state.get("trace_id", "unknown")
        with self._logged_node("generate_trip_plan", trace_id):
            query = self._build_planner_query(request, state)
            prompt = ChatPromptTemplate.from_messages(
                [("system", PLANNER_SYSTEM_PROMPT), ("human", "{query}")]
            )
            chain = prompt | self.llm

            last_error = None
            for attempt in range(1, 3):
                started = time.perf_counter()
                try:
                    response = chain.invoke({"query": query})
                except Exception as exc:
                    elapsed_ms = round((time.perf_counter() - started) * 1000)
                    logger.exception(
                        "llm_failed trace_id=%s node=generate_trip_plan attempt=%s "
                        "elapsed_ms=%s error_type=%s retryable=true",
                        trace_id, attempt, elapsed_ms, type(exc).__name__,
                    )
                    raise
                content = response.content if hasattr(response, "content") else str(response)
                try:
                    plan = self._parse_json_response(content)
                    elapsed_ms = round((time.perf_counter() - started) * 1000)
                    logger.info(
                        "llm_finished trace_id=%s node=generate_trip_plan attempt=%s elapsed_ms=%s",
                        trace_id, attempt, elapsed_ms,
                    )
                    return {"trip_plan": plan}
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "llm_parse_retry trace_id=%s node=generate_trip_plan attempt=%s "
                        "error_type=%s",
                        trace_id, attempt, type(exc).__name__,
                    )
                    query = (
                        f"上一次输出不符合 JSON 结构，错误：{exc}\n"
                        f"上一次输出：{content[:2000]}\n"
                        "请重新输出完整合法 JSON。\n"
                        f"原始需求：{query}"
                    )
            raise ValueError(f"LLM 未能生成合法行程计划: {last_error}")

    def _semantic_review(self, request: TripRequest, plan: TripPlan) -> ReviewResult:
        review_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是旅行计划审查员。请只输出 JSON，不要输出解释文字。判断计划是否满足用户的旅行偏好、特别期待、交通住宿选择和每日节奏。硬约束由程序检查，你只审查语义内容。预算限制是每位出行人的上限，计划中的 budget.total 是所有人的总预算，必须使用总预算 ÷ 出行人数计算人均预算；不要仅因为总预算高于人均预算上限而判定超预算。若只有轻微偏好未完全满足，passed 可以为 true，但 issues 中要说明；用户没有提出的要求不要列为问题。JSON 格式："
                '{{"passed":true,"semantic_score":85,"issues":[],"suggestions":[],"summary":""}}',
            ),
            ("human", "用户请求：{request}\n旅行计划：{plan}"),
        ])
        try:
            response = (review_prompt | self.llm).invoke(
                {"request": request.model_dump_json(), "plan": plan.model_dump_json()}
            )
            content = response.content if hasattr(response, "content") else str(response)
            raw = self._parse_json_object(content)
            score = raw.get("semantic_score")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
                score = None
            return ReviewResult(
                passed=bool(raw.get("passed", False)),
                semantic_score=score,
                hard_rule_passed=True,
                semantic_rule_passed=bool(raw.get("passed", False)),
                issues=[str(item) for item in raw.get("issues", [])],
                suggestions=[str(item) for item in raw.get("suggestions", [])],
                summary=str(raw.get("summary", "")),
            )
        except Exception as exc:
            return ReviewResult(
                passed=False,
                hard_rule_passed=True,
                semantic_rule_passed=False,
                issues=[f"语义审查失败：{exc}"],
                summary="无法完成语义审查",
            )

    @staticmethod
    def _parse_json_object(content: str) -> dict:
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1)
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("审查响应中未找到 JSON 对象")
        value = json.loads(content[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("审查响应不是 JSON 对象")
        return value

    def _review_trip_plan(self, state: GraphState) -> dict:
        request = state["request"]
        plan = state["trip_plan"]
        trace_id = state.get("trace_id", "unknown")
        with self._logged_node("review_trip_plan", trace_id):
            plan.budget = calculate_budget(plan, request)
            hard_issues = validate_trip_plan_hard_rules(plan, request)
            semantic = self._semantic_review(request, plan)
            issues = hard_issues + semantic.issues
            hard_passed = not hard_issues
            semantic_passed = semantic.semantic_rule_passed
            passed = hard_passed and semantic_passed
            if not hard_passed:
                level = "C"
            elif issues:
                level = "B"
            else:
                level = "A"
            retry_count = state.get("retry_count", 0)
            if not passed and retry_count < state.get("max_retries", 3):
                retry_count += 1
                logger.info(
                    "review_retry trace_id=%s retry_count=%s max_retries=%s",
                    trace_id, retry_count, state.get("max_retries", 3),
                )
            logger.info(
                "review_finished trace_id=%s level=%s passed=%s retry_count=%s",
                trace_id, level, passed, retry_count,
            )
            review = ReviewResult(
                level=level,
                passed=passed,
                semantic_score=semantic.semantic_score,
                hard_rule_passed=hard_passed,
                semantic_rule_passed=semantic_passed,
                issues=issues,
                suggestions=semantic.suggestions,
                summary=semantic.summary or ("；".join(issues) if issues else "计划符合需求"),
                retry_count=retry_count,
            )
            return {
                "trip_plan": plan,
                "review_result": review,
                "review_feedback": "；".join(issues + semantic.suggestions),
                "retry_count": retry_count,
            }

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("search_attractions", self._search_attractions)
        graph.add_node("get_weather", self._get_weather)
        graph.add_node("search_hotels", self._search_hotels)
        graph.add_node("search_intercity_transport", self._search_intercity_transport)
        graph.add_node("generate_trip_plan", self._generate_trip_plan)
        graph.add_node("review_trip_plan", self._review_trip_plan)
        graph.add_edge(START, "search_attractions")
        graph.add_edge("search_attractions", "get_weather")
        graph.add_edge("get_weather", "search_hotels")
        graph.add_edge("search_hotels", "search_intercity_transport")
        graph.add_edge("search_intercity_transport", "generate_trip_plan")
        graph.add_edge("generate_trip_plan", "review_trip_plan")
        graph.add_conditional_edges(
            "review_trip_plan",
            route_after_review,
            {"regenerate": "generate_trip_plan", "end": END},
        )
        return graph.compile()

    def plan_trip(
        self,
        request: TripRequest,
        trace_id: str | None = None,
        current_draft: TripPlan | None = None,
        conversation_context: str = "",
    ) -> PlanningResult:
        result = self.graph.invoke({
            "request": request,
            "trace_id": trace_id or "unknown",
            "retry_count": 0,
            "max_retries": 3,
            "current_draft": current_draft,
            "conversation_context": conversation_context,
        })
        trip_plan = result["trip_plan"]

        trip_plan = self._ensure_budget(trip_plan, request)

        try:
            rag = self._get_rag_service()
            for segment in trip_plan.segments:
                for day in segment.days:
                    for attraction in day.attractions:
                        detail = rag.get_attraction_rag_text(
                            attraction.name, segment.city
                        )
                        if detail:
                            attraction.description = (
                                f"{attraction.description}\n\n——知识库参考——\n{detail}"
                            )
        except Exception as exc:
            logger.exception(
                "rag_history_enrichment_failed trace_id=%s error_type=%s",
                trace_id or "unknown", type(exc).__name__,
            )
        review = result.get("review_result") or ReviewResult(
            level="C", summary="未获取审查结果"
        )
        return PlanningResult(plan=trip_plan, review=review)

    def get_agent_info(self) -> dict:
        return {
            "name": "LangGraph 旅行规划系统",
            "framework": "langgraph",
            "nodes": [
                "search_attractions",
                "get_weather",
                "search_hotels",
                "search_intercity_transport",
                "generate_trip_plan",
                "review_trip_plan",
            ],
        }

    @staticmethod
    def _parse_json_response(content: str) -> TripPlan:
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1)
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("LLM 响应中未找到 JSON 对象")
        return TripPlan.model_validate(json.loads(content[start : end + 1]))

    def _build_planner_query(self, request: TripRequest, state: GraphState) -> str:
        city_blocks = []
        city_data = state.get("city_data", [])
        if not city_data and state.get("attraction_pois") is not None:
            city_data = [{
                "city": request.city,
                "attraction_pois": state.get("attraction_pois", []),
                "weather_info": state.get("weather_info", []),
                "hotel_pois": state.get("hotel_pois", []),
            }]
        for item, destination in zip(city_data, request.destinations):
            city_blocks.append(f"""城市：{destination.city}
日期：{destination.start_date} 至 {destination.end_date}
天数：{(date.fromisoformat(destination.end_date) - date.fromisoformat(destination.start_date)).days + 1}天
可选景点：
{self._pois_to_text(item.get('attraction_pois', [])) or '无'}

天气信息：
{self._weather_to_text(item.get('weather_info', [])) or '无'}

可选酒店：
{self._pois_to_text(item.get('hotel_pois', [])) or '无'}""")
        transport_text = "\n".join(
            f"{item.from_city} -> {item.to_city} | 方式: {item.method} | "
            f"耗时: {item.duration_minutes}分钟 | 费用: {item.estimated_cost}元"
            for item in state.get("transport_data", [])
        )
        city_text = "\n\n".join(city_blocks)
        query = f"""请为以下多城市旅行需求生成完整行程计划：

城市片段数据：
{city_text or '无'}

城市间交通：
{transport_text or '无跨城交通'}

出行人数：{request.traveler_count}人
交通方式：{request.transportation}
住宿偏好：{request.accommodation}
旅行偏好：{', '.join(request.preferences) if request.preferences else '无'}
"""
        if request.budget_limit is not None:
            query += (
                f"\n人均预算基准上限：{request.budget_limit}元，允许合理浮动20%，请将人均预算控制在{request.budget_limit * BUDGET_TOLERANCE:.0f}元以内。\n"
                "预算包含门票、住宿、餐饮和当地交通，不包含往返大交通。\n"
            )
        if request.free_text_input:
            query += f"\n额外要求：{request.free_text_input}\n"
        if state.get("current_draft"):
            query += (
                "\n当前临时计划（请在保留未被修改约束的前提下重新规划完整计划）：\n"
                f"{state['current_draft'].model_dump_json()}\n"
            )
        if state.get("conversation_context"):
            query += f"\n当前会话中的关键对话：\n{state['conversation_context']}\n"
        if state.get("review_feedback"):
            query += f"\n上一次审查反馈，请优先修正：{state['review_feedback']}\n"
        try:
            context = self._get_rag_service().build_rag_context(request)
            if context:
                query += f"\n{context}\n"
        except Exception as exc:
            logger.exception(
                "rag_context_failed trace_id=%s error_type=%s",
                state.get("trace_id", "unknown"), type(exc).__name__,
            )
        return query + "\n请严格按照要求输出完整 JSON。"

    @staticmethod
    def _pois_to_text(pois: list[POIInfo]) -> str:
        return "\n".join(
            f"{index}. {poi.name} | 地址: {poi.address} | 坐标: "
            f"{poi.location.longitude},{poi.location.latitude}"
            for index, poi in enumerate(pois, 1)
        )

    @staticmethod
    def _weather_to_text(weather_list: list[WeatherInfo]) -> str:
        lines = []
        for weather in weather_list:
            if weather.forecast_available is False:
                lines.append(f"{weather.date}: 暂无预报，不要推测天气")
                continue
            lines.append(
                f"{weather.date}: 白天{weather.day_weather} {weather.day_temp}°C / "
                f"夜间{weather.night_weather} {weather.night_temp}°C, "
                f"风向{weather.wind_direction} {weather.wind_power}"
            )
        return "\n".join(lines)

    @staticmethod
    def _ensure_budget(trip_plan: TripPlan, request: TripRequest) -> TripPlan:
        if trip_plan.budget is not None:
            return trip_plan
        attractions = sum(
            attraction.ticket_price
            for day in trip_plan.days
            for attraction in day.attractions
        ) or 200
        meals = sum(
            meal.estimated_cost for day in trip_plan.days for meal in day.meals
        ) or 150 * request.travel_days
        hotels = sum(
            day.hotel.estimated_cost
            for day in trip_plan.days
            if day.hotel and day.hotel.estimated_cost
        ) or 400 * request.travel_days
        transportation = 50 * request.travel_days
        trip_plan.budget = Budget(
            total_attractions=attractions,
            total_hotels=hotels,
            total_meals=meals,
            total_transportation=transportation,
            total=attractions + hotels + meals + transportation,
        )
        return trip_plan


_multi_agent_planner: Optional[MultiAgentTripPlanner] = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    global _multi_agent_planner
    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()
    return _multi_agent_planner
