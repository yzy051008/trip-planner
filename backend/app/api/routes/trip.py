"""旅行规划接口。"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...agents.trip_planner_agent import PlanningResult, get_trip_planner_agent
from ...core.error import BizException
from ...db.database import get_db
from ...models.schemas import ReviewResult, TripPlan, TripPlanResponse, TripRequest
from ...services import history_service
from ...services.rag_service import get_rag_service


router = APIRouter(prefix="/trip", tags=["旅行规划"])
logger = logging.getLogger(__name__)


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
)
def plan_trip(request: TripRequest, http_request: Request, db: Session = Depends(get_db)):
    trace_id = getattr(http_request.state, "trace_id", "unknown")
    result = get_trip_planner_agent().plan_trip(
        request, trace_id=trace_id
    )
    if isinstance(result, PlanningResult):
        trip_plan = result.plan
        review = result.review
    else:
        # Keep compatibility with older/custom agents that return a raw plan.
        trip_plan = TripPlan.model_validate(result)
        review = ReviewResult(
            level="A",
            passed=True,
            hard_rule_passed=True,
            semantic_rule_passed=True,
            summary="计划已生成",
        )

    record_id = None
    try:
        record = history_service.create_trip_record(db, request, trip_plan)
        record_id = record.id
    except Exception as exc:
        logger.exception(
            "history_persist_failed trace_id=%s error_type=%s",
            trace_id, type(exc).__name__,
        )

    if record_id is not None:
        try:
            synced = get_rag_service().add_history_plan(record_id, request, trip_plan)
            if synced is False:
                logger.warning("rag_history_sync_failed trace_id=%s result=false", trace_id)
        except Exception as exc:
            logger.exception(
                "rag_history_sync_failed trace_id=%s error_type=%s",
                trace_id, type(exc).__name__,
            )

    return TripPlanResponse(
        success=True,
        message="旅行计划生成成功",
        id=record_id,
        data=trip_plan,
        review=review,
    )
