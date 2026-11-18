"""Tests for the tool-calling agent loop.

The AI is a scripted fake (it "decides" to call tools in a fixed order); the MCP server
is the real one, connected in-process, with fake search data.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import anyio
import pytest
from openai.types.chat import ChatCompletion

from app.mcp_server.server import build_server
from app.models.document import ChunkMatch, Document, DocumentWithCount
from app.repositories.document_repository import DocumentRepository
from app.services.search_service import SemanticSearchService
from app.services.tool_agent import REJECTED_RESULT, ToolAgent, needs_approval, to_openai_tool


def completion(content: str | None = None, tool_calls: list[dict] | None = None) -> ChatCompletion:
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return ChatCompletion.model_validate(
        {
            "id": "x", "object": "chat.completion", "created": 0, "model": "fake-model",
            "choices": [{"index": 0, "finish_reason": "tool_calls" if tool_calls else "stop", "message": message}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )


def tool_call(call_id: str, name: str, arguments: dict | str, signature: str | None = None) -> dict:
    call = {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments)},
    }
    if signature:
        call["extra_content"] = {"google": {"thought_signature": signature}}
    return call


@pytest.fixture
def search() -> MagicMock:
    fake = MagicMock(spec=SemanticSearchService)
    fake.search.return_value = [
        ChunkMatch(
            chunk_id=uuid4(), document_id=uuid4(), document_title="Handbook", chunk_index=6,
            page_number=3, content="Parents receive 4 weeks of paid paternity leave.", similarity=0.71,
        )
    ]
    return fake


DOC_ID = uuid4()


@pytest.fixture
def repo() -> MagicMock:
    fake = MagicMock(spec=DocumentRepository)
    fake.list_documents.return_value = [
        DocumentWithCount(id=DOC_ID, title="Handbook", source_type="pdf", file_name="h.pdf",
                          created_at=datetime(2026, 11, 18, tzinfo=UTC), chunk_count=12)
    ]
    fake.get_document.return_value = Document(
        id=DOC_ID, title="Handbook", source_type="pdf", created_at=datetime(2026, 11, 18, tzinfo=UTC)
    )
    return fake


@pytest.fixture
def server(search: MagicMock, repo: MagicMock):
    return build_server(lambda: search, lambda: repo, lambda: MagicMock())


def make_agent(server, responses: list[ChatCompletion], max_steps: int = 5) -> tuple[ToolAgent, AsyncMock]:
    llm = MagicMock()
    llm.chat.completions.create = AsyncMock(side_effect=responses)
    return ToolAgent(llm, "fake-model", mcp_source=server, max_steps=max_steps), llm.chat.completions.create


def run(agent: ToolAgent, question: str):
    return anyio.run(agent.run, question)


# --- The happy path -------------------------------------------------------------------

def test_agent_calls_a_tool_then_answers(server, search: MagicMock) -> None:
    agent, create = make_agent(
        server,
        [
            completion(tool_calls=[tool_call("c1", "search_documents", {"query": "paternity leave"}, signature="SIG")]),
            completion("Fathers get 4 weeks of paid paternity leave (Handbook, page 3)."),
        ],
    )

    result = run(agent, "How much paternity leave do fathers get?")

    assert result.answer.startswith("Fathers get 4 weeks")
    assert result.steps == 2 and result.stopped_early is False
    [record] = result.tool_calls
    assert (record.name, record.arguments, record.is_error) == ("search_documents", {"query": "paternity leave"}, False)
    assert "4 weeks of paid paternity leave" in record.result
    search.search.assert_called_once_with("paternity leave", top_k=5)
    assert result.usage.total_tokens == 30  # summed over both AI calls

    # What the AI saw in the second call: its own tool request (with the Gemini
    # thought signature kept), then the tool result linked by the same id.
    second_messages = create.call_args_list[1].kwargs["messages"]
    assistant, tool_msg = second_messages[-2], second_messages[-1]
    assert assistant["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "SIG"}}
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert "Handbook" in tool_msg["content"]


def test_tools_are_described_to_the_ai_in_openai_format(server) -> None:
    agent, create = make_agent(server, [completion("Hello!")])

    run(agent, "Hi")

    tools = create.call_args.kwargs["tools"]
    names = {t["function"]["name"] for t in tools}
    assert names == {"search_documents", "list_documents", "list_recent_conversations", "save_note", "delete_document"}
    search_tool = next(t for t in tools if t["function"]["name"] == "search_documents")
    assert search_tool["type"] == "function"
    assert search_tool["function"]["parameters"]["required"] == ["query"]


def test_general_question_is_answered_without_tools(server, search: MagicMock) -> None:
    agent, _ = make_agent(server, [completion("2 + 2 = 4.")])

    result = run(agent, "What is 2 + 2?")

    assert result.answer == "2 + 2 = 4." and result.tool_calls == [] and result.steps == 1
    search.search.assert_not_called()


def test_several_tools_in_one_step_are_all_run(server) -> None:
    agent, _ = make_agent(
        server,
        [
            completion(tool_calls=[
                tool_call("c1", "list_documents", {}),
                tool_call("c2", "search_documents", {"query": "leave", "top_k": 2}),
            ]),
            completion("Done."),
        ],
    )

    result = run(agent, "Overview and leave rules?")

    assert [r.name for r in result.tool_calls] == ["list_documents", "search_documents"]


# --- Robustness -------------------------------------------------------------------------

def test_unknown_tool_is_not_run_and_the_ai_is_told(server) -> None:
    agent, create = make_agent(
        server,
        [completion(tool_calls=[tool_call("c1", "delete_everything", {})]), completion("Sorry.")],
    )

    result = run(agent, "Do something")

    [record] = result.tool_calls
    assert record.is_error and "unknown tool" in record.result
    assert create.call_args_list[1].kwargs["messages"][-1]["content"].startswith("Error: unknown tool")


def test_invalid_json_arguments_become_an_error_result(server, search: MagicMock) -> None:
    agent, _ = make_agent(
        server,
        [completion(tool_calls=[tool_call("c1", "search_documents", "{not json")]), completion("Sorry.")],
    )

    [record] = run(agent, "Search").tool_calls

    assert record.is_error and "invalid tool arguments" in record.result
    search.search.assert_not_called()


def test_tool_errors_are_passed_back_so_the_ai_can_recover(server) -> None:
    agent, _ = make_agent(
        server,
        [
            completion(tool_calls=[tool_call("c1", "search_documents", {"query": "x", "top_k": 99})]),
            completion(tool_calls=[tool_call("c2", "search_documents", {"query": "x", "top_k": 5})]),
            completion("Found it."),
        ],
    )

    result = run(agent, "Search")

    assert [r.is_error for r in result.tool_calls] == [True, False]
    assert "between 1 and 10" in result.tool_calls[0].result


def test_max_steps_forces_a_final_answer_without_tools(server) -> None:
    looping = completion(tool_calls=[tool_call("c", "list_documents", {})])
    agent, create = make_agent(server, [looping, looping, completion("Best answer I have.")], max_steps=2)

    result = run(agent, "Loop forever")

    assert result.stopped_early is True
    assert result.answer == "Best answer I have."
    assert len(result.tool_calls) == 2
    assert "tools" not in create.call_args_list[-1].kwargs  # no tools offered in the last call


def test_empty_question_is_rejected(server) -> None:
    agent, create = make_agent(server, [])

    with pytest.raises(ValueError):
        run(agent, "   ")
    create.assert_not_called()


# --- Human approval -------------------------------------------------------------------------

DELETE_CALL = tool_call("d1", "delete_document", {"document_id": str(DOC_ID)})


def resume(agent: ToolAgent, paused, approvals: dict[str, bool]):
    return anyio.run(agent.resume, paused, approvals)


def test_destructive_tool_pauses_and_runs_nothing(server, repo: MagicMock) -> None:
    agent, create = make_agent(server, [completion(tool_calls=[DELETE_CALL])])

    paused = run(agent, "Delete the handbook")

    assert paused.status == "needs_approval"
    [pending] = paused.pending
    assert (pending.call_id, pending.name, pending.destructive) == ("d1", "delete_document", True)
    assert pending.arguments == {"document_id": str(DOC_ID)}
    repo.delete_document.assert_not_called()  # NOTHING happens before a human decides
    assert create.call_count == 1  # and the AI is not asked again yet


def test_approved_action_runs_and_the_ai_finishes(server, repo: MagicMock) -> None:
    agent, create = make_agent(server, [completion(tool_calls=[DELETE_CALL]), completion("The handbook was deleted.")])
    paused = run(agent, "Delete the handbook")

    result = resume(agent, paused, {"d1": True})

    assert result.status == "done"
    assert result.answer == "The handbook was deleted."
    repo.delete_document.assert_called_once_with(DOC_ID)
    [record] = result.tool_calls
    assert record.approval == "approved" and "Deleted document 'Handbook'" in record.result
    assert result.steps == 2


def test_rejected_action_never_runs_and_the_ai_is_told(server, repo: MagicMock) -> None:
    agent, create = make_agent(server, [completion(tool_calls=[DELETE_CALL]), completion("OK, I did not delete it.")])
    paused = run(agent, "Delete the handbook")

    result = resume(agent, paused, {"d1": False})

    repo.delete_document.assert_not_called()
    assert result.tool_calls[0].approval == "rejected"
    tool_message = create.call_args_list[1].kwargs["messages"][-1]
    assert tool_message == {"role": "tool", "tool_call_id": "d1", "content": REJECTED_RESULT}


def test_missing_decision_counts_as_rejected(server, repo: MagicMock) -> None:
    agent, _ = make_agent(server, [completion(tool_calls=[DELETE_CALL]), completion("Not deleted.")])
    paused = run(agent, "Delete the handbook")

    result = resume(agent, paused, {})  # no decision for d1

    repo.delete_document.assert_not_called()
    assert result.tool_calls[0].approval == "rejected"


def test_read_only_calls_in_the_same_step_run_immediately(server, repo: MagicMock) -> None:
    agent, create = make_agent(
        server,
        [
            completion(tool_calls=[tool_call("l1", "list_documents", {}), DELETE_CALL]),
            completion("Done."),
        ],
    )

    paused = run(agent, "List then delete")

    assert [r.name for r in paused.tool_calls] == ["list_documents"]  # ran automatically
    assert [p.name for p in paused.pending] == ["delete_document"]  # waits

    resume(agent, paused, {"d1": True})

    # Both tool results go back to the AI, in the order it asked for them.
    messages = create.call_args_list[1].kwargs["messages"]
    assert [m["tool_call_id"] for m in messages if m["role"] == "tool"] == ["l1", "d1"]


def test_resume_without_a_pause_is_an_error(server) -> None:
    agent, _ = make_agent(server, [completion("Hi")])
    finished = run(agent, "Hi")

    with pytest.raises(ValueError):
        resume(agent, finished, {})


def test_policy_asks_when_a_tool_has_no_annotations() -> None:
    no_annotations = MagicMock(annotations=None)
    read_only = MagicMock()
    read_only.annotations.read_only_hint = True
    writes = MagicMock()
    writes.annotations.read_only_hint = False

    assert needs_approval(no_annotations) is True  # unknown → ask (safe default)
    assert needs_approval(read_only) is False
    assert needs_approval(writes) is True


def test_to_openai_tool() -> None:
    tool = MagicMock()
    tool.name, tool.description, tool.input_schema = "t", "Does t.", {"type": "object", "properties": {}}

    assert to_openai_tool(tool) == {
        "type": "function",
        "function": {"name": "t", "description": "Does t.", "parameters": {"type": "object", "properties": {}}},
    }
