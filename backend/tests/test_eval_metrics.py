"""Unit tests for the evaluation metric functions (pure: no AI, no database)."""

from uuid import uuid4

import pytest

from app.models.document import ChunkMatch
from app.services.rag_service import NOT_FOUND_ANSWER
from evals.metrics import (
    EvalCase,
    check_answer,
    find_rank,
    kept_after_filter,
    retrieval_metrics,
    threshold_metrics,
)


def match(content: str, similarity: float, keyword_rank: int | None = None) -> ChunkMatch:
    return ChunkMatch(
        chunk_id=uuid4(), document_id=uuid4(), document_title="Doc", chunk_index=0,
        content=content, similarity=similarity, keyword_rank=keyword_rank,
    )


ANSWERABLE = EvalCase("a", "paraphrase", "How long is probation?", "probation period of six months", ["six months"])
UNANSWERABLE = EvalCase("u", "unanswerable", "Is there a gym?", None, [])


# --- Ranks and retrieval metrics -------------------------------------------------------

def test_find_rank_ignores_case_and_pdf_line_breaks() -> None:
    matches = [match("Something else.", 0.7), match("A Probation\nPeriod of six   months applies.", 0.6)]

    assert find_rank(matches, "probation period of six months") == 2


def test_find_rank_is_none_when_missing() -> None:
    assert find_rank([match("Unrelated.", 0.9)], "six months") is None


def test_retrieval_metrics() -> None:
    metrics = retrieval_metrics([1, 2, None, 4])

    assert metrics["hit@1"] == 0.25
    assert metrics["hit@3"] == 0.5
    assert metrics["hit@5"] == 0.75
    assert metrics["mrr"] == pytest.approx((1 + 0.5 + 0 + 0.25) / 4)


def test_retrieval_metrics_with_no_cases() -> None:
    assert retrieval_metrics([]) == {"hit@1": 0.0, "hit@3": 0.0, "hit@5": 0.0, "mrr": 0.0}


# --- Filtering, like the SQL does ---------------------------------------------------------

def test_filter_keeps_similar_chunks_and_top_keyword_matches() -> None:
    matches = [
        match("similar", 0.70),
        match("exact code but low similarity", 0.50, keyword_rank=1),
        match("weak keyword match", 0.50, keyword_rank=3),
        match("not similar", 0.40),
    ]

    kept = kept_after_filter(matches, threshold=0.55, top_k=5)

    assert [m.content for m in kept] == ["similar", "exact code but low similarity"]


def test_filter_respects_top_k() -> None:
    matches = [match(f"c{i}", 0.9) for i in range(8)]

    assert len(kept_after_filter(matches, threshold=0.5, top_k=5)) == 5


def test_threshold_metrics_recall_and_refusal() -> None:
    results = [
        (ANSWERABLE, [match("The probation period of six months.", 0.62)]),
        (UNANSWERABLE, [match("Parking info.", 0.58)]),
    ]

    low = threshold_metrics(results, threshold=0.55)
    high = threshold_metrics(results, threshold=0.60)

    assert (low["recall"], low["refusal_rate"]) == (1.0, 0.0)  # keeps everything, refuses nothing
    assert (high["recall"], high["refusal_rate"]) == (1.0, 1.0)  # 0.62 passes, 0.58 filtered out
    assert high["balanced"] == 1.0


# --- Answer checks -------------------------------------------------------------------------

def test_correct_cited_answer_passes() -> None:
    ok, reason = check_answer(ANSWERABLE, "Probation lasts six months [1].", ["The probation period of six months."])

    assert ok and reason == "correct and cited"


@pytest.mark.parametrize(
    ("answer", "cited", "reason"),
    [
        (NOT_FOUND_ANSWER, [], "refused but the answer is in the documents"),
        ("Probation lasts three months [1].", ["The probation period of six months."], "missing"),
        ("Probation lasts six months.", [], "no citation"),
        ("Probation lasts six months [1].", ["Parking info."], "cited sources don't include"),
    ],
)
def test_wrong_answers_fail_with_a_reason(answer: str, cited: list[str], reason: str) -> None:
    ok, why = check_answer(ANSWERABLE, answer, cited)

    assert not ok
    assert reason in why


def test_unanswerable_must_be_refused() -> None:
    assert check_answer(UNANSWERABLE, NOT_FOUND_ANSWER, [])[0] is True
    assert check_answer(UNANSWERABLE, "Yes, on floor 2 [1].", ["..."])[0] is False
