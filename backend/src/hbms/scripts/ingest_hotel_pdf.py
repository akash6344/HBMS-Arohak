"""Ingest a hotel knowledge PDF into MongoDB for RAG.

Dry-run (chunk only, no API/DB writes):
  python -m hbms.scripts.ingest_hotel_pdf --pdf AROHAK_Hotel_Information_For_RAG.pdf --dry-run

Full ingest (requires MISTRAL_API_KEY and Mongo):
  python -m hbms.scripts.ingest_hotel_pdf \\
    --pdf AROHAK_Hotel_Information_For_RAG.pdf \\
    --organization-id <org_id> \\
    --hotel-id <hotel_id>
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from hbms.core.config import BACKEND_ROOT, get_settings
from hbms.db.mongo import mongo_manager
from hbms.rag.chunking import Chunk
from hbms.rag.ingest import IngestResult, ingest_hotel_pdf


def _default_pdf() -> Path:
    return BACKEND_ROOT / "AROHAK_Hotel_Information_For_RAG.pdf"


def _print_chunks(chunks: list[Chunk]) -> None:
    print(f"Created {len(chunks)} chunks (section-aware strategy)\n")
    for chunk in chunks:
        preview = chunk.chunk_text.replace("\n", " ")
        if len(preview) > 140:
            preview = preview[:137] + "..."
        print(
            f"[{chunk.chunk_index:02d}] p{chunk.page_start}-{chunk.page_end} "
            f"| {chunk.section}\n    {preview}\n"
        )


async def _run(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf).expanduser().resolve()
    if args.dry_run:
        chunks = await ingest_hotel_pdf(
            pdf_path=pdf_path,
            organization_id=args.organization_id or "dry-run-org",
            hotel_id=args.hotel_id or "dry-run-hotel",
            dry_run=True,
        )
        assert isinstance(chunks, list)
        _print_chunks(chunks)
        return

    if not args.organization_id or not args.hotel_id:
        raise SystemExit("--organization-id and --hotel-id are required unless --dry-run")

    settings = get_settings()
    if not settings.mistral_api_key:
        raise SystemExit("Set MISTRAL_API_KEY in backend/.env before full ingest.")

    await mongo_manager.connect()
    try:
        result = await ingest_hotel_pdf(
            pdf_path=pdf_path,
            organization_id=args.organization_id,
            hotel_id=args.hotel_id,
            uploaded_by=args.uploaded_by,
            version=args.version,
            replace_existing=not args.no_replace,
            dry_run=False,
            settings=settings,
        )
        assert isinstance(result, IngestResult)
        print(
            "Ingest complete:\n"
            f"  document_id={result.document_id}\n"
            f"  chunks={result.chunk_count}\n"
            f"  replaced_previous={result.replaced_previous}\n"
            f"  source={result.source_file}"
        )
    finally:
        await mongo_manager.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest hotel PDF for RAG")
    parser.add_argument("--pdf", type=str, default=str(_default_pdf()), help="Path to PDF")
    parser.add_argument("--organization-id", type=str, default=None)
    parser.add_argument("--hotel-id", type=str, default=None)
    parser.add_argument("--uploaded-by", type=str, default=None)
    parser.add_argument("--version", type=str, default="1.0")
    parser.add_argument("--dry-run", action="store_true", help="Chunk only; no embed/store")
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Do not delete a previous version of the same source_file",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
