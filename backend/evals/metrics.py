"""Pure evaluation functions: no AI calls, no database. Easy to unit-test.

Retrieval metrics (for questions that HAVE an answer in the documents):
- hit@k: was the correct chunk among the first k results?            (1 = yes, 0 = no)
- MRR:   Mean Reciprocal Rank = average of 1/rank of the correct chunk (rank 1 → 1.0,
         rank 2 → 0.5, rank 3 → 0.33, not found → 0). Rewards finding it EARLY.

Threshold metrics (what RAG actually sends to the AI after filtering):
- recall:        answerable questions whose correct chunk survives the filter
- refusal rate:  unanswerable questions where NOTHING survives (the AI isn't even asked)
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.models.document import ChunkMatch
from app.services.rag_service import NOT_FOUND_ANSWER

KEYWORD_TOP = 2  # must match keyword_top in hybrid_match_document_chunks()


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    question: str
    expected_text: str | None  # None = the documents don't contain the answer
    answer_contains: list[str] = field(default_factory=list)

    @property
    def answerable(self) -> bool:
        return self.expected_text is not None


def load_cases(path: Path) -> list[EvalCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**case) for case in data["cases"]]


def normalize(text: str) -> str:
    """Lowercase + single spaces, so PDF line breaks don't break matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def contains(chunk_text: str, expected: str) -> bool:
    return normalize(expected) in normalize(chunk_text)


def find_rank(matches: list[ChunkMatch], expected_text: str) -> int | None:
    """1-based position of the first chunk containing the expected text, or None."""
    for position, match in enumerate(matches, start=1):
        if contains(match.content, expected_text):
            return position
    return None


def passes_filter(match: ChunkMatch, threshold: float) -> bool:
    """The same rule as the SQL: similar enough OR one of the best keyword matches."""
    return match.similarity >= threshold or (
        match.keyword_rank is not None and match.keyword_rank <= KEYWORD_TOP
    )


def kept_after_filter(matches: list[ChunkMatch], threshold: float, top_k: int) -> list[ChunkMatch]:
    """What RAG would give the AI: filter by the threshold, then take the first top_k."""
    return [m for m in matches if passes_filter(m, threshold)][:top_k]


def retrieval_metrics(ranks: list[int | None]) -> dict[str, float]:
    """hit@1/3/5 and MRR over the ranks of the correct chunk (None = not found)."""
    if not ranks:
        return {"hit@1": 0.0, "hit@3": 0.0, "hit@5": 0.0, "mrr": 0.0}
    n = len(ranks)

    def hit(k: int) -> float:
        return sum(1 for r in ranks if r is not None and r <= k) / n

    return {
        "hit@1": hit(1),
        "hit@3": hit(3),
        "hit@5": hit(5),
        "mrr": sum(1 / r for r in ranks if r is not None) / n,
    }


def threshold_metrics(
    results: list[tuple[EvalCase, list[ChunkMatch]]],
    threshold: float,
    top_k: int = 5,
) -> dict[str, float]:
    """For one threshold: recall on answerable questions, refusal rate on unanswerable ones."""
    answerable = [(c, m) for c, m in results if c.answerable]
    unanswerable = [(c, m) for c, m in results if not c.answerable]

    kept_correct = sum(
        1
        for case, matches in answerable
        if find_rank(kept_after_filter(matches, threshold, top_k), case.expected_text) is not None
    )
    refused = sum(1 for _, matches in unanswerable if not kept_after_filter(matches, threshold, top_k))

    recall = kept_correct / len(answerable) if answerable else 0.0
    refusal = refused / len(unanswerable) if unanswerable else 0.0
    return {
        "threshold": threshold,
        "recall": recall,
        "refusal_rate": refusal,
        "balanced": (recall + refusal) / 2,  # one number to compare thresholds
    }


def check_answer(case: EvalCase, answer: str, cited_texts: list[str]) -> tuple[bool, str]:
    """Is the AI's answer right? Returns (passed, reason)."""
    refused = normalize(answer) == normalize(NOT_FOUND_ANSWER)

    if not case.answerable:
        return (True, "correctly refused") if refused else (False, "answered but should refuse")

    if refused:
        return False, "refused but the answer is in the documents"
    missing = [word for word in case.answer_contains if normalize(word) not in normalize(answer)]
    if missing:
        return False, f"answer is missing {missing}"
    if not cited_texts:
        return False, "no citation"
    if not any(contains(text, case.expected_text) for text in cited_texts):
        return False, "cited sources don't include the correct chunk"
    return True, "correct and cited"
