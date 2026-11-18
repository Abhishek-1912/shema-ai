"""Unit tests for DocumentRepository. The Supabase client is a mock."""

from unittest.mock import MagicMock
from uuid import uuid4

from postgrest.types import ReturnMethod

from app.models.document import NewChunk
from app.repositories.document_repository import DocumentRepository

DOCUMENT_ID = uuid4()
NOW = "2026-11-18T10:00:00+00:00"


def fake_client_returning(*results: list[dict]) -> MagicMock:
    """Every chain method returns the same query mock; each execute() returns the next result."""
    query = MagicMock()
    for method in ("select", "insert", "delete", "eq", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [MagicMock(data=result) for result in results]

    client = MagicMock()
    client.table.return_value = query
    client.rpc.return_value = query
    client.query = query
    return client


def test_create_document() -> None:
    client = fake_client_returning(
        [{"id": str(DOCUMENT_ID), "title": "Policy", "source_type": "pdf", "file_name": "p.pdf", "created_at": NOW}]
    )

    document = DocumentRepository(client).create_document("Policy", "pdf", "p.pdf")

    assert document.id == DOCUMENT_ID
    client.query.insert.assert_called_once_with(
        {"title": "Policy", "source_type": "pdf", "file_name": "p.pdf"}
    )


def test_list_documents_reads_chunk_counts() -> None:
    client = fake_client_returning(
        [
            {"id": str(DOCUMENT_ID), "title": "Policy", "source_type": "pdf", "file_name": "p.pdf",
             "created_at": NOW, "document_chunks": [{"count": 12}]},
        ]
    )

    [document] = DocumentRepository(client).list_documents()

    assert document.title == "Policy"
    assert document.chunk_count == 12
    client.query.select.assert_called_once_with("*, document_chunks(count)")


def test_get_document_returns_none_when_missing() -> None:
    client = fake_client_returning([])

    assert DocumentRepository(client).get_document(DOCUMENT_ID) is None


def test_add_chunks_inserts_all_rows_in_one_request_without_returning_vectors() -> None:
    client = fake_client_returning([])
    chunks = [
        NewChunk(chunk_index=0, content="First", embedding=[0.1, 0.2]),
        NewChunk(chunk_index=1, content="Second", embedding=[0.3, 0.4], page_number=2),
    ]

    saved = DocumentRepository(client).add_chunks(DOCUMENT_ID, chunks)

    assert saved == 2
    client.table.assert_called_with("document_chunks")
    rows = client.query.insert.call_args.args[0]
    assert [row["chunk_index"] for row in rows] == [0, 1]
    assert rows[1] == {
        "document_id": str(DOCUMENT_ID),
        "chunk_index": 1,
        "content": "Second",
        "page_number": 2,
        "embedding": [0.3, 0.4],
    }
    assert client.query.insert.call_args.kwargs["returning"] == ReturnMethod.minimal


def test_add_no_chunks_makes_no_request() -> None:
    client = fake_client_returning()

    assert DocumentRepository(client).add_chunks(DOCUMENT_ID, []) == 0
    client.table.assert_not_called()


def test_hybrid_search_calls_the_hybrid_function_with_text_and_vector() -> None:
    row = {
        "chunk_id": str(uuid4()),
        "document_id": str(DOCUMENT_ID),
        "document_title": "Forms",
        "chunk_index": 0,
        "page_number": None,
        "content": "Project KESTREL is the data warehouse migration.",
        "similarity": 0.52,
        "keyword_rank": 1,
        "score": 0.0328,
    }
    client = fake_client_returning([row])

    [match] = DocumentRepository(client).hybrid_search("KESTREL", [0.1, 0.2], limit=5, min_similarity=0.55)

    client.rpc.assert_called_once_with(
        "hybrid_match_document_chunks",
        {
            "query_text": "KESTREL",
            "query_embedding": [0.1, 0.2],
            "match_count": 5,
            "min_similarity": 0.55,
            "keyword_top": 2,
        },
    )
    assert match.keyword_rank == 1  # kept although similarity 0.52 < 0.55: exact keyword match
    assert match.score == 0.0328


def test_search_calls_the_database_function() -> None:
    row = {
        "chunk_id": str(uuid4()),
        "document_id": str(DOCUMENT_ID),
        "document_title": "Policy",
        "chunk_index": 0,
        "page_number": None,
        "content": "Refunds within 30 days.",
        "similarity": 0.81,
    }
    client = fake_client_returning([row])

    matches = DocumentRepository(client).search([0.1, 0.2], limit=3, min_similarity=0.5)

    client.rpc.assert_called_once_with(
        "match_document_chunks",
        {"query_embedding": [0.1, 0.2], "match_count": 3, "min_similarity": 0.5},
    )
    assert matches[0].document_title == "Policy"
    assert matches[0].similarity == 0.81
