from hbms.rag.chunking import chunk_hotel_pdf_text
from hbms.rag.pdf_extract import pages_to_annotated_text
from hbms.rag.pdf_extract import PageText


SAMPLE_ANNOTATED = """[[PAGE 1]]
The Meridian Grand Mumbai
Document Type: Hotel Information

1. Hotel Overview
Hotel Name: The Meridian Grand Mumbai
Check-in: 2:00 PM
Check-out: 12:00 PM

2. Hotel Policies
Check-in Policy
- Standard check-in time is 2:00 PM.
- Guests must provide a valid government-issued photo ID at check-in.

Check-out Policy
- Standard check-out time is 12:00 PM.
- Late check-out after 6:00 PM is charged at the full applicable nightly room rate.

[[PAGE 2]]
3. Cancellation and Modification Policy
- A customer can directly cancel a booking until 24 hours before the scheduled check-in date.
- For a booking with check-in on 20 September, direct cancellation is available until 19 September.

4. Room Categories
Room Type Capacity Price / Night Key Features
Deluxe King 2 guests INR 8,500 King bed, city view
Family Suite 4 guests INR 22,000 Two bedrooms

[[PAGE 3]]
11. Frequently Asked Questions
Q: What time is check-in?
A: Standard check-in is at 2:00 PM.
Q: Is Wi-Fi free?
A: Yes. Complimentary Wi-Fi is available throughout the hotel.
Q: What should the chatbot do if information is not in this document?
A: It should state that the information is not available in the provided hotel document rather than inventing an answer.
"""


def test_chunk_hotel_pdf_text_splits_sections_and_faqs() -> None:
    chunks = chunk_hotel_pdf_text(SAMPLE_ANNOTATED)
    sections = [c.section for c in chunks]

    assert any(s.startswith("1. Hotel Overview") for s in sections)
    assert any("Check-in Policy" in s for s in sections)
    assert any("Check-out Policy" in s for s in sections)
    assert any("Cancellation" in s for s in sections)
    assert any("Room Categories" in s for s in sections)

    faq_chunks = [c for c in chunks if c.metadata["unit_kind"] == "faq"]
    assert len(faq_chunks) >= 3
    assert any("What time is check-in?" in c.chunk_text for c in faq_chunks)
    assert all(c.embedding_text.startswith("[") for c in chunks)


def test_pages_to_annotated_text_preserves_page_markers() -> None:
    annotated = pages_to_annotated_text(
        [
            PageText(page_number=1, text="Hello"),
            PageText(page_number=2, text="World"),
        ]
    )
    assert "[[PAGE 1]]" in annotated
    assert "[[PAGE 2]]" in annotated


def test_size_cap_splits_oversized_section() -> None:
    long_body = "Paragraph one. " * 80
    annotated = f"[[PAGE 1]]\n1. Long Section\n{long_body}"
    chunks = chunk_hotel_pdf_text(annotated, max_chars=200, overlap_chars=40)
    assert len(chunks) > 1
    assert all(len(c.chunk_text) <= 280 for c in chunks)  # allow mild overlap growth
