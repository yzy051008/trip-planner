import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.error import (
    BizException,
    ExternalServiceError,
    biz_exception_handler,
    external_service_exception_handler,
    global_exception_handler,
)


def test_biz_exception_returns_custom_status_and_message():
    app = FastAPI()
    app.add_exception_handler(BizException, biz_exception_handler)

    @app.get("/missing")
    def missing():
        raise BizException("数据不存在", status_code=404)

    response = TestClient(app).get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "数据不存在"
    assert body["error_code"] == "BUSINESS_ERROR"
    assert body["trace_id"]


def test_unknown_exception_returns_standard_500_response():
    app = FastAPI()
    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/failure")
    def failure():
        raise RuntimeError("测试异常")

    response = TestClient(app, raise_server_exceptions=False).get("/failure")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "服务器内部错误，请稍后重试"
    assert body["error_code"] == "INTERNAL_SERVER_ERROR"
    assert body["trace_id"]
    assert "测试异常" not in body["message"]


def test_external_service_error_returns_retryable_503_response():
    app = FastAPI()
    app.add_exception_handler(ExternalServiceError, external_service_exception_handler)

    @app.get("/amap")
    def amap_failure():
        raise ExternalServiceError(
            "高德接口请求超时",
            service="amap",
            operation="get_weather",
            trace_id="trace-amap",
            retry_count=2,
            error_code="AMAP_TIMEOUT",
        )

    response = TestClient(app).get("/amap")

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "message": "高德接口请求超时",
        "error_code": "AMAP_TIMEOUT",
        "trace_id": "trace-amap",
    }
