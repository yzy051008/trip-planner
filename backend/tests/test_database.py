from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine, init_db
from app.db.models import TripRecord


def test_init_db_creates_trip_records_table_and_is_idempotent():
    init_db()
    init_db()

    inspector = inspect(engine)
    assert "trip_records" in inspector.get_table_names()

    with SessionLocal() as db:
        existing_count = len(db.scalars(select(TripRecord)).all())
        db.add(
            TripRecord(
                city="北京",
                start_date="2026-09-04",
                end_date="2026-09-06",
                travel_days=3,
                transportation="公共交通",
                accommodation="经济型酒店",
                preferences='["历史文化"]',
                free_text_input="少走路",
                plan_json='{"city":"北京","days":[]}',
            )
        )
        db.commit()

        records = db.scalars(select(TripRecord)).all()
        assert len(records) == existing_count + 1
        assert records[-1].city == "北京"
