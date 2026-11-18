"""Compare vector-only and hybrid search side by side, with the RAG threshold applied.

Run from the backend folder (venv active):
    python -m scripts.compare_search KESTREL "EXP-311" "How many days of annual leave do I get?"
"""

import argparse

from app.services.rag_service import DEFAULT_MIN_SIMILARITY
from app.services.search_service import get_search_service


def show(title: str, matches: list) -> None:
    print(f"  {title}: {len(matches)} chunk(s) pass the {DEFAULT_MIN_SIMILARITY} threshold")
    for m in matches[:3]:
        keyword = f"keyword #{m.keyword_rank}" if m.keyword_rank else "no keyword match"
        print(f"     {m.similarity:.3f}  ({keyword:16})  {m.content[:70]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vector vs hybrid search")
    parser.add_argument("queries", nargs="+")
    args = parser.parse_args()
    search = get_search_service()

    for query in args.queries:
        print(f"\n=== {query!r}")
        show("vector", search.search(query, top_k=5, min_similarity=DEFAULT_MIN_SIMILARITY, hybrid=False))
        show("hybrid", search.search(query, top_k=5, min_similarity=DEFAULT_MIN_SIMILARITY, hybrid=True))


if __name__ == "__main__":
    main()
