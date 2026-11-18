"""Text extraction: turn an uploaded file (bytes) into plain text, page by page.

Supported: PDF (with page numbers), DOCX, TXT, MD.
Not supported: scanned PDFs (images of text) — that needs OCR, which we don't do.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

import docx
import pypdf

from app.models.document import SourceType

EXTENSIONS: dict[str, SourceType] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}


class ExtractionError(ValueError):
    """The file can't be turned into text. The message is safe to show to the user."""


class UnsupportedFileTypeError(ExtractionError):
    """The file extension is not one we can read (HTTP 415)."""


class FileTooLargeError(ExtractionError):
    """The file is bigger than the upload limit (HTTP 413)."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None  # 1, 2, 3... for PDFs; None when the format has no pages
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    source_type: SourceType
    pages: list[ExtractedPage]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def source_type_for(file_name: str) -> SourceType:
    extension = PurePath(file_name).suffix.lower()
    if extension not in EXTENSIONS:
        allowed = ", ".join(sorted(EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or file_name}'. Allowed: {allowed}."
        )
    return EXTENSIONS[extension]


def extract_text(file_name: str, data: bytes) -> ExtractedDocument:
    """Pick the right reader from the file extension and return the text per page."""
    source_type = source_type_for(file_name)
    if not data:
        raise ExtractionError("The file is empty.")

    if source_type == "pdf":
        pages = _read_pdf(data)
    elif source_type == "docx":
        pages = [ExtractedPage(None, _read_docx(data))]
    else:
        pages = [ExtractedPage(None, _read_plain_text(data))]

    pages = [page for page in pages if page.text.strip()]  # drop empty pages
    if not pages:
        hint = " It may be a scanned PDF (images only), which needs OCR." if source_type == "pdf" else ""
        raise ExtractionError(f"No text could be found in the file.{hint}")
    return ExtractedDocument(source_type, pages)


# --- Readers ---------------------------------------------------------------------------

def _read_pdf(data: bytes) -> list[ExtractedPage]:
    try:
        reader = pypdf.PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("The PDF is password-protected. Remove the password and try again.")
        return [
            ExtractedPage(page_number=number, text=page.extract_text() or "")
            for number, page in enumerate(reader.pages, start=1)
        ]
    except ExtractionError:
        raise
    except Exception as error:  # pypdf raises many different errors for broken files
        raise ExtractionError("The PDF could not be read. It may be damaged.") from error


def _read_docx(data: bytes) -> str:
    try:
        document = docx.Document(BytesIO(data))
    except Exception as error:  # not a zip / not a Word file
        raise ExtractionError("The Word file could not be read. Is it a real .docx file?") from error

    blocks = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:  # text inside tables, one row per line
        for row in table.rows:
            blocks.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n\n".join(block for block in blocks if block.strip())


def _read_plain_text(data: bytes) -> str:
    # utf-8-sig also removes the invisible "BOM" some Windows editors put at the start.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("The text file uses an unknown character encoding. Save it as UTF-8.")
