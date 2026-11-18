"""Ask a question about your stored documents and get a cited answer (RAG).

Uses the "[demo]" handbook stored by scripts.semantic_search_demo (run that once first).

Run from the backend folder (venv active):
    python -m scripts.rag_demo "How many days do I have to return a product?"
"""

import argparse
import textwrap

from app.services.rag_service import get_rag_service


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG demo")
    parser.add_argument("question", nargs="?", default="How many days do I have to return a product?")
    args = parser.parse_args()

    result = get_rag_service().answer(args.question)

    print(f"Question: {args.question}\n")
    print("Answer:")
    print(textwrap.indent(textwrap.fill(result.answer, width=90), "  "))

    if not result.sources:
        print("\n(No document was relevant enough, so the AI was not called.)")
        return

    print("\nSources given to the AI:")
    for source in result.sources:
        mark = "cited" if source.cited else "     "
        chunk = source.chunk
        print(f"  [{source.number}] {mark}  {chunk.similarity:.3f}  {chunk.document_title}, chunk {chunk.chunk_index}")
        print(f"                     {chunk.content}")

    if result.usage:
        print(f"\nModel: {result.model} | tokens: {result.usage.input_tokens} in, "
              f"{result.usage.output_tokens} out, {result.usage.total_tokens} total")


if __name__ == "__main__":
    main()
