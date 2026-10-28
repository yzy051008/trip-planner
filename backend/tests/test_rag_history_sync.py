from types import SimpleNamespace

from langchain_core.documents import Document

from app.services.rag_service import RagService


class FakeStore:
    def __init__(self):
        self.deleted = []
        self.added = []

    def delete(self, **kwargs):
        self.deleted.append(kwargs)

    def add_documents(self, documents, ids=None):
        self.added.append((documents, ids))


def make_service(store):
    service = object.__new__(RagService)
    service._embedding = object()
    service._history_store = store
    return service


def test_add_history_plan_uses_record_id_as_stable_document_id():
    store = FakeStore()
    service = make_service(store)
    request = SimpleNamespace(
        city="上海",
        travel_days=1,
        start_date="2026-09-01",
        end_date="2026-09-01",
        transportation="步行",
        accommodation="酒店",
        preferences=[],
    )
    plan = SimpleNamespace(days=[], budget=None)

    assert service.add_history_plan(12, request, plan) is True

    assert store.added[0][1] == ["history-12"]
    assert isinstance(store.added[0][0][0], Document)


def test_add_history_plan_stores_all_segment_cities_in_metadata():
    store = FakeStore()
    service = make_service(store)
    request = SimpleNamespace(
        destinations=[
            SimpleNamespace(city="上海"),
            SimpleNamespace(city="杭州"),
        ],
        city="上海",
        travel_days=3,
        start_date="2026-09-01",
        end_date="2026-09-03",
        transportation="高铁",
        accommodation="酒店",
        preferences=[],
    )
    plan = SimpleNamespace(segments=[], days=[], budget=None)

    assert service.add_history_plan(13, request, plan) is True

    metadata = store.added[0][0][0].metadata
    assert metadata["city"] == "上海"
    assert metadata["cities"] == "上海,杭州"


def test_update_history_plan_replaces_existing_stable_document():
    store = FakeStore()
    service = make_service(store)
    request = SimpleNamespace(
        city="上海",
        travel_days=1,
        start_date="2026-09-01",
        end_date="2026-09-01",
        transportation="步行",
        accommodation="酒店",
        preferences=[],
    )
    plan = SimpleNamespace(days=[], budget=None)

    assert service.update_history_plan(12, request, plan) is True

    assert store.deleted == [{"ids": ["history-12"]}]
    assert store.added[0][1] == ["history-12"]


def test_delete_history_plan_removes_stable_document():
    store = FakeStore()
    service = make_service(store)

    assert service.delete_history_plan(12) is True

    assert store.deleted == [{"ids": ["history-12"]}]
