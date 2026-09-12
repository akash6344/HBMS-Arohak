"""Heading/section-aware chunking for hotel policy PDFs.

Strategy (selected after literature review):
- Prefer numbered sections and named subsections over fixed windows.
- Keep FAQ as one Q+A pair per chunk.
- Keep compact tables (room categories) intact.
- Recursively size-cap oversized sections with light overlap.
- Prefix each chunk with its section title for embedding context.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_PAGE_MARKER = re.compile(r"\[\[PAGE\s+(\d+)\]\]")
_SECTION_HEADING = re.compile(r"^(\d+)\.\s+(.+)$")
_SUBSECTION_HEADING = re.compile(
    r"^(Check-in Policy|Check-out Policy|Guest and Occupancy Policy|"
    r"Room Categories|Room Amenities|Hotel Facilities|"
    r"Parking and Transportation|Food and Beverage|"
    r"Wi-Fi and Connectivity|Accessibility|"
    r"Frequently Asked Questions|RAG Grounding Rules for Candidates)$",
    re.IGNORECASE,
)
_FAQ_QUESTION = re.compile(r"^Q:\s*(.+)$", re.IGNORECASE)
_FAQ_ANSWER = re.compile(r"^A:\s*(.+)$", re.IGNORECASE)

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 180


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_text: str
    embedding_text: str
    section: str
    page_start: int
    page_end: int
    chunk_index: int
    metadata: dict[str, str | int | bool]


def chunk_hotel_pdf_text(
    annotated_text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    """Chunk annotated PDF text produced by ``pages_to_annotated_text``."""
    units = _split_into_units(annotated_text)
    chunks: list[Chunk] = []
    for unit in units:
        pieces = _size_cap(unit["body"], max_chars=max_chars, overlap_chars=overlap_chars)
        total_pieces = len(pieces)
        for piece_index, piece in enumerate(pieces):
            section = unit["section"]
            embedding_text = f"[{section}]\n{piece}".strip()
            page_start, page_end = _infer_pages(unit["raw_body"], piece, unit["page_hint"])
            chunks.append(
                Chunk(
                    chunk_text=piece,
                    embedding_text=embedding_text,
                    section=section,
                    page_start=page_start,
                    page_end=page_end,
                    chunk_index=len(chunks),
                    metadata={
                        "section_number": unit["section_number"],
                        "unit_kind": unit["kind"],
                        "piece_index": piece_index,
                        "piece_count": total_pieces,
                    },
                )
            )
    return chunks


def _split_into_units(annotated_text: str) -> list[dict[str, str | int]]:
    lines = annotated_text.splitlines()
    current_section_number = "0"
    current_section_title = "Document"
    current_kind = "section"
    buffer: list[str] = []
    page_hint = 1
    units: list[dict[str, str | int]] = []

    def flush() -> None:
        nonlocal buffer
        body = "\n".join(buffer).strip()
        body = _PAGE_MARKER.sub("", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if not body:
            buffer = []
            return
        section = (
            f"{current_section_number}. {current_section_title}"
            if current_section_number != "0"
            else current_section_title
        )
        if current_kind == "faq":
            units.extend(_faq_units(body, section, current_section_number, page_hint))
        else:
            units.append(
                {
                    "section": section,
                    "section_number": current_section_number,
                    "kind": current_kind,
                    "body": body,
                    "raw_body": "\n".join(buffer),
                    "page_hint": page_hint,
                }
            )
        buffer = []

    for line in lines:
        page_match = _PAGE_MARKER.match(line.strip())
        if page_match:
            page_hint = int(page_match.group(1))
            continue

        section_match = _SECTION_HEADING.match(line.strip())
        if section_match:
            flush()
            current_section_number = section_match.group(1)
            current_section_title = section_match.group(2).strip()
            current_kind = "faq" if _is_faq_section(current_section_title) else "section"
            continue

        subsection_match = _SUBSECTION_HEADING.match(line.strip())
        if subsection_match and current_section_number != "0":
            # Nested policy headings under an already-numbered parent.
            flush()
            current_section_title = subsection_match.group(1).strip()
            current_kind = "subsection"
            continue

        buffer.append(line)

    flush()
    return units


def _is_faq_section(title: str) -> bool:
    lowered = title.lower()
    return "faq" in lowered or "frequently asked" in lowered


def _faq_units(
    body: str,
    section: str,
    section_number: str,
    page_hint: int,
) -> list[dict[str, str | int]]:
    units: list[dict[str, str | int]] = []
    question: str | None = None
    answer_lines: list[str] = []

    def flush_qa() -> None:
        nonlocal question, answer_lines
        if not question:
            answer_lines = []
            return
        answer = " ".join(answer_lines).strip()
        text = f"Q: {question}"
        if answer:
            text = f"{text}\nA: {answer}"
        units.append(
            {
                "section": f"{section} / {question}",
                "section_number": section_number,
                "kind": "faq",
                "body": text,
                "raw_body": text,
                "page_hint": page_hint,
            }
        )
        question = None
        answer_lines = []

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        q_match = _FAQ_QUESTION.match(stripped)
        if q_match:
            flush_qa()
            question = q_match.group(1).strip()
            continue
        a_match = _FAQ_ANSWER.match(stripped)
        if a_match and question is not None:
            answer_lines.append(a_match.group(1).strip())
            continue
        if question is not None:
            answer_lines.append(stripped)

    flush_qa()
    return units


def _size_cap(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, max_chars=max_chars, overlap_chars=overlap_chars, separators=separators)


def _recursive_split(
    text: str,
    *,
    max_chars: int,
    overlap_chars: int,
    separators: list[str],
) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    if not separators:
        return _window_split(text, max_chars=max_chars, overlap_chars=overlap_chars)

    separator = separators[0]
    parts = text.split(separator) if separator else list(text)
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = part if not current else f"{current}{separator}{part}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.extend(
                _recursive_split(
                    current,
                    max_chars=max_chars,
                    overlap_chars=overlap_chars,
                    separators=separators[1:],
                )
            )
        if len(part) > max_chars:
            chunks.extend(
                _recursive_split(
                    part,
                    max_chars=max_chars,
                    overlap_chars=overlap_chars,
                    separators=separators[1:],
                )
            )
            current = ""
        else:
            current = part

    if current:
        chunks.extend(
            _recursive_split(
                current,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
                separators=separators[1:],
            )
        )

    return _apply_overlap(chunks, overlap_chars=overlap_chars)


def _window_split(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    step = max(max_chars - overlap_chars, 1)
    return [text[i : i + max_chars].strip() for i in range(0, len(text), step) if text[i : i + max_chars].strip()]


def _apply_overlap(chunks: list[str], *, overlap_chars: int) -> list[str]:
    if overlap_chars <= 0 or len(chunks) <= 1:
        return [c.strip() for c in chunks if c.strip()]

    overlapped: list[str] = []
    previous_tail = ""
    for chunk in chunks:
        body = chunk.strip()
        if not body:
            continue
        if previous_tail and not body.startswith(previous_tail):
            body = f"{previous_tail} {body}".strip()
        overlapped.append(body)
        previous_tail = body[-overlap_chars:] if len(body) > overlap_chars else body
    return overlapped


def _infer_pages(raw_body: str, piece: str, page_hint: int) -> tuple[int, int]:
    markers = [int(m.group(1)) for m in _PAGE_MARKER.finditer(raw_body)]
    if not markers:
        return page_hint, page_hint

    # Prefer pages that appear near the piece content in the raw buffer.
    piece_key = piece[:80]
    idx = raw_body.find(piece_key)
    if idx < 0:
        return min(markers), max(markers)

    preceding = [m for m in _PAGE_MARKER.finditer(raw_body) if m.start() <= idx]
    if preceding:
        page = int(preceding[-1].group(1))
        return page, page
    return min(markers), max(markers)
