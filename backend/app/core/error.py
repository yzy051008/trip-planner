"""业务异常与全局异常处理器。"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .trace import new_trace_id


logger = logging.getLogger(__name__)


class BizException(Exception):
    """业务异常：携带 HTTP 状态码和需要返回给用户的提示信息。"""

    def __init__(self, detail: str, status_code: int = 400, error_code: str = "BUSINESS_ERROR"):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(detail)


class ExternalServiceError(BizException):
    """可安全返回给客户端的外部服务错误。"""

    def __init__(
        self,
        detail: str,
        *,
        service: str,
        operation: str,
        trace_id: str,
        retry_count: int = 0,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
    ):
        self.service = service
        self.operation = operation
        self.trace_id = trace_id
        self.retry_count = retry_count
        super().__init__(detail, status_code=503, error_code=error_code)


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None) or new_trace_id()


async def biz_exception_handler(request: Request, exc: BizException):
    """处理可控业务异常，返回统一错误结构。"""
    trace_id = _trace_id(request)
    logger.warning(
        "business_error trace_id=%s status_code=%s error_code=%s path=%s",
        trace_id, exc.status_code, exc.error_code, request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": exc.error_code,
            "trace_id": trace_id,
        },
    )


async def external_service_exception_handler(request: Request, exc: ExternalServiceError):
    """将外部依赖失败转换为不暴露原始响应的统一错误。"""
    trace_id = exc.trace_id or _trace_id(request)
    logger.warning(
        "external_service_error trace_id=%s service=%s operation=%s "
        "retry_count=%s error_code=%s",
        trace_id, exc.service, exc.operation, exc.retry_count, exc.error_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": exc.error_code,
            "trace_id": trace_id,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace_id = _trace_id(request)
    logger.warning("validation_error trace_id=%s path=%s", trace_id, request.url.path)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数不合法",
            "error_code": "VALIDATION_ERROR",
            "trace_id": trace_id,
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """处理未捕获异常，返回统一的 500 错误结构。"""
    trace_id = _trace_id(request)
    logger.exception("internal_error trace_id=%s path=%s", trace_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误，请稍后重试",
            "error_code": "INTERNAL_SERVER_ERROR",
            "trace_id": trace_id,
        },
    )
