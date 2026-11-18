"""See how a long document is split into overlapping chunks.

Run from the backend folder (venv active):
    python -m scripts.chunking_demo                      # show the chunks
    python -m scripts.chunking_demo --max 400 --overlap 100
    python -m scripts.chunking_demo --store              # also embed + save to Supabase for RAG
"""

import argparse
from pathlib import Path

from app.repositories.document_repository import get_document_repository
from app.services.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS, chunk_text
from app.services.search_service import get_search_service

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "employee_handbook.md"
TITLE = "[demo] Northwind Labs Employee Handbook"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunking demo")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_CHARS, help="max characters per chunk")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP_CHARS, help="overlap characters")
    parser.add_argument("--store", action="store_true", help="embed and save the chunks to Supabase")
    args = parser.parse_args()

    text = SAMPLE.read_text(encoding="utf-8")
    chunks = chunk_text(text, max_chars=args.max, overlap_chars=args.overlap)

    print(f"Document: {SAMPLE.name} — {len(text)} characters (~{len(text) // 4} tokens)")
    print(f"Settings: max {args.max} chars, overlap {args.overlap} chars → {len(chunks)} chunks\n")

    for index, chunk in enumerate(chunks):
        print(f"── chunk {index}  ({len(chunk)} chars) " + "─" * 40)
        print(chunk)
        if index + 1 < len(chunks):
            following = chunks[index + 1]
            shared = next(
                (chunk[i:] for i in range(len(chunk)) if following.startswith(chunk[i:]) and chunk[i:].strip()),
                "",
            )
            if shared:
                print(f"   ↳ overlap repeated at the start of chunk {index + 1}: {shared[:70]!r}…")
        print()

    if args.store:
        repo = get_document_repository()
        existing = repo.find_document_by_title(TITLE)
        if existing:
            repo.delete_document(existing.id)
        added = get_search_service().add_document(TITLE, chunks, source_type="md", file_name=SAMPLE.name)
        print(f"Stored {TITLE!r}: {added.chunk_count} chunks embedded and saved.")


if __name__ == "__main__":
    main()
