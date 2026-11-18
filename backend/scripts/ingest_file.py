"""Ingest a file into the knowledge base: extract → chunk → embed → store.

Run from the backend folder (venv active):
    python -m scripts.ingest_file samples/northwind_handbook.pdf
    python -m scripts.ingest_file samples/office_faq.docx --title "Office FAQ" --replace
"""

import argparse
import time
from pathlib import Path

from app.repositories.document_repository import get_document_repository
from app.services.extraction import ExtractionError
from app.services.ingestion_service import get_ingestion_service, title_from_file_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a document")
    parser.add_argument("path", type=Path)
    parser.add_argument("--title", help="document title (default: from the file name)")
    parser.add_argument("--replace", action="store_true", help="delete a document with the same title first")
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"File not found: {args.path}")
        return

    title = args.title or title_from_file_name(args.path.name)
    if args.replace:
        repo = get_document_repository()
        existing = repo.find_document_by_title(title)
        if existing:
            repo.delete_document(existing.id)
            print(f"Deleted the old {title!r}.")

    started = time.perf_counter()
    try:
        result = get_ingestion_service().ingest_file(args.path.name, args.path.read_bytes(), title=title)
    except ExtractionError as error:
        print(f"Could not ingest {args.path.name}: {error}")
        return

    print(
        f"Ingested {result.document.title!r} ({result.document.source_type}): "
        f"{result.page_count} page(s) → {result.chunk_count} chunks "
        f"in {time.perf_counter() - started:.1f} s"
    )


if __name__ == "__main__":
    main()
