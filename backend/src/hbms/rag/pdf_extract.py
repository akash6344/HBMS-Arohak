"""Page-aware PDF text extraction for hotel knowledge PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader

_BOILERPLATE_LINE = re.compile(
    r"^(AROHAK Hackathon Hiring|Page\s+\d+|RAG Chatbot\s*[—\-].*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int  # 1-based
    text: str


def extract_pdf_pages(pdf_path: Path | str) -> list[PageText]:
    path = Path(pdf_path)
    if not path.is_file():
        msg = f"PDF not found: {path}"
        raise FileNotFoundError(msg)

    reader = PdfReader(str(path))
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        cleaned = _clean_page_text(raw)
        if cleaned:
            pages.append(PageText(page_number=index + 1, text=cleaned))
    return pages


def pages_to_annotated_text(pages: list[PageText]) -> str:
    """Join pages with markers so chunker can recover page numbers."""
    blocks: list[str] = []
    for page in pages:
        blocks.append(f"[[PAGE {page.page_number}]]\n{page.text}")
    return "\n\n".join(blocks)


def _clean_page_text(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if _BOILERPLATE_LINE.match(stripped):
            continue
        # Normalize odd PDF bullets / private-use glyphs to a consistent marker.
        normalized = (
            stripped.replace("\uf07f", "-")
            .replace("•", "-")
            .replace("\u25cf", "-")
            .replace("\u25e6", "-")
        )
        normalized = re.sub(r"^[\u0000-\u001f\ufffd]+\s*", "- ", normalized)
        normalized = re.sub(r"^[\?\x7f]\s+", "- ", normalized)
        lines.append(normalized)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
