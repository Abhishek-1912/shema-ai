"""Tests for Shema's MCP server, using a real MCP client connected IN-PROCESS.

The client speaks the real protocol (list tools, call tool...), but no subprocess is
started and the search/repository are fakes, so no AI or database is touched.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import anyio
import pytest
from mcp import Client

from app.mcp_server.server import build_server
from app.models.conversation import Conversation
from app.models.document import ChunkMatch, Document, DocumentWithCount
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.services.search_service import AddedDocument, SemanticSearchService

NOW = datetime(2026, 11, 18, tzinfo=UTC)


@pytest.fixture
def search() -> MagicMock:
    fake = MagicMock(spec=SemanticSearchService)
    fake.search.return_value = [
        ChunkMatch(
            chunk_id=uuid4(), document_id=uuid4(), document_title="Forms and codes",
            chunk_index=1, page_number=None,
            content="Project KESTREL is the data warehouse migration.", similarity=0.5234,
        )
    ]
    return fake


@pytest.fixture
def repo() -> MagicMock:
    fake = MagicMock(spec=DocumentRepository)
    fake.list_documents.return_value = [
        DocumentWithCount(
            id=uuid4(), title="Handbook", source_type="pdf", file_name="h.pdf",
            created_at=datetime(2026, 11, 18, tzinfo=UTC), chunk_count=12,
        )
    ]
    return fake


@pytest.fixture
def conversations() -> MagicMock:
    fake = MagicMock(spec=ConversationRepository)
    fake.list_conversations.return_value = [
        Conversation(id=uuid4(), title="What is an LLM?", created_at=NOW, updated_at=NOW)
    ]
    return fake


@pytest.fixture
def server(search: MagicMock, repo: MagicMock, conversations: MagicMock) -> Iterator:
    yield build_server(lambda: search, lambda: repo, lambda: conversations)


def run(coro_fn):  # small helper: run an async test body
    return anyio.run(coro_fn)


def test_server_advertises_its_tools_resources_and_prompts(server) -> None:
    async def body():
        async with Client(server) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            resources = [str(r.uri) for r in (await client.list_resources()).resources]
            prompts = [p.name for p in (await client.list_prompts()).prompts]
            return tools, resources, prompts

    tools, resources, prompts = run(body)

    assert set(tools) == {
        "search_documents", "list_documents", "list_recent_conversations", "save_note", "delete_document",
    }
    # Permissions are declared by the server through annotations:
    assert tools["list_recent_conversations"].annotations.read_only_hint is True
    assert tools["save_note"].annotations.read_only_hint is False
    assert tools["delete_document"].annotations.destructive_hint is True
    schema = tools["search_documents"].input_schema
    assert schema["required"] == ["query"]  # top_k has a default, so it's optional
    assert schema["properties"]["top_k"]["type"] == "integer"
    assert tools["search_documents"].annotations.read_only_hint is True
    assert "meaning and keywords" in tools["search_documents"].description
    assert resources == ["shema://documents"]
    assert prompts == ["grounded_question"]


def test_search_tool_returns_structured_results(server, search: MagicMock) -> None:
    async def body():
        async with Client(server) as client:
            return await client.call_tool("search_documents", {"query": "KESTREL", "top_k": 3})

    result = run(body)

    assert result.is_error is False
    [hit] = result.structured_content["result"]
    assert hit == {
        "document_title": "Forms and codes",
        "page_number": None,
        "content": "Project KESTREL is the data warehouse migration.",
        "similarity": 0.523,
    }
    search.search.assert_called_once_with("KESTREL", top_k=3)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [({"query": "   "}, "must not be empty"), ({"query": "x", "top_k": 99}, "between 1 and 10")],
)
def test_bad_tool_input_returns_a_clear_tool_error(server, search: MagicMock, arguments: dict, message: str) -> None:
    async def body():
        async with Client(server) as client:
            return await client.call_tool("search_documents", arguments)

    result = run(body)

    assert result.is_error is True
    assert message in result.content[0].text
    search.search.assert_not_called()


def test_list_documents_tool(server) -> None:
    async def body():
        async with Client(server) as client:
            return await client.call_tool("list_documents", {})

    [doc] = run(body).structured_content["result"]

    assert (doc["title"], doc["source_type"], doc["chunk_count"]) == ("Handbook", "pdf", 12)


def call(server, name: str, arguments: dict):
    async def body():
        async with Client(server) as client:
            return await client.call_tool(name, arguments)

    return run(body)


def test_list_recent_conversations_tool(server, conversations: MagicMock) -> None:
    [conversation] = call(server, "list_recent_conversations", {"limit": 5}).structured_content["result"]

    assert conversation["title"] == "What is an LLM?"
    conversations.list_conversations.assert_called_once_with(limit=5)


def test_save_note_chunks_and_stores_the_text(server, search: MagicMock) -> None:
    search.add_document.return_value = AddedDocument(
        document=Document(id=uuid4(), title="Meeting notes", source_type="text", created_at=NOW), chunk_count=1
    )

    result = call(server, "save_note", {"title": " Meeting notes ", "content": "We decided to use pgvector."})

    assert result.structured_content == {"ok": True, "message": "Saved note 'Meeting notes' (1 chunks)."}
    search.add_document.assert_called_once_with("Meeting notes", ["We decided to use pgvector."], source_type="text")


def test_save_note_rejects_empty_content(server, search: MagicMock) -> None:
    result = call(server, "save_note", {"title": "Empty", "content": "   "})

    assert result.is_error and "must not be empty" in result.content[0].text
    search.add_document.assert_not_called()


def test_delete_document_deletes_an_existing_document(server, repo: MagicMock) -> None:
    document = Document(id=uuid4(), title="Old policy", source_type="pdf", created_at=NOW)
    repo.get_document.return_value = document

    result = call(server, "delete_document", {"document_id": str(document.id)})

    assert result.structured_content == {"ok": True, "message": "Deleted document 'Old policy'."}
    repo.delete_document.assert_called_once_with(document.id)


@pytest.mark.parametrize(
    ("document_id", "found", "message"),
    [("not-a-uuid", True, "not a valid id"), (str(uuid4()), False, "No document with that id")],
)
def test_delete_document_refuses_bad_or_unknown_ids(
    server, repo: MagicMock, document_id: str, found: bool, message: str
) -> None:
    repo.get_document.return_value = None if not found else MagicMock()

    result = call(server, "delete_document", {"document_id": document_id})

    assert result.is_error and message in result.content[0].text
    repo.delete_document.assert_not_called()


def test_catalog_resource_is_markdown(server) -> None:
    async def body():
        async with Client(server) as client:
            return await client.read_resource("shema://documents")

    text = run(body).contents[0].text

    assert text.startswith("# Documents")
    assert "**Handbook** (pdf, 12 chunks)" in text


def test_grounded_question_prompt_embeds_the_question(server) -> None:
    async def body():
        async with Client(server) as client:
            return await client.get_prompt("grounded_question", {"question": "What is KESTREL?"})

    prompt = run(body)

    text = prompt.messages[0].content.text
    assert "ONLY passages returned by the search_documents tool" in text
    assert text.endswith("Question: What is KESTREL?")
