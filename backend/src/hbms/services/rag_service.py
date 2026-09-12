"""Grounded RAG answers from hotel PDF chunks."""

from __future__ import annotations

from dataclasses import dataclass
import time

from fastapi import HTTPException, status
from mistralai import Mistral
from mistralai.models import SDKError

from hbms.core.config import Settings, get_settings
from hbms.domain.schemas import AuthenticatedPrincipal
from hbms.rag.embeddings import EmbeddingError
from hbms.rag.retrieve import RetrievedChunk, list_hotels_with_documents, retrieve_hotel_chunks
from hbms.repositories.hotel_repository import HotelRepository

UNAVAILABLE_MESSAGE = (
    "That information is not available in the provided hotel document."
)

SYSTEM_PROMPT = """You are a hotel information assistant.
Answer ONLY using the provided document excerpts.
If the excerpts do not contain the answer, reply exactly with:
That information is not available in the provided hotel document.
Do not invent policies, prices, timings, or amenities.
Keep answers concise and factual.
When helpful, mention the section name from the excerpts.
"""


@dataclass(frozen=True, slots=True)
class Citation:
    section: str
    page_start: int
    page_end: int
    score: float
    excerpt: str


@dataclass(frozen=True, slots=True)
class RagAnswer:
    answer: str
    grounded: bool
    hotel_id: str
    organization_id: str
    citations: list[Citation]


class RagService:
    @staticmethod
    async def list_knowledge_hotels(_: AuthenticatedPrincipal) -> list[dict]:
        return await list_hotels_with_documents()

    @staticmethod
    async def ask(
        principal: AuthenticatedPrincipal,
        *,
        hotel_id: str,
        question: str,
        settings: Settings | None = None,
    ) -> RagAnswer:
        _ = principal  # auth already enforced by router; all signed-in roles may ask
        cfg = settings or get_settings()
        if not cfg.mistral_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mistral API key is not configured.",
            )

        cleaned = question.strip()
        if len(cleaned) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is too short.",
            )

        hotel = await HotelRepository.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
        organization_id = str(hotel["organization_id"])

        try:
            chunks = await retrieve_hotel_chunks(
                organization_id=organization_id,
                hotel_id=hotel_id,
                question=cleaned,
                settings=cfg,
            )
        except EmbeddingError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        if not chunks:
            return RagAnswer(
                answer=UNAVAILABLE_MESSAGE,
                grounded=False,
                hotel_id=hotel_id,
                organization_id=organization_id,
                citations=[],
            )

        answer_text = _generate_grounded_answer(cleaned, chunks, settings=cfg)
        grounded = UNAVAILABLE_MESSAGE.lower() not in answer_text.lower()
        citations = [
            Citation(
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                score=round(chunk.score, 4),
                excerpt=chunk.chunk_text[:280],
            )
            for chunk in chunks
        ]
        return RagAnswer(
            answer=answer_text.strip(),
            grounded=grounded,
            hotel_id=hotel_id,
            organization_id=organization_id,
            citations=citations if grounded else [],
        )


def _extractive_answer(chunks: list[RetrievedChunk]) -> str:
    """Fallback answer built only from retrieved text (no model invention)."""
    top = chunks[0]
    text = top.chunk_text.strip()
    if "A:" in text:
        answer_part = text.split("A:", 1)[1].strip()
        if answer_part:
            return f"{answer_part} (from {top.section})"
    return f"{text} (from {top.section})"


def _generate_grounded_answer(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    settings: Settings,
) -> str:
    context_blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Excerpt {index}] Section: {chunk.section} "
            f"(pages {chunk.page_start}-{chunk.page_end})\n{chunk.chunk_text}"
        )
    user_prompt = (
        "Document excerpts:\n"
        + "\n\n".join(context_blocks)
        + f"\n\nCustomer question: {question}\n"
        + "Answer using only the excerpts above."
    )

    client = Mistral(api_key=settings.mistral_api_key)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.complete(
                model=settings.mistral_chat_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if not response.choices:
                return UNAVAILABLE_MESSAGE
            content = response.choices[0].message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            return UNAVAILABLE_MESSAGE
        except SDKError as exc:
            last_error = exc
            message = str(exc).lower()
            if "429" in message or "rate" in message:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        except Exception as exc:  # noqa: BLE001 - fall back to extractive answer
            last_error = exc
            break

    # Still grounded: answer from retrieved chunks only if the chat model is unavailable.
    if last_error is not None and chunks and chunks[0].score >= 0.7:
        return _extractive_answer(chunks)
    if last_error is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hotel info assistant is temporarily unavailable. Please try again.",
        ) from last_error
    return UNAVAILABLE_MESSAGE
