"""Tenant-scoped retrieval over hotel document chunk embeddings."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from hbms.core.config import Settings, get_settings
from hbms.rag.embeddings import embed_query
from hbms.repositories.hotel_document_repository import HotelDocumentRepository

DEFAULT_TOP_K = 4
DEFAULT_MIN_SCORE = 0.55


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_text: str
    section: str
    page_start: int
    page_end: int
    score: float
    chunk_index: int


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def retrieve_hotel_chunks(
    *,
    organization_id: str,
    hotel_id: str,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    """Retrieve top chunks for a hotel. Filter by org+hotel is applied in the DB query."""
    cfg = settings or get_settings()
    docs = await HotelDocumentRepository.list_chunks_for_hotel(
        organization_id=organization_id,
        hotel_id=hotel_id,
        limit=500,
    )
    if not docs:
        return []

    query_vector = embed_query(question, settings=cfg)
    scored: list[RetrievedChunk] = []
    for doc in docs:
        embedding = doc.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            continue
        score = _cosine(query_vector, embedding)
        if score < min_score:
            continue
        scored.append(
            RetrievedChunk(
                chunk_text=str(doc.get("chunk_text") or ""),
                section=str(doc.get("section") or "Unknown"),
                page_start=int(doc.get("page_start") or 1),
                page_end=int(doc.get("page_end") or 1),
                score=score,
                chunk_index=int(doc.get("chunk_index") or 0),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]


async def list_hotels_with_documents() -> list[dict[str, Any]]:
    return await HotelDocumentRepository.list_hotels_with_documents()
