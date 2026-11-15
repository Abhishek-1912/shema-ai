"""See embeddings with your own eyes: text → numbers → similarity → semantic search.

Run from the backend folder (venv active):
    python -m scripts.embeddings_demo
    python -m scripts.embeddings_demo "Why did investors lose money?"
"""

import argparse
import math

from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service

SENTENCES = [
    "The cat sat on the mat.",
    "A kitten was resting on the rug.",
    "Dogs love playing fetch in the park.",
    "The stock market fell sharply today.",
    "Investors lost money as share prices dropped.",
    "Python is a popular programming language.",
    "I write my backend code in FastAPI.",
]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """How much two vectors point in the same direction: 1 = same, 0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))
    return dot / (length_a * length_b)


def shared_words(a: str, b: str) -> set[str]:
    """Words two sentences have in common (what a simple keyword search would use)."""
    clean = lambda text: {w.strip(".,?!").lower() for w in text.split()}  # noqa: E731
    return clean(a) & clean(b) - {"the", "a", "on", "in", "was", "my", "is", "as"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Embeddings demo")
    parser.add_argument("query", nargs="?", default="Where is the little cat sleeping?")
    args = parser.parse_args()

    settings = get_settings()
    embedder = get_embedding_service()

    # 1. Turn ALL texts into vectors. The service batches them into as few requests as possible.
    texts = SENTENCES + [args.query]
    vectors = embedder.embed_texts(texts)
    sentence_vectors, query_vector = vectors[:-1], vectors[-1]

    # 2. What does an embedding look like?
    first = sentence_vectors[0]
    print(f"Model: {settings.embedding_model}")
    print(f'"{SENTENCES[0]}" became {len(first)} numbers. The first 5:')
    print("   ", [round(x, 4) for x in first[:5]], "...")

    # 3. Compare pairs of sentences.
    print("\nSimilarity between pairs (1.0 = same meaning):")
    pairs = [(0, 1), (0, 3), (3, 4), (5, 6), (2, 4)]
    for i, j in pairs:
        score = cosine_similarity(sentence_vectors[i], sentence_vectors[j])
        common = shared_words(SENTENCES[i], SENTENCES[j]) or "none"
        print(f"  {score:.3f}  {SENTENCES[i]!r:48} vs {SENTENCES[j]!r}")
        print(f"         shared keywords: {common}")

    # 4. Semantic search: rank every sentence by meaning, not by matching words.
    print(f'\nSemantic search for: "{args.query}"')
    ranked = sorted(
        ((cosine_similarity(query_vector, vec), text) for vec, text in zip(sentence_vectors, SENTENCES, strict=True)),
        reverse=True,
    )
    for rank, (score, text) in enumerate(ranked, start=1):
        print(f"  {rank}. {score:.3f}  {text}")


if __name__ == "__main__":
    main()
