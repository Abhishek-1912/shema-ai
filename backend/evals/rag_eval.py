"""Measure RAG quality on a fixed question set, and tune settings with numbers.

Run from the backend folder (venv active):
    python -m evals.rag_eval                          # retrieval: hybrid vs vector + threshold sweep (no AI answers)
    python -m evals.rag_eval --answers                # also generate and check AI answers (uses LLM quota)
    python -m evals.rag_eval --chunk-sizes 300,500,800  # re-load the corpus at each size and compare retrieval
    python -m evals.rag_eval --load-corpus            # (re)load the demo documents first
"""

import argparse
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.models.document import ChunkMatch
from app.repositories.document_repository import get_document_repository
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMRateLimitError, LLMUnavailableError, get_llm_service
from app.services.rag_service import DEFAULT_MIN_SIMILARITY, RagService
from app.services.search_service import get_search_service
from evals.metrics import (
    EvalCase,
    check_answer,
    find_rank,
    load_cases,
    retrieval_metrics,
    threshold_metrics,
)

EVALS = Path(__file__).resolve().parent
SAMPLES = EVALS.parent / "samples"
RESULTS = EVALS / "results"
CASES_FILE = EVALS / "rag_eval_set.json"

# The documents the eval set was written for: (file, title)
CORPUS = [
    ("northwind_handbook.pdf", "[demo] Northwind handbook (PDF)"),
    ("office_faq.docx", "[demo] Office FAQ (Word)"),
    ("forms_and_codes.md", "[demo] Forms and codes"),
]
THRESHOLDS = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
CANDIDATES = 20  # how many results to fetch per question (filtering happens afterwards)


def with_retry[T](action: Callable[[], T], what: str) -> T:
    """Free tier: ~100 embedding requests per minute. Wait and retry instead of crashing."""
    for attempt in range(4):
        try:
            return action()
        except (LLMRateLimitError, LLMUnavailableError) as error:
            wait = 30 * (attempt + 1)
            print(f"    {what}: {type(error).__name__}, waiting {wait}s and retrying…")
            time.sleep(wait)
    return action()  # last try: let the error surface


def load_corpus(max_chars: int, overlap_chars: int) -> None:
    repo = get_document_repository()
    ingestion = IngestionService(get_search_service(), max_chars, overlap_chars)
    for file_name, title in CORPUS:
        data = (SAMPLES / file_name).read_bytes()
        existing = repo.find_document_by_title(title)
        # Ingest the new version FIRST, then delete the old one, so a failure never
        # leaves the document missing (that happened once when the rate limit hit).
        result = with_retry(lambda: ingestion.ingest_file(file_name, data, title=title), title)
        if existing:
            repo.delete_document(existing.id)
        print(f"  loaded {title}: {result.chunk_count} chunks (max {max_chars} chars)")


def retrieve_all(cases: list[EvalCase], hybrid: bool) -> list[tuple[EvalCase, list[ChunkMatch]]]:
    search = get_search_service()
    return [
        (
            case,
            with_retry(
                lambda case=case: search.search(case.question, top_k=CANDIDATES, min_similarity=0.0, hybrid=hybrid),
                case.id,
            ),
        )
        for case in cases
    ]


def print_retrieval(label: str, results: list[tuple[EvalCase, list[ChunkMatch]]]) -> dict:
    answerable = [(c, m) for c, m in results if c.answerable]
    ranks = [find_rank(m, c.expected_text) for c, m in answerable]
    metrics = retrieval_metrics(ranks)
    print(
        f"  {label:7} hit@1 {metrics['hit@1']:.0%}  hit@3 {metrics['hit@3']:.0%}  "
        f"hit@5 {metrics['hit@5']:.0%}  MRR {metrics['mrr']:.3f}"
    )
    misses = [(c.id, r) for (c, _), r in zip(answerable, ranks) if r != 1]
    if misses:
        print(f"          not at rank 1: {', '.join(f'{i} (rank {r})' for i, r in misses)}")
    return metrics


def print_thresholds(results: list[tuple[EvalCase, list[ChunkMatch]]]) -> list[dict]:
    rows = [threshold_metrics(results, t) for t in THRESHOLDS]
    print("  threshold   recall (answer kept)   refusal (nothing kept)   balanced")
    best = max(rows, key=lambda r: (r["balanced"], r["recall"]))
    for row in rows:
        marks = []
        if row["threshold"] == DEFAULT_MIN_SIMILARITY:
            marks.append("current")
        if row is best:
            marks.append("best")
        print(
            f"    {row['threshold']:.2f}        {row['recall']:6.0%}                 "
            f"{row['refusal_rate']:6.0%}                {row['balanced']:.0%}   {' '.join(marks)}"
        )
    return rows


def run_answers(cases: list[EvalCase], delay: float) -> list[dict]:
    rag = RagService(get_search_service(), get_llm_service())
    rows = []
    for case in cases:
        for attempt in range(3):
            try:
                result = rag.answer(case.question)
                break
            except (LLMRateLimitError, LLMUnavailableError) as error:
                wait = 20 * (attempt + 1)
                print(f"    {case.id}: {type(error).__name__}, retrying in {wait}s")
                time.sleep(wait)
        else:
            rows.append({"id": case.id, "passed": False, "reason": "AI unavailable"})
            continue

        cited = [s.chunk.content for s in result.sources if s.cited]
        passed, reason = check_answer(case, result.answer, cited)
        rows.append({"id": case.id, "category": case.category, "passed": passed, "reason": reason, "answer": result.answer})
        print(f"    {'PASS' if passed else 'FAIL'}  {case.id:18} {reason}")
        time.sleep(delay)  # stay under the free-tier requests-per-minute limit

    total = len(rows)
    passed_count = sum(r["passed"] for r in rows)
    print(f"  answers correct: {passed_count}/{total} ({passed_count / total:.0%})")
    for category in ("paraphrase", "code", "unanswerable"):
        subset = [r for r in rows if r.get("category") == category]
        if subset:
            print(f"    {category:13} {sum(r['passed'] for r in subset)}/{len(subset)}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG evaluation")
    parser.add_argument("--answers", action="store_true", help="also generate and check AI answers")
    parser.add_argument("--chunk-sizes", help="comma-separated chunk sizes to compare, e.g. 300,500,800")
    parser.add_argument("--load-corpus", action="store_true", help="(re)load the demo documents first")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between AI answers")
    args = parser.parse_args()

    settings = get_settings()
    cases = load_cases(CASES_FILE)
    report: dict = {"date": datetime.now(UTC).isoformat(), "cases": len(cases), "threshold": DEFAULT_MIN_SIMILARITY}
    print(f"{len(cases)} questions ({sum(c.answerable for c in cases)} answerable, "
          f"{sum(not c.answerable for c in cases)} must be refused)\n")

    if args.chunk_sizes:
        report["chunk_sizes"] = {}
        for size in [int(s) for s in args.chunk_sizes.split(",")]:
            print(f"== Chunk size {size}")
            load_corpus(size, size // 5)
            results = retrieve_all(cases, hybrid=True)
            report["chunk_sizes"][size] = {
                "retrieval": print_retrieval("hybrid", results),
                "thresholds": print_thresholds(results),
            }
            print()
        print(f"== Restoring the default chunk size ({settings.chunk_max_chars})")
        load_corpus(settings.chunk_max_chars, settings.chunk_overlap_chars)
    else:
        if args.load_corpus:
            print("== Loading corpus")
            load_corpus(settings.chunk_max_chars, settings.chunk_overlap_chars)
            print()
        print("== Retrieval (is the correct chunk found, and how high?)")
        hybrid = retrieve_all(cases, hybrid=True)
        vector = retrieve_all(cases, hybrid=False)
        report["retrieval"] = {"hybrid": print_retrieval("hybrid", hybrid), "vector": print_retrieval("vector", vector)}
        print("\n== Threshold sweep (hybrid): what survives the filter that RAG applies")
        report["thresholds_hybrid"] = print_thresholds(hybrid)
        print("\n== Threshold sweep (vector only)")
        report["thresholds_vector"] = print_thresholds(vector)

    if args.answers:
        print(f"\n== Answers (threshold {DEFAULT_MIN_SIMILARITY}, {args.delay}s between questions)")
        report["answers"] = run_answers(cases, args.delay)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"rag_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport saved to {out.relative_to(EVALS.parent)}")


if __name__ == "__main__":
    main()
