"""RAG ingest and retrieval helpers for hotel PDF knowledge bases."""

from hbms.rag.chunking import Chunk, chunk_hotel_pdf_text

__all__ = [
    "Chunk",
    "IngestResult",
    "chunk_hotel_pdf_text",
    "ingest_hotel_pdf",
]


def __getattr__(name: str):
    if name in {"IngestResult", "ingest_hotel_pdf"}:
        from hbms.rag.ingest import IngestResult, ingest_hotel_pdf

        return IngestResult if name == "IngestResult" else ingest_hotel_pdf
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
