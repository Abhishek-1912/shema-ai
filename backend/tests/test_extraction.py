"""Unit tests for text extraction. Real PDF/DOCX files are generated in memory."""

from io import BytesIO

import docx
import pytest

from app.services.extraction import ExtractionError, extract_text, source_type_for
from scripts.simple_pdf import build_simple_pdf


def make_docx(paragraphs: list[str], table: list[list[str]] | None = None) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table:
        word_table = document.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, value in enumerate(row):
                word_table.cell(r, c).text = value
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# --- File types ---------------------------------------------------------------------

@pytest.mark.parametrize(
    ("name", "expected"),
    [("a.pdf", "pdf"), ("A.PDF", "pdf"), ("b.docx", "docx"), ("c.txt", "txt"), ("d.md", "md"), ("e.markdown", "md")],
)
def test_source_type_from_extension(name: str, expected: str) -> None:
    assert source_type_for(name) == expected


@pytest.mark.parametrize("name", ["virus.exe", "photo.png", "old.doc", "no_extension"])
def test_unsupported_types_are_rejected(name: str) -> None:
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        extract_text(name, b"data")


def test_empty_file_is_rejected() -> None:
    with pytest.raises(ExtractionError, match="empty"):
        extract_text("notes.txt", b"")


# --- PDF --------------------------------------------------------------------------------

def test_pdf_text_is_extracted_per_page_with_page_numbers() -> None:
    pdf = build_simple_pdf(["Refunds take 30 days.", "Leave is 15 days per year."])

    result = extract_text("policy.pdf", pdf)

    assert result.source_type == "pdf"
    assert [p.page_number for p in result.pages] == [1, 2]
    assert "Refunds take 30 days." in result.pages[0].text
    assert "Leave is 15 days per year." in result.pages[1].text


def test_empty_pdf_pages_are_skipped_but_numbers_stay_correct() -> None:
    pdf = build_simple_pdf(["Page one text.", "", "Page three text."])

    result = extract_text("doc.pdf", pdf)

    assert [p.page_number for p in result.pages] == [1, 3]


def test_pdf_without_any_text_suggests_ocr() -> None:
    pdf = build_simple_pdf(["", ""])

    with pytest.raises(ExtractionError, match="scanned PDF"):
        extract_text("scan.pdf", pdf)


def test_broken_pdf_gives_a_friendly_error() -> None:
    with pytest.raises(ExtractionError, match="could not be read"):
        extract_text("broken.pdf", b"%PDF-1.4 this is not really a pdf")


# --- DOCX ---------------------------------------------------------------------------------

def test_docx_paragraphs_and_tables_are_extracted() -> None:
    data = make_docx(
        ["Remote work policy", "", "Up to three days per week."],
        table=[["Grade", "Days"], ["Junior", "2"]],
    )

    result = extract_text("policy.docx", data)

    assert result.source_type == "docx"
    assert result.pages[0].page_number is None  # Word files have no fixed pages
    text = result.pages[0].text
    assert "Remote work policy\n\nUp to three days per week." in text
    assert "Grade | Days" in text and "Junior | 2" in text


def test_fake_docx_gives_a_friendly_error() -> None:
    with pytest.raises(ExtractionError, match="Word file could not be read"):
        extract_text("fake.docx", b"just some text, not a zip file")


# --- TXT / MD -----------------------------------------------------------------------------

def test_utf8_text_with_bom_is_read() -> None:
    result = extract_text("notes.txt", "﻿Hello – café".encode("utf-8"))

    assert result.pages[0].text == "Hello – café"


def test_windows_encoded_text_is_read() -> None:
    result = extract_text("old.txt", "Price: 5 €".encode("cp1252"))

    assert result.pages[0].text == "Price: 5 €"


def test_markdown_is_read_as_text() -> None:
    result = extract_text("guide.md", b"# Title\n\nSome **bold** text.")

    assert result.source_type == "md"
    assert result.pages[0].text.startswith("# Title")
