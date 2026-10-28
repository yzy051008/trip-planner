"""历史行程接口。"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.error import BizException
from ...db.database import get_db
from ...models.schemas import TripPlan
from ...services import history_service
from ...services.rag_service import get_rag_service


router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("", summary="历史记录列表")
def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    records, total = history_service.list_trip_records(db, page, page_size, city)
    return {
        "success": True,
        "data": [history_service.trip_record_to_summary(record) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{record_id}", summary="历史记录详情")
def get_history(record_id: int, db: Session = Depends(get_db)):
    record = history_service.get_trip_record(db, record_id)
    if record is None:
        raise BizException("历史记录不存在", status_code=404)

    return {
        "success": True,
        "data": {
            "id": record.id,
            "city": record.city,
            "start_date": record.start_date,
            "end_date": record.end_date,
            "travel_days": record.travel_days,
            "transportation": record.transportation,
            "accommodation": record.accommodation,
            "preferences": json.loads(record.preferences or "[]"),
            "free_text_input": record.free_text_input,
            "segments": [
                {
                    "city": segment.city,
                    "start_date": segment.start_date,
                    "end_date": segment.end_date,
                    "segment_order": segment.segment_order,
                }
                for segment in record.segments
            ],
            "plan": json.loads(record.plan_json),
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


@router.put("/{record_id}", summary="更新历史记录行程")
def update_history(record_id: int, plan: TripPlan, db: Session = Depends(get_db)):
    record = history_service.update_trip_record(db, record_id, plan)
    if record is None:
        raise BizException("历史记录不存在", status_code=404)
    request = history_service.request_from_record(record)
    get_rag_service().update_history_plan(record.id, request, plan)
    return {"success": True, "message": "更新成功", "id": record.id}


@router.delete("/{record_id}", summary="删除历史记录")
def delete_history(record_id: int, db: Session = Depends(get_db)):
    if not history_service.delete_trip_record(db, record_id):
        raise BizException("历史记录不存在", status_code=404)
    get_rag_service().delete_history_plan(record_id)
    return {"success": True, "message": "删除成功"}
