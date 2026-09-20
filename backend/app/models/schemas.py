"""旅行规划请求、响应和业务数据模型。"""

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripRequest(BaseModel):
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    travel_days: int = Field(..., ge=1, le=30, description="旅行天数")
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿偏好")
    preferences: list[str] = Field(default_factory=list, description="旅行偏好标签")
    free_text_input: Optional[str] = Field(default="", description="额外要求")
    traveler_count: int = Field(default=1, ge=1, description="出行人数")
    budget_limit: Optional[int] = Field(default=None, ge=0, description="人均预算上限(元)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "北京",
                "start_date": "2025-06-01",
                "end_date": "2025-06-03",
                "travel_days": 3,
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


class TripPlan(BaseModel):
    city: str
    start_date: str = ""
    end_date: str = ""
    days: list[DayPlan]
    weather_info: list[WeatherInfo] = Field(default_factory=list)
    overall_suggestions: str = ""
    budget: Optional[Budget] = None


class TripPlanResponse(BaseModel):
    success: bool
    message: str = ""
    id: Optional[int] = None
    data: Optional[TripPlan] = None
    review: Optional["ReviewResult"] = None


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
