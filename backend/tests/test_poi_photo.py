from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from app.api.routes import poi


def test_photo_route_returns_poi_photo_payload(monkeypatch):
    class FakeAmapService:
        def get_poi_photo_by_name(self, name):
            assert name == "故宫"
            return "https://example.com/forbidden-city.jpg"

    monkeypatch.setattr(poi, "get_amap_service", lambda: FakeAmapService())
    app = FastAPI()
    app.include_router(poi.router, prefix="/api")

    response = TestClient(app).get("/api/poi/photo", params={"name": "故宫"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "获取图片成功",
        "data": {
            "name": "故宫",
            "photo_url": "https://example.com/forbidden-city.jpg",
        },
    }


def test_photo_service_converts_http_url_and_uses_cache(monkeypatch):
    from app.services import amap_service

    class FakeSettings:
        amap_api_key = "test-key"

    monkeypatch.setattr(amap_service, "get_settings", lambda: FakeSettings())
    service = amap_service.AmapService()
    calls = []

    def fake_get(path, params):
        calls.append((path, params))
        return {"pois": [{"photos": [{"url": "http://example.com/photo.jpg"}]}]}

    monkeypatch.setattr(service, "_get", fake_get)

    assert service.get_poi_photo_by_name("故宫") == "https://example.com/photo.jpg"
    assert service.get_poi_photo_by_name("故宫") == "https://example.com/photo.jpg"
    assert len(calls) == 1


def test_photo_service_falls_back_to_poi_detail_when_search_has_no_photo(monkeypatch):
    from app.services import amap_service

    class FakeSettings:
        amap_api_key = "test-key"

    monkeypatch.setattr(amap_service, "get_settings", lambda: FakeSettings())
    service = amap_service.AmapService()
    monkeypatch.setattr(
        service,
        "_get",
        lambda path, params: {"pois": [{"id": "poi-1", "photos": []}]},
    )
    monkeypatch.setattr(
        service,
        "get_poi_detail",
        lambda poi_id: {"photos": [{"url": "http://example.com/detail.jpg"}]},
    )

    assert service.get_poi_photo_by_name("故宫") == "https://example.com/detail.jpg"


def test_amap_service_parses_poi_weather_route_and_detail_data(monkeypatch):
    from app.services import amap_service

    class FakeSettings:
        amap_api_key = "test-key"

    monkeypatch.setattr(amap_service, "get_settings", lambda: FakeSettings())
    service = amap_service.AmapService()

    responses = [
        {"pois": [{"id": "1", "name": "故宫", "type": "景点", "address": "北京", "location": "116.397,39.918", "tel": "123"}]},
        {"geocodes": [{"adcode": "110000", "location": "116.397,39.918"}]},
        {"forecasts": [{"casts": [{"date": "2026-09-04", "dayweather": "晴", "nightweather": "多云", "daytemp": "25", "nighttemp": "15", "daywind": "南风", "daypower": "3"}]}]},
        {"geocodes": [{"location": "116.397,39.918"}]},
        {"geocodes": [{"location": "116.407,39.928"}]},
        {"route": {"paths": [{"distance": "1000", "duration": "600"}]}},
        {"geocodes": [{"adcode": "110000"}]},
        {"pois": [{"name": "故宫", "photos": []}]},
    ]
    monkeypatch.setattr(service, "_get", lambda path, params: responses.pop(0))

    assert service.search_poi("故宫", "北京")[0].location.latitude == 39.918
    assert service.get_weather("北京")[0].day_temp == 25
    route = service.plan_route("天安门", "故宫", route_type="driving")
    assert route["route_type"] == "driving"
    assert route["distance"] == 1000
    assert service.geocode("北京")[0]["adcode"] == "110000"
    assert service.get_poi_detail("1")["name"] == "故宫"


def test_weather_matches_itinerary_dates_and_marks_unavailable_forecasts(monkeypatch):
    from app.services import amap_service

    class FakeSettings:
        amap_api_key = "test-key"

    monkeypatch.setattr(amap_service, "get_settings", lambda: FakeSettings())
    service = amap_service.AmapService()
    responses = [
        {"geocodes": [{"adcode": "110000"}]},
        {
            "forecasts": [
                {
                    "casts": [
                        {"date": "2026-09-08", "dayweather": "晴", "daytemp": "28"},
                        {"date": "2026-09-09", "dayweather": "小雨", "daytemp": "24"},
                    ]
                }
            ]
        },
    ]
    monkeypatch.setattr(service, "_get", lambda path, params: responses.pop(0))

    weather = service.get_weather("北京", "2026-09-08", "2026-09-11")

    assert [item.date for item in weather] == [
        "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11"
    ]
    assert weather[0].day_weather == "晴"
    assert weather[1].forecast_available is True
    assert weather[2].forecast_available is False
    assert weather[2].day_weather == "暂无预报"
    assert weather[3].day_temp == 0


def test_search_poi_normalizes_non_string_address(monkeypatch):
    from app.services import amap_service

    class FakeSettings:
        amap_api_key = "test-key"

    monkeypatch.setattr(amap_service, "get_settings", lambda: FakeSettings())
    service = amap_service.AmapService()
    monkeypatch.setattr(
        service,
        "_get",
        lambda path, params: {
            "pois": [
                {
                    "id": "1",
                    "name": "呼和浩特博物馆",
                    "type": "博物馆",
                    "address": [],
                    "location": "111.675,40.815",
                }
            ]
        },
    )

    pois = service.search_poi("博物馆", "内蒙古")

    assert pois[0].address == ""


def test_amap_get_logs_external_call(caplog):
    from app.services.amap_service import AmapService

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "1", "pois": []}

    class Client:
        def get(self, *args, **kwargs):
            return Response()

    service = object.__new__(AmapService)
    service.client = Client()
    service.api_key = "test-key"

    with caplog.at_level("INFO"):
        service._get("/v3/place/text", {"keywords": "测试"}, trace_id="trace-amap")

    assert any(
        "external_call_finished" in record.getMessage()
        and "service=amap" in record.getMessage()
        and "trace-amap" in record.getMessage()
        for record in caplog.records
    )


def test_amap_get_retries_read_timeout_then_succeeds(monkeypatch):
    from app.services.amap_service import AmapService

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "1", "pois": []}

    calls = {"count": 0}

    class Client:
        def get(self, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                raise httpx.ReadTimeout("temporary timeout")
            return Response()

    service = object.__new__(AmapService)
    service.client = Client()
    service.api_key = "test-key"
    service.max_retries = 2
    service.sleep = lambda _: None
    service._wait_for_rate_limit = lambda: None

    result = service._get("/v3/place/text", {"keywords": "测试"}, trace_id="trace-retry")

    assert result == {"status": "1", "pois": []}
    assert calls["count"] == 3


def test_amap_get_does_not_retry_authentication_error(monkeypatch):
    from app.services.amap_service import AmapService

    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(401, request=request)
    calls = {"count": 0}

    class Client:
        def get(self, *args, **kwargs):
            calls["count"] += 1
            return response

    service = object.__new__(AmapService)
    service.client = Client()
    service.api_key = "test-key"
    service.max_retries = 2
    service.sleep = lambda _: None
    service._wait_for_rate_limit = lambda: None

    with pytest.raises(Exception):
        service._get("/v3/place/text", {"keywords": "测试"}, trace_id="trace-auth")

    assert calls["count"] == 1


def test_amap_get_raises_structured_timeout_after_retry_budget():
    from app.core.error import ExternalServiceError
    from app.services.amap_service import AmapService

    class Client:
        def get(self, *args, **kwargs):
            raise httpx.ConnectTimeout("unavailable")

    service = object.__new__(AmapService)
    service.client = Client()
    service.api_key = "test-key"
    service.max_retries = 2
    service.sleep = lambda _: None
    service._wait_for_rate_limit = lambda: None

    with pytest.raises(ExternalServiceError) as error:
        service._get("/v3/weather/weatherInfo", {"city": "110000"}, trace_id="trace-timeout")

    assert error.value.error_code == "AMAP_TIMEOUT"
    assert error.value.retry_count == 2
    assert error.value.trace_id == "trace-timeout"
