"""本地 Embedding + ChromaDB 的旅行知识检索服务。"""

import os
import re
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_settings
from ..models.schemas import TripPlan, TripRequest


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
CHROMA_DIR = DATA_DIR / "chroma"

_KNOWLEDGE_COLLECTION = "trip_knowledge"
_HISTORY_COLLECTION = "trip_history"
_CITY_NAME_MAP = {
    "shenzhen": "深圳",
    "beijing": "北京",
    "shanghai": "上海",
    "guangzhou": "广州",
}


def _create_embeddings(settings):
    if settings.embedding_provider.lower() != "local":
        return None
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "本地 Embedding 依赖未安装，请安装 sentence-transformers 和 langchain-huggingface"
        ) from exc
    return HuggingFaceEmbeddings(
        model_name=settings.local_embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


class RagService:
    def __init__(self):
        self.settings = get_settings()
        self._embedding = None
        self._knowledge_store = None
        self._history_store = None
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
            separators=["\n## ", "\n### ", "\n- ", "\n", "。", "；", " "],
        )
        self._init()

    def _init(self) -> None:
        if self.settings.embedding_provider.lower() != "local":
            return
        try:
            from langchain_chroma import Chroma

            os.makedirs(CHROMA_DIR, exist_ok=True)
            self._embedding = _create_embeddings(self.settings)
            self._knowledge_store = Chroma(
                collection_name=_KNOWLEDGE_COLLECTION,
                embedding_function=self._embedding,
                persist_directory=str(CHROMA_DIR),
            )
            self._history_store = Chroma(
                collection_name=_HISTORY_COLLECTION,
                embedding_function=self._embedding,
                persist_directory=str(CHROMA_DIR),
            )
        except Exception:
            self._embedding = None
            self._knowledge_store = None
            self._history_store = None

    @property
    def enabled(self) -> bool:
        return self._embedding is not None

    def _new_store(self, collection_name: str):
        from langchain_chroma import Chroma

        return Chroma(
            collection_name=collection_name,
            embedding_function=self._embedding,
            persist_directory=str(CHROMA_DIR),
        )

    def _load_knowledge_documents(self) -> list[Document]:
        documents = []
        for md_path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            city = _CITY_NAME_MAP.get(md_path.stem, md_path.stem)
            content = md_path.read_text(encoding="utf-8")
            for chunk in self._text_splitter.split_text(content):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={"city": city, "source": md_path.name},
                    )
                )
        return documents

    def ensure_knowledge_index(self) -> bool:
        if not self.enabled:
            return False
        try:
            if self._knowledge_store.similarity_search("测试", k=1):
                return True
        except Exception:
            pass
        return self.build_knowledge_index()["success"]

    def build_knowledge_index(self) -> dict:
        if not self.enabled:
            return {"success": False, "message": "RAG 未启用", "chunks": 0}
        documents = self._load_knowledge_documents()
        if not documents:
            return {"success": True, "message": "知识目录为空", "chunks": 0}
        try:
            self._knowledge_store.delete_collection()
            self._knowledge_store = self._new_store(_KNOWLEDGE_COLLECTION)
            self._knowledge_store.add_documents(documents)
            return {
                "success": True,
                "message": f"已索引 {len(documents)} 个文本块",
                "chunks": len(documents),
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "chunks": 0}

    def add_history_plan(
        self, record_id: int, request: TripRequest, trip_plan: TripPlan
    ) -> bool:
        if not self.enabled:
            return False
        try:
            self._history_store.add_documents(
                [
                    Document(
                        page_content=self._plan_to_text(request, trip_plan),
                        metadata={"record_id": record_id, "city": request.city},
                    )
                ],
                ids=[self._history_document_id(record_id)],
            )
            return True
        except Exception:
            return False

    def update_history_plan(
        self, record_id: int, request: TripRequest, trip_plan: TripPlan
    ) -> bool:
        if not self.enabled:
            return False
        try:
            document_id = self._history_document_id(record_id)
            self._history_store.delete(ids=[document_id])
            self._history_store.add_documents(
                [
                    Document(
                        page_content=self._plan_to_text(request, trip_plan),
                        metadata={"record_id": record_id, "city": request.city},
                    )
                ],
                ids=[document_id],
            )
            return True
        except Exception:
            return False

    def delete_history_plan(self, record_id: int) -> bool:
        if not self.enabled:
            return False
        try:
            self._history_store.delete(ids=[self._history_document_id(record_id)])
            return True
        except Exception:
            return False

    @staticmethod
    def _history_document_id(record_id: int) -> str:
        return f"history-{record_id}"

    @staticmethod
    def _plan_to_text(request: TripRequest, trip_plan: TripPlan) -> str:
        lines = [
            f"{request.city} {request.travel_days}天旅行计划",
            f"日期: {request.start_date} 至 {request.end_date}",
            f"交通: {request.transportation}, 住宿: {request.accommodation}",
            f"偏好: {','.join(request.preferences) if request.preferences else '无'}",
        ]
        for day in trip_plan.days:
            attractions = "、".join(attraction.name for attraction in day.attractions)
            lines.append(f"第{day.day_index + 1}天: {attractions}")
        if trip_plan.budget:
            lines.append(f"总预算: {trip_plan.budget.total}元")
        return "\n".join(lines)

    def retrieve(self, query: str, city: Optional[str] = None, k: int = 3) -> list[str]:
        if not self.enabled:
            return []
        results = []
        try:
            if city:
                docs = self._knowledge_store.similarity_search(
                    query, k=k, filter={"city": city}
                )
                results.extend(
                    f"[知识库-{doc.metadata.get('city')}] {doc.page_content}"
                    for doc in docs
                )
            docs = self._history_store.similarity_search(query, k=2)
            results.extend(f"[历史行程] {doc.page_content}" for doc in docs)
        except Exception:
            return results
        return results

    def build_rag_context(self, request: TripRequest, top_k: int = 3) -> str:
        if not self.enabled:
            return ""
        query = (
            f"{request.city} {request.travel_days}天旅行 "
            f"{','.join(request.preferences) if request.preferences else ''} "
            f"{request.free_text_input or ''}"
        )
        chunks = self.retrieve(query, city=request.city, k=top_k)
        if not chunks:
            return ""
        return (
            "## 检索到的相关知识 (供你参考, 让行程更真实/贴合当地实际):\n"
            + "\n\n".join(f"- {chunk}" for chunk in chunks)
        )

    def get_knowledge_attractions(self, city: str, max_names: int = 5) -> list[str]:
        if not self.enabled:
            return []
        try:
            docs = self._knowledge_store.similarity_search(
                f"{city} 必去景点 门票 交通 打卡", k=3, filter={"city": city}
            )
            names = []
            for doc in docs:
                for match in re.finditer(r"^###\s+(.+)$", doc.page_content, re.M):
                    name = match.group(1).strip()
                    if name and name not in names:
                        names.append(name)
            return names[:max_names]
        except Exception:
            return []

    def get_attraction_rag_text(
        self, name: str, city: str, max_chars: int = 320
    ) -> str:
        if not self.enabled:
            return ""
        try:
            docs = self._knowledge_store.similarity_search(
                f"{city} {name} 门票 开放时间 交通 避坑 打卡",
                k=1,
                filter={"city": city},
            )
            if not docs:
                return ""
            lines = []
            for line in docs[0].page_content.splitlines():
                line = line.strip()
                if line and not line.startswith("##") and not line.startswith("###"):
                    lines.append(line)
            return "\n".join(lines).strip()[:max_chars]
        except Exception:
            return ""


_rag_service: Optional[RagService] = None


def get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
