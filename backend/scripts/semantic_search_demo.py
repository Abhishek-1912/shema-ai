"""Semantic search with pgvector: store a small knowledge base once, then search it.

Run from the backend folder (venv active):
    python -m scripts.semantic_search_demo "How do I get my money back?"
    python -m scripts.semantic_search_demo --reset      # delete and re-load the sample documents
"""

import argparse
import time

from app.repositories.document_repository import get_document_repository
from app.services.search_service import get_search_service

# A tiny fictional company handbook. Each document is already split into chunks
# (Module 04 will do this splitting automatically for real files).
SAMPLE_DOCUMENTS: dict[str, list[str]] = {
    "[demo] Refund policy": [
        "Customers can return any product within 30 days of delivery for a full refund.",
        "Damaged items must be reported within 7 days with a photo of the damage.",
        "Refunds are paid back to the original payment method within 5 business days.",
    ],
    "[demo] Leave policy": [
        "New employees receive 15 days of paid annual leave in their first year.",
        "Sick leave requires a doctor's note when it lasts longer than two days.",
        "Unused annual leave can be carried over to the next year, up to 5 days.",
    ],
    "[demo] IT security policy": [
        "Passwords must be at least 12 characters long and changed every 90 days.",
        "Never share your login details with anyone, including the IT team.",
        "Report lost or stolen laptops to the IT help desk immediately.",
    ],
}


def load_sample_documents(reset: bool) -> None:
    repo = get_document_repository()
    search = get_search_service()

    for title, chunks in SAMPLE_DOCUMENTS.items():
        existing = repo.find_document_by_title(title)
        if existing and not reset:
            continue  # already stored: embeddings are NOT recomputed
        if existing:
            repo.delete_document(existing.id)
        added = search.add_document(title, chunks)
        print(f"Stored {title!r}: {added.chunk_count} chunks embedded and saved.")


def main() -> None:
    parser = argparse.ArgumentParser(description="pgvector semantic search demo")
    parser.add_argument("query", nargs="?", default="How do I get my money back?")
    parser.add_argument("--reset", action="store_true", help="re-load the sample documents")
    args = parser.parse_args()

    load_sample_documents(reset=args.reset)

    started = time.perf_counter()
    results = get_search_service().search(args.query, top_k=3)
    elapsed = time.perf_counter() - started

    print(f'\nSearch: "{args.query}"  ({elapsed:.2f} s: embed the question + SQL search)')
    for rank, match in enumerate(results, start=1):
        print(f"  {rank}. {match.similarity:.3f}  [{match.document_title}, chunk {match.chunk_index}]")
        print(f"         {match.content}")


if __name__ == "__main__":
    main()
