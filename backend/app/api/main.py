"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response

from ..core.error import (
    BizException,
    biz_exception_handler,
    global_exception_handler,
    validation_exception_handler,
)
from ..core.logging_config import configure_logging
from ..core.trace import new_trace_id
from ..db.database import init_db
from .routes import history
from .routes import poi
from .routes import trip


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LangChain 智能旅行助手",
    version="1.0.0",
    lifespan=lifespan,
)

configure_logging()


@app.middleware("http")
async def trace_middleware(request: Request, call_next) -> Response:
    trace_id = new_trace_id()
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response

app.add_exception_handler(BizException, biz_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(history.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(trip.router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "LangChain 智能旅行助手",
        "version": "1.0.0",
        "status": "running",
    }
