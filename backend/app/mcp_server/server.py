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

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from app.repositories.document_repository import DocumentRepository, get_document_repository
from app.services.search_service import SemanticSearchService, get_search_service

MAX_RESULTS = 10
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


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


def build_server(
    search_factory: Callable[[], SemanticSearchService] = get_search_service,
    repository_factory: Callable[[], DocumentRepository] = get_document_repository,
) -> MCPServer:
    """Create the server. The factories are injected so tests can pass fakes."""
    server = MCPServer(
        name="shema-knowledge",
        title="Shema AI knowledge base",
        instructions=(
            "Search and list the documents stored in Shema AI. "
            "Use search_documents to find passages that answer a question; "
            "cite the document title (and page) of what you use."
        ),
        version="0.1.0",
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
