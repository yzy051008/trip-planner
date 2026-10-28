"""旅行规划请求、响应和业务数据模型。"""

from datetime import date, timedelta
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CityRequest(BaseModel):
    city: str = Field(..., min_length=1, description="目的地城市")
    start_date: str = Field(..., description="城市行程开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="城市行程结束日期 YYYY-MM-DD")
    preferences: list[str] = Field(default_factory=list, description="城市级偏好")

    @model_validator(mode="after")
    def validate_date_range(self):
        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)
        if end < start:
            raise ValueError("城市结束日期不能早于开始日期")
        return self


class TripRequest(BaseModel):
    destinations: list[CityRequest] = Field(default_factory=list, min_length=1)
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿偏好")
    preferences: list[str] = Field(default_factory=list, description="旅行偏好标签")
    free_text_input: Optional[str] = Field(default="", description="额外要求")
    traveler_count: int = Field(default=1, ge=1, description="出行人数")
    budget_limit: Optional[int] = Field(default=None, ge=0, description="人均预算上限(元)")

    # Legacy input fields remain accepted so saved forms and older clients can
    # be migrated to the Segment model without a separate endpoint.
    city: Optional[str] = Field(default=None, exclude=True)
    start_date: Optional[str] = Field(default=None, exclude=True)
    end_date: Optional[str] = Field(default=None, exclude=True)
    travel_days: Optional[int] = Field(default=None, exclude=True, ge=1, le=30)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_destination(cls, values):
        if isinstance(values, dict) and not values.get("destinations") and values.get("city"):
            values = dict(values)
            values["destinations"] = [{
                "city": values["city"],
                "start_date": values.get("start_date"),
                "end_date": values.get("end_date"),
            }]
        return values

    @model_validator(mode="after")
    def populate_legacy_accessors(self):
        for previous, current in zip(self.destinations, self.destinations[1:]):
            previous_end = date.fromisoformat(previous.end_date)
            current_start = date.fromisoformat(current.start_date)
            if current_start not in (previous_end, previous_end + timedelta(days=1)):
                raise ValueError(
                    f"{previous.city}与{current.city}的日期必须连续，最多允许共享一天交通日"
                )
        self.city = self.destinations[0].city
        self.start_date = self.destinations[0].start_date
        self.end_date = self.destinations[-1].end_date
        total_days = sum(
            (date.fromisoformat(item.end_date) - date.fromisoformat(item.start_date)).days + 1
            for item in self.destinations
        )
        shared_transition_days = sum(
            1 for previous, current in zip(self.destinations, self.destinations[1:])
            if previous.end_date == current.start_date
        )
        self.travel_days = total_days - shared_transition_days
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "destinations": [
                    {"city": "北京", "start_date": "2025-06-01", "end_date": "2025-06-03"}
                ],
                "transportation": "公共交通",
                "accommodation": "经济型酒店",
                "preferences": ["历史文化", "美食"],
                "free_text_input": "希望多安排一些博物馆",
                "traveler_count": 1,
                "budget_limit": 5000,
            }
        }
    )


class POISearchRequest(BaseModel):
    keywords: str = Field(..., description="搜索关键词")
    city: str = Field(..., description="城市")
    citylimit: bool = Field(default=True, description="是否限制在城市范围内")


class RouteRequest(BaseModel):
    origin_address: str = Field(..., description="起点地址")
    destination_address: str = Field(..., description="终点地址")
    origin_city: Optional[str] = Field(default=None, description="起点城市")
    destination_city: Optional[str] = Field(default=None, description="终点城市")
    route_type: str = Field(default="walking", description="路线类型")


class Location(BaseModel):
    longitude: float
    latitude: float


class Attraction(BaseModel):
    name: str
    address: str
    location: Location
    visit_duration: int
    description: str
    category: Optional[str] = "景点"
    rating: Optional[float] = None
    photos: list[str] = Field(default_factory=list)
    poi_id: Optional[str] = ""
    image_url: Optional[str] = None
    ticket_price: int = 0


class Meal(BaseModel):
    type: str
    name: str
    address: Optional[str] = None
    location: Optional[Location] = None
    description: Optional[str] = None
    estimated_cost: int = 0


class Hotel(BaseModel):
    name: str
    address: str = ""
    location: Optional[Location] = None
    price_range: str = ""
    rating: str = ""
    distance: str = ""
    type: str = ""
    estimated_cost: int = 0


class DayPlan(BaseModel):
    date: str
    day_index: int
    description: str
    transportation: str
    accommodation: str
    hotel: Optional[Hotel] = None
    attractions: list[Attraction] = Field(default_factory=list)
    meals: list[Meal] = Field(default_factory=list)


class WeatherInfo(BaseModel):
    date: str
    forecast_available: bool = True
    day_weather: str = ""
    night_weather: str = ""
    day_temp: Union[int, str] = 0
    night_temp: Union[int, str] = 0
    wind_direction: str = ""
    wind_power: str = ""

    @field_validator("day_temp", "night_temp", mode="before")
    @classmethod
    def parse_temperature(cls, value):
        if value is None:
            return 0
        if isinstance(value, str):
            value = value.replace("°C", "").replace("℃", "").replace("°", "").strip()
            try:
                return int(value)
            except ValueError:
                return 0
        return value


class Budget(BaseModel):
    total_attractions: int = 0
    total_hotels: int = 0
    total_meals: int = 0
    total_transportation: int = 0
    total: int = 0


class TransportSegment(BaseModel):
    from_city: str
    to_city: str
    method: str = ""
    estimated_cost: int = 0
    duration_minutes: int = 0
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None


class CitySegment(BaseModel):
    city: str
    start_date: str
    end_date: str
    days: list[DayPlan] = Field(default_factory=list)
    weather_info: list[WeatherInfo] = Field(default_factory=list)
    hotel_options: list[Hotel] = Field(default_factory=list)
    transport_from_previous: Optional[TransportSegment] = None


class TripPlan(BaseModel):
    segments: list[CitySegment] = Field(default_factory=list, min_length=1)
    # Legacy output fields are accepted when reading old history records.
    city: Optional[str] = Field(default=None, exclude=True)
    start_date: str = ""
    end_date: str = ""
    days: list[DayPlan] = Field(default_factory=list, exclude=True)
    weather_info: list[WeatherInfo] = Field(default_factory=list, exclude=True)
    overall_suggestions: str = ""
    budget: Optional[Budget] = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_plan(cls, values):
        if isinstance(values, dict) and not values.get("segments") and values.get("city"):
            values = dict(values)
            values["segments"] = [{
                "city": values["city"],
                "start_date": values.get("start_date", ""),
                "end_date": values.get("end_date", ""),
                "days": values.get("days", []),
                "weather_info": values.get("weather_info", []),
            }]
        return values

    @model_validator(mode="after")
    def populate_legacy_accessors(self):
        if self.segments:
            self.city = self.segments[0].city
            self.start_date = self.segments[0].start_date
            self.end_date = self.segments[-1].end_date
            self.days = [day for segment in self.segments for day in segment.days]
            self.weather_info = [
                weather for segment in self.segments for weather in segment.weather_info
            ]
        return self


class TripPlanResponse(BaseModel):
    success: bool
    message: str = ""
    id: Optional[int] = None
    data: Optional[TripPlan] = None
    review: Optional["ReviewResult"] = None


class PlanningSessionResponse(BaseModel):
    success: bool = True
    session_id: str
    status: Literal[
        "drafting",
        "replanning",
        "waiting_confirmation",
        "confirmed",
        "failed",
        "cancelled",
    ]
    draft_version: int = Field(ge=1)
    data: Optional[TripPlan] = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    review: Optional["ReviewResult"] = None
    message: str = ""
    record_id: Optional[int] = None


class PlanningTurnResponse(BaseModel):
    success: bool = True
    type: Literal["answer", "replan", "clarify", "reject", "error"]
    message: str
    session_id: Optional[str] = None
    status: Optional[str] = None
    draft_version: Optional[int] = Field(default=None, ge=1)
    data: Optional[TripPlan] = None
    plan_changed: bool = False
    changes: list[str] = Field(default_factory=list)
    review: Optional["ReviewResult"] = None
    requires_confirmation: bool = False


class PlanningMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    draft_version: int = Field(..., ge=1)


class PlanningConfirmRequest(BaseModel):
    draft_version: int = Field(..., ge=1)


class ReviewResult(BaseModel):
    level: Literal["A", "B", "C"] = "C"
    passed: bool = False
    semantic_score: Optional[float] = Field(default=None, ge=0, le=100)
    hard_rule_passed: bool = False
    semantic_rule_passed: bool = False
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = ""
    retry_count: int = 0


class POIInfo(BaseModel):
    id: str
    name: str
    type: str
    address: str
    location: Location
    tel: Optional[str] = None


class POISearchResponse(BaseModel):
    success: bool
    message: str = ""
    data: list[POIInfo] = Field(default_factory=list)


class RouteInfo(BaseModel):
    distance: float
    duration: int
    route_type: str
    description: str


class RouteResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[RouteInfo] = None


class WeatherResponse(BaseModel):
    success: bool
    message: str = ""
    data: list[WeatherInfo] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    trace_id: Optional[str] = None
