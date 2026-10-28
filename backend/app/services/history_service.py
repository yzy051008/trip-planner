"""历史行程记录的数据库操作。"""

import json
from typing import Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from ..db.models import TripRecord, TripSegment
from ..models.schemas import CityRequest, TripPlan, TripRequest


def create_trip_record(db: Session, request: TripRequest, trip_plan: TripPlan) -> TripRecord:
    record = TripRecord(
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
        travel_days=request.travel_days,
        transportation=request.transportation,
        accommodation=request.accommodation,
        preferences=json.dumps(request.preferences, ensure_ascii=False),
        free_text_input=request.free_text_input or "",
        plan_json=trip_plan.model_dump_json(),
    )
    db.add(record)
    db.flush()
    _replace_record_segments(record, trip_plan)
    db.commit()
    db.refresh(record)
    return record


def _segment_to_record(segment, segment_order: int) -> TripSegment:
    return TripSegment(
        city=segment.city,
        start_date=segment.start_date,
        end_date=segment.end_date,
        segment_order=segment_order,
        transport_from_previous_json=(
            segment.transport_from_previous.model_dump_json()
            if segment.transport_from_previous
            else None
        ),
    )


def _replace_record_segments(record: TripRecord, trip_plan: TripPlan) -> None:
    record.segments.clear()
    record.segments.extend(
        _segment_to_record(segment, index)
        for index, segment in enumerate(trip_plan.segments)
    )


def request_from_record(record: TripRecord) -> TripRequest:
    """从历史记录重建 RAG 更新所需的多城市请求。"""
    segments = getattr(record, "segments", [])
    destinations = [
        CityRequest(
            city=segment.city,
            start_date=segment.start_date,
            end_date=segment.end_date,
        )
        for segment in segments
    ]
    if not destinations:
        destinations = [
            CityRequest(
                city=record.city,
                start_date=record.start_date,
                end_date=record.end_date,
            )
        ]
    return TripRequest(
        destinations=destinations,
        transportation=record.transportation,
        accommodation=record.accommodation,
        preferences=json.loads(record.preferences or "[]"),
        free_text_input=record.free_text_input,
    )


def list_trip_records(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    city: Optional[str] = None,
):
    query = select(TripRecord)
    if city:
        query = (
            query.outerjoin(TripSegment, TripSegment.trip_record_id == TripRecord.id)
            .where(
                or_(
                    TripRecord.city.contains(city),
                    TripSegment.city.contains(city),
                )
            )
            .distinct()
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(desc(TripRecord.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(records), total


def get_trip_record(db: Session, record_id: int) -> Optional[TripRecord]:
    return db.get(TripRecord, record_id)


def update_trip_record(
    db: Session, record_id: int, trip_plan: TripPlan
) -> Optional[TripRecord]:
    record = db.get(TripRecord, record_id)
    if record is None:
        return None
    record.plan_json = trip_plan.model_dump_json()
    _replace_record_segments(record, trip_plan)
    db.commit()
    db.refresh(record)
    return record


def delete_trip_record(db: Session, record_id: int) -> bool:
    record = db.get(TripRecord, record_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True


def trip_record_to_summary(record: TripRecord) -> dict:
    try:
        plan = json.loads(record.plan_json)
    except json.JSONDecodeError:
        plan = {}

    return {
        "id": record.id,
        "city": record.city,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "travel_days": record.travel_days,
        "transportation": record.transportation,
        "accommodation": record.accommodation,
        "preferences": json.loads(record.preferences or "[]"),
        "segments": [
            {
                "city": segment.city,
                "start_date": segment.start_date,
                "end_date": segment.end_date,
                "segment_order": segment.segment_order,
            }
            for segment in record.segments
        ],
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "attraction_count": sum(
            len(day.get("attractions", []))
            for segment in plan.get("segments", [])
            for day in segment.get("days", [])
        ) or sum(
            len(day.get("attractions", [])) for day in plan.get("days", [])
        ),
        "budget_total": (plan.get("budget") or {}).get("total", 0),
    }
