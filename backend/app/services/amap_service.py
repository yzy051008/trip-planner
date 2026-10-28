"""高德地图图片服务。"""

import logging
import threading
import time
from datetime import date, timedelta
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings
from ..core.error import ExternalServiceError
from ..models.schemas import Location, POIInfo, WeatherInfo


AMAP_BASE_URL = "https://restapi.amap.com"
AMAP_MIN_REQUEST_INTERVAL_SECONDS = 1.0
logger = logging.getLogger(__name__)


class AmapService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.amap_api_key
        if not self.api_key:
            raise ValueError("高德地图 API Key 未配置")
        self.client = httpx.Client(
            timeout=httpx.Timeout(
                connect=getattr(settings, "amap_connect_timeout", 3.0),
                read=getattr(settings, "amap_read_timeout", 10.0),
                write=getattr(settings, "amap_write_timeout", 3.0),
                pool=getattr(settings, "amap_pool_timeout", 3.0),
            )
        )
        self.max_retries = getattr(settings, "amap_max_retries", 2)
        self.sleep = time.sleep
        self._photo_cache: Dict[str, tuple[str, float]] = {}
        self._photo_blocked_until = 0.0
        self._rate_limit_lock = threading.Lock()
        self._last_request_at = 0.0

    def _wait_for_rate_limit(self) -> None:
        if not hasattr(self, "_rate_limit_lock"):
            self._rate_limit_lock = threading.Lock()
            self._last_request_at = 0.0
        with self._rate_limit_lock:
            now = time.monotonic()
            wait_seconds = AMAP_MIN_REQUEST_INTERVAL_SECONDS - (now - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._last_request_at = time.monotonic()

    def _get(self, path: str, params: Dict[str, Any], trace_id: str | None = None) -> dict:
        trace_id = trace_id or getattr(self, "trace_id", "unknown")
        method = path.rsplit("/", 1)[-1]
        max_retries = getattr(self, "max_retries", 2)
        sleep = getattr(self, "sleep", time.sleep)
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            started = time.perf_counter()
            try:
                self._wait_for_rate_limit()
                response = self.client.get(
                    f"{AMAP_BASE_URL}{path}",
                    params={**params, "key": self.api_key},
                )
                status_code = getattr(response, "status_code", 200)
                if status_code in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                else:
                    response.raise_for_status()
                data = response.json()
                if data.get("status") != "1":
                    raise ExternalServiceError(
                        f"高德 API 错误: {data.get('info', '未知错误')}",
                        service="amap",
                        operation=method,
                        trace_id=trace_id,
                        retry_count=attempt,
                        error_code="AMAP_BUSINESS_ERROR",
                    )
                logger.info(
                    "external_call_finished trace_id=%s service=amap method=%s "
                    "attempt=%s elapsed_ms=%s",
                    trace_id, method, attempt + 1,
                    round((time.perf_counter() - started) * 1000),
                )
                return data
            except ExternalServiceError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                retryable = status_code in {429, 500, 502, 503, 504}
                if not retryable or attempt >= max_retries:
                    error_code = "AMAP_RATE_LIMITED" if status_code == 429 else "AMAP_HTTP_ERROR"
                    raise ExternalServiceError(
                        "高德服务暂时不可用" if retryable else "高德接口请求失败",
                        service="amap",
                        operation=method,
                        trace_id=trace_id,
                        retry_count=attempt,
                        error_code=error_code,
                    ) from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt >= max_retries:
                    code = "AMAP_TIMEOUT" if isinstance(exc, httpx.TimeoutException) else "AMAP_CONNECTION_ERROR"
                    raise ExternalServiceError(
                        "高德接口请求超时" if code == "AMAP_TIMEOUT" else "高德服务连接失败",
                        service="amap",
                        operation=method,
                        trace_id=trace_id,
                        retry_count=attempt,
                        error_code=code,
                    ) from exc
            except Exception as exc:
                logger.exception(
                    "external_call_failed trace_id=%s service=amap method=%s "
                    "elapsed_ms=%s error_type=%s",
                    trace_id, method, round((time.perf_counter() - started) * 1000),
                    type(exc).__name__,
                )
                raise

            logger.warning(
                "external_call_retry trace_id=%s service=amap method=%s attempt=%s "
                "error_type=%s",
                trace_id, method, attempt + 1, type(last_error).__name__,
            )
            sleep(0.5 * (2 ** attempt))

        raise RuntimeError(f"高德请求失败: {last_error}")

    @staticmethod
    def _parse_location(location: str) -> Location:
        longitude, latitude = location.split(",")
        return Location(longitude=float(longitude), latitude=float(latitude))

    @staticmethod
    def _safe_text(value: Any) -> str:
        """将第三方接口字段安全转换为模型要求的字符串。"""
        return value if isinstance(value, str) else ""

    def search_poi(
        self, keywords: str, city: str, citylimit: bool = True
    ) -> list[POIInfo]:
        data = self._get(
            "/v3/place/text",
            {
                "keywords": keywords,
                "city": city,
                "citylimit": str(citylimit).lower(),
                "offset": 10,
                "page": 1,
                "extensions": "all",
            },
        )
        pois = []
        for item in data.get("pois", []):
            location = item.get("location", "")
            pois.append(
                POIInfo(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    type=item.get("type", ""),
                    address=self._safe_text(item.get("address")),
                    location=(
                        self._parse_location(location)
                        if location
                        else Location(longitude=0, latitude=0)
                    ),
                    tel=item.get("tel") or None,
                )
            )
        return pois

    def geocode(self, address: str, city: Optional[str] = None) -> list[dict]:
        params = {"address": address}
        if city:
            params["city"] = city
        data = self._get("/v3/geocode/geo", params)
        return data.get("geocodes", [])

    def get_weather(
        self, city: str, start_date: str | None = None, end_date: str | None = None
    ) -> list[WeatherInfo]:
        geocodes = self.geocode(city)
        if not geocodes:
            return []
        adcode = geocodes[0].get("adcode", "")
        data = self._get(
            "/v3/weather/weatherInfo",
            {"city": adcode, "extensions": "all"},
        )
        weather_list = []
        for forecast in data.get("forecasts", []):
            for cast in forecast.get("casts", []):
                weather_list.append(
                    WeatherInfo(
                        date=cast.get("date", ""),
                        day_weather=cast.get("dayweather", ""),
                        night_weather=cast.get("nightweather", ""),
                        day_temp=cast.get("daytemp", 0),
                        night_temp=cast.get("nighttemp", 0),
                        wind_direction=cast.get("daywind", ""),
                        wind_power=cast.get("daypower", ""),
                    )
                )
        if start_date is None or end_date is None:
            return weather_list

        requested_start = date.fromisoformat(start_date)
        requested_end = date.fromisoformat(end_date)
        if requested_end < requested_start:
            return []

        weather_by_date = {weather.date: weather for weather in weather_list}
        result = []
        current = requested_start
        while current <= requested_end:
            requested_date = current.isoformat()
            result.append(
                weather_by_date.get(
                    requested_date,
                    WeatherInfo(
                        date=requested_date,
                        forecast_available=False,
                        day_weather="暂无预报",
                        night_weather="暂无预报",
                    ),
                )
            )
            current += timedelta(days=1)
        return result

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking",
    ) -> Dict[str, Any]:
        origin_geocodes = self.geocode(origin_address, origin_city)
        destination_geocodes = self.geocode(destination_address, destination_city)
        if not origin_geocodes or not destination_geocodes:
            return {}

        origin = origin_geocodes[0].get("location", "")
        destination = destination_geocodes[0].get("location", "")
        if not origin or not destination:
            return {}

        paths = {
            "driving": "/v3/direction/driving",
            "transit": "/v3/direction/transit/integrated",
            "walking": "/v3/direction/walking",
        }
        data = self._get(
            paths.get(route_type, paths["walking"]),
            {"origin": origin, "destination": destination},
        )
        route_paths = data.get("route", {}).get("paths", [])
        if not route_paths:
            return {}

        first = route_paths[0]
        distance = float(first.get("distance", 0))
        duration = int(first.get("duration", 0))
        return {
            "distance": distance,
            "duration": duration,
            "route_type": route_type,
            "description": f"全程约{distance / 1000:.1f}公里,预计{duration // 60}分钟",
        }

    def get_poi_photo_by_name(self, name: str) -> Optional[str]:
        cached = self._photo_cache.get(name)
        if cached and cached[1] > time.time():
            return cached[0]
        if time.time() < self._photo_blocked_until:
            return None

        try:
            data = self._get(
                "/v3/place/text",
                {"keywords": name, "offset": 1, "page": 1, "extensions": "all"},
            )
            pois = data.get("pois", [])
            if not pois:
                return None

            photos = pois[0].get("photos") or []
            if not photos and pois[0].get("id"):
                detail = self.get_poi_detail(pois[0]["id"])
                photos = detail.get("photos") or []
            url = photos[0].get("url", "") if photos else ""
            if not url:
                return None

            url = url if url.startswith("https://") else url.replace(
                "http://", "https://", 1
            )
            self._photo_cache[name] = (url, time.time() + 3600)
            return url
        except Exception as exc:
            if "CUQPS_HAS_EXCEEDED_THE_LIMIT" in str(exc):
                self._photo_blocked_until = time.time() + 30
            return None

    def get_poi_detail(self, poi_id: str) -> dict:
        data = self._get(
            "/v3/place/detail",
            {"id": poi_id, "extensions": "all"},
        )
        pois = data.get("pois", [])
        return pois[0] if pois else {}


_amap_service: Optional[AmapService] = None


def get_amap_service() -> AmapService:
    global _amap_service
    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service
