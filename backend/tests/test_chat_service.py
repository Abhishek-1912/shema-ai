"""Unit tests for ChatService: the business rules of a chat turn.

Both collaborators (LLMService and ConversationRepository) are mocks.
"""

from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from app.repositories.conversation_repository import (
    ConversationNotFoundError,
    ConversationRepository,
)
from app.services.chat_service import (
    MAX_HISTORY_MESSAGES,
    ChatService,
    build_prompt_messages,
    make_title,
)
from app.services.llm_service import (
    ChatMessage,
    LLMResult,
    LLMService,
    LLMUnavailableError,
    TokenUsage,
)
from tests.factories import make_conversation, make_message

USAGE = TokenUsage(input_tokens=10, output_tokens=6, thinking_tokens=4, total_tokens=20)


@pytest.fixture
def llm() -> MagicMock:
    fake = MagicMock(spec=LLMService)
    fake.chat.return_value = LLMResult(content="An answer.", model="fake-model", usage=USAGE)
    return fake


@pytest.fixture
def repo() -> MagicMock:
    fake = MagicMock(spec=ConversationRepository)
    fake.add_message.side_effect = lambda conversation_id, role, content, **_: make_message(
        conversation_id, role, content
    )
    return fake


# --- New conversation -----------------------------------------------------------

def test_new_conversation_is_created_with_title_and_both_messages_saved(
    llm: MagicMock, repo: MagicMock
) -> None:
    new = make_conversation(title="What is an LLM?")
    repo.create_conversation.return_value = new

    turn = ChatService(llm, repo).send_message("  What is an LLM?  ")

    llm.chat.assert_called_once_with([ChatMessage(role="user", content="What is an LLM?")])
    repo.create_conversation.assert_called_once_with("What is an LLM?")
    assert repo.add_message.call_args_list == [
        call(new.id, "user", "What is an LLM?"),
        call(new.id, "assistant", "An answer.", model="fake-model", usage=USAGE),
    ]
    assert turn.conversation_id == new.id
    assert turn.assistant_message.content == "An answer."


# --- Existing conversation ------------------------------------------------------

def test_existing_conversation_sends_history_then_new_message(llm: MagicMock, repo: MagicMock) -> None:
    conversation = make_conversation()
    repo.get_conversation.return_value = conversation
    repo.get_recent_messages.return_value = [
        make_message(conversation.id, "user", "What is an LLM?"),
        make_message(conversation.id, "assistant", "A language model."),
    ]

    ChatService(llm, repo).send_message("Give me an example.", conversation.id)

    repo.get_recent_messages.assert_called_once_with(conversation.id, MAX_HISTORY_MESSAGES)
    llm.chat.assert_called_once_with(
        [
            ChatMessage(role="user", content="What is an LLM?"),
            ChatMessage(role="assistant", content="A language model."),
            ChatMessage(role="user", content="Give me an example."),
        ]
    )
    repo.create_conversation.assert_not_called()


def test_unknown_conversation_raises_not_found_and_skips_llm(llm: MagicMock, repo: MagicMock) -> None:
    repo.get_conversation.return_value = None

    with pytest.raises(ConversationNotFoundError):
        ChatService(llm, repo).send_message("Hi", uuid4())

    llm.chat.assert_not_called()


# --- Failure rule: nothing is saved ---------------------------------------------

def test_llm_failure_saves_nothing(llm: MagicMock, repo: MagicMock) -> None:
    llm.chat.side_effect = LLMUnavailableError("overloaded")

    with pytest.raises(LLMUnavailableError):
        ChatService(llm, repo).send_message("Hi")

    repo.create_conversation.assert_not_called()
    repo.add_message.assert_not_called()


# --- Helpers ----------------------------------------------------------------------

def test_short_title_is_kept() -> None:
    assert make_title("  What is an LLM?  ") == "What is an LLM?"


def test_long_title_is_cut_to_60_characters() -> None:
    title = make_title("a" * 100)

    assert len(title) == 60
    assert title.endswith("…")


def test_prompt_drops_leading_assistant_messages() -> None:
    conversation_id = uuid4()
    history = [
        make_message(conversation_id, "assistant", "orphan reply (start of trimmed history)"),
        make_message(conversation_id, "user", "Question"),
        make_message(conversation_id, "assistant", "Answer"),
    ]

    messages = build_prompt_messages(history, "Next question")

    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert messages[-1].content == "Next question"
