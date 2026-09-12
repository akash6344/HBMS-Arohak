"""Persist hotel PDF chunks and embeddings into MongoDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hbms.core.config import Settings, get_settings
from hbms.rag.chunking import Chunk, chunk_hotel_pdf_text
from hbms.rag.embeddings import embed_texts
from hbms.rag.pdf_extract import extract_pdf_pages, pages_to_annotated_text
from hbms.repositories.hotel_document_repository import HotelDocumentRepository


@dataclass(frozen=True, slots=True)
class IngestResult:
    document_id: str
    organization_id: str
    hotel_id: str
    source_file: str
    chunk_count: int
    replaced_previous: bool


async def ingest_hotel_pdf(
    *,
    pdf_path: Path | str,
    organization_id: str,
    hotel_id: str,
    uploaded_by: str | None = None,
    version: str = "1.0",
    replace_existing: bool = True,
    dry_run: bool = False,
    settings: Settings | None = None,
) -> IngestResult | list[Chunk]:
    """Extract → chunk → embed → store a hotel knowledge PDF.

    When ``dry_run=True``, returns the chunks without calling Mistral or Mongo.
    """
    path = Path(pdf_path)
    pages = extract_pdf_pages(path)
    annotated = pages_to_annotated_text(pages)
    chunks = chunk_hotel_pdf_text(annotated)
    if dry_run:
        return chunks

    cfg = settings or get_settings()
    embedding_inputs = [chunk.embedding_text for chunk in chunks]
    vectors = embed_texts(embedding_inputs, settings=cfg)

    replaced_previous = False
    if replace_existing:
        existing = await HotelDocumentRepository.find_by_source(
            organization_id=organization_id,
            hotel_id=hotel_id,
            source_file=path.name,
        )
        if existing is not None:
            await HotelDocumentRepository.delete_document_and_chunks(str(existing["_id"]))
            replaced_previous = True

    document = await HotelDocumentRepository.create_document(
        organization_id=organization_id,
        hotel_id=hotel_id,
        source_file=path.name,
        version=version,
        uploaded_by=uploaded_by,
        page_count=len(pages),
        chunk_count=len(chunks),
        metadata={
            "embedding_model": cfg.mistral_embed_model,
            "embedding_dimensions": 1024,
            "chunking_strategy": "section_aware_recursive",
            "ingested_at": datetime.now(UTC).isoformat(),
        },
    )
    document_id = str(document["_id"])

    chunk_docs: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk_docs.append(
            {
                "organization_id": organization_id,
                "hotel_id": hotel_id,
                "document_id": document_id,
                "chunk_text": chunk.chunk_text,
                "embedding_text": chunk.embedding_text,
                "embedding": vector,
                "section": chunk.section,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata,
            }
        )
    await HotelDocumentRepository.insert_chunks(chunk_docs)

    return IngestResult(
        document_id=document_id,
        organization_id=organization_id,
        hotel_id=hotel_id,
        source_file=path.name,
        chunk_count=len(chunks),
        replaced_previous=replaced_previous,
    )
