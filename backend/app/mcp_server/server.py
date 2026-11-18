"""Shema AI's MCP server: exposes the knowledge base as tools any MCP client can use.

MCP (Model Context Protocol) = a standard plug between AI apps and tools/data:
- an MCP SERVER (this file) offers tools, resources and prompts,
- an MCP CLIENT connects to it, asks "what do you offer?" and calls things,
- the HOST is the app that owns the client and the AI (our backend, Cursor, Claude Desktop...).

Run it over stdio (the client starts it as a subprocess):
    python -m app.mcp_server.server

IMPORTANT for stdio servers: never print() to stdout — stdout IS the protocol channel.
Logs go to stderr (the SDK does this for us).
"""

from collections.abc import Callable
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from app.repositories.conversation_repository import (
    ConversationRepository,
    get_conversation_repository,
)
from app.repositories.document_repository import DocumentRepository, get_document_repository
from app.services.chunking import chunk_text
from app.services.search_service import SemanticSearchService, get_search_service

MAX_RESULTS = 10
MAX_NOTE_CHARS = 20_000

# Annotations tell the HOST what a tool does. Our agent uses them for permissions:
# read-only tools run automatically, everything else waits for a human's approval.
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)


# --- What the tools return (becomes JSON + a schema the AI can read) -------------------

class SearchResult(BaseModel):
    document_title: str
    page_number: int | None
    content: str
    similarity: float


class DocumentInfo(BaseModel):
    id: str
    title: str
    source_type: str
    chunk_count: int


class ConversationInfo(BaseModel):
    id: str
    title: str
    updated_at: str


class ActionResult(BaseModel):
    ok: bool
    message: str


def build_server(
    search_factory: Callable[[], SemanticSearchService] = get_search_service,
    repository_factory: Callable[[], DocumentRepository] = get_document_repository,
    conversation_factory: Callable[[], ConversationRepository] = get_conversation_repository,
) -> MCPServer:
    """Create the server. The factories are injected so tests can pass fakes."""
    server = MCPServer(
        name="shema-knowledge",
        title="Shema AI knowledge base",
        instructions=(
            "Search, list and manage the documents stored in Shema AI. "
            "Use search_documents to find passages that answer a question; "
            "cite the document title (and page) of what you use. "
            "save_note and delete_document change data and need the user's approval."
        ),
        version="0.2.0",
    )

    # --- Tools: actions the AI can decide to call ---------------------------------------

    @server.tool(annotations=READ_ONLY)
    def search_documents(query: str, top_k: int = 5) -> list[SearchResult]:
        """Search the user's documents by meaning and keywords.

        Returns the most relevant passages, best first, with their document title,
        page number (PDFs only) and similarity score (0-1).
        """
        if not query.strip():
            raise ToolError("query must not be empty.")
        if not 1 <= top_k <= MAX_RESULTS:
            raise ToolError(f"top_k must be between 1 and {MAX_RESULTS}.")

        matches = search_factory().search(query, top_k=top_k)
        return [
            SearchResult(
                document_title=m.document_title,
                page_number=m.page_number,
                content=m.content,
                similarity=round(m.similarity, 3),
            )
            for m in matches
        ]

    @server.tool(annotations=READ_ONLY)
    def list_documents() -> list[DocumentInfo]:
        """List every document in the knowledge base (title, type, number of chunks)."""
        return [
            DocumentInfo(
                id=str(d.id), title=d.title, source_type=d.source_type, chunk_count=d.chunk_count
            )
            for d in repository_factory().list_documents()
        ]

    @server.tool(annotations=READ_ONLY)
    def list_recent_conversations(limit: int = 10) -> list[ConversationInfo]:
        """List the user's most recent chat conversations (title and last activity)."""
        if not 1 <= limit <= 50:
            raise ToolError("limit must be between 1 and 50.")
        return [
            ConversationInfo(id=str(c.id), title=c.title, updated_at=c.updated_at.isoformat())
            for c in conversation_factory().list_conversations(limit=limit)
        ]

    # --- Tools that CHANGE data: the host must ask a human before running them ----------

    @server.tool(annotations=WRITES)
    def save_note(title: str, content: str) -> ActionResult:
        """Save a new note in the knowledge base so it becomes searchable.

        Changes data: the user must approve this before it runs.
        """
        title, content = title.strip(), content.strip()
        if not title or not content:
            raise ToolError("title and content must not be empty.")
        if len(content) > MAX_NOTE_CHARS:
            raise ToolError(f"content is longer than {MAX_NOTE_CHARS} characters.")
        added = search_factory().add_document(title, chunk_text(content), source_type="text")
        return ActionResult(ok=True, message=f"Saved note '{title}' ({added.chunk_count} chunks).")

    @server.tool(annotations=DESTRUCTIVE)
    def delete_document(document_id: str) -> ActionResult:
        """Permanently delete a document (and all its chunks) by its id.

        Destructive and cannot be undone: the user must approve this before it runs.
        Use list_documents first to find the id.
        """
        try:
            uuid = UUID(document_id)
        except ValueError:
            raise ToolError("document_id is not a valid id. Use list_documents to find it.") from None
        repository = repository_factory()
        document = repository.get_document(uuid)
        if document is None:
            raise ToolError("No document with that id exists.")
        repository.delete_document(uuid)
        return ActionResult(ok=True, message=f"Deleted document '{document.title}'.")

    # --- Resources: data the client can READ (the app decides, not the AI) ---------------

    @server.resource(
        "shema://documents",
        name="document-catalog",
        description="A Markdown list of all documents in the knowledge base.",
        mime_type="text/markdown",
    )
    def document_catalog() -> str:
        documents = repository_factory().list_documents()
        if not documents:
            return "# Documents\n\n(no documents yet)"
        lines = [f"- **{d.title}** ({d.source_type}, {d.chunk_count} chunks)" for d in documents]
        return "# Documents\n\n" + "\n".join(lines)

    # --- Prompts: reusable prompt templates the USER picks -------------------------------

    @server.prompt(description="Ask a question that must be answered only from the documents.")
    def grounded_question(question: str) -> str:
        return (
            "Answer the question below using ONLY passages returned by the search_documents "
            "tool. Cite the document title (and page) for every fact. If the documents don't "
            f"contain the answer, say so.\n\nQuestion: {question}"
        )

    return server


server = build_server()

if __name__ == "__main__":
    server.run()  # stdio transport by default
