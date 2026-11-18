"""Create sample PDF and DOCX files in backend/samples/ for trying the ingestion pipeline.

Run from the backend folder (venv active):
    python -m scripts.make_sample_files
"""

import re
from pathlib import Path

import docx

from scripts.simple_pdf import build_simple_pdf

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def make_handbook_pdf() -> Path:
    """The Markdown handbook as a PDF: two '##' sections per page, so pages differ."""
    markdown = (SAMPLES / "employee_handbook.md").read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## )", markdown)
    pages = ["\n\n".join(sections[i : i + 2]) for i in range(0, len(sections), 2)]
    pages = [page.replace("#", "").strip() for page in pages]
    path = SAMPLES / "northwind_handbook.pdf"
    path.write_bytes(build_simple_pdf(pages))
    return path


def make_faq_docx() -> Path:
    document = docx.Document()
    document.add_heading("Northwind Labs Office FAQ", level=1)
    document.add_paragraph(
        "This FAQ is fictional and exists only to test Shema AI's document upload."
    )
    document.add_heading("Where can I park?", level=2)
    document.add_paragraph(
        "Employees can park for free in the basement garage. Visitor parking is on level 1 "
        "and must be booked at reception one day in advance."
    )
    document.add_heading("Is there a canteen?", level=2)
    document.add_paragraph(
        "The canteen on the ground floor serves lunch from 12:00 to 14:30. Lunch is free on "
        "Fridays; on other days it costs 120 rupees."
    )
    document.add_heading("Office opening hours", level=2)
    table = document.add_table(rows=3, cols=2)
    for row, (day, hours) in enumerate([("Day", "Hours"), ("Monday-Friday", "07:00-21:00"), ("Saturday", "09:00-14:00")]):
        table.cell(row, 0).text = day
        table.cell(row, 1).text = hours
    path = SAMPLES / "office_faq.docx"
    document.save(path)
    return path


if __name__ == "__main__":
    for created in (make_handbook_pdf(), make_faq_docx()):
        print(f"Created {created.relative_to(SAMPLES.parent)} ({created.stat().st_size} bytes)")
