"""Chat orchestration: load history → ask the LLM → save the turn.

This is the first piece of Shema AI's "AI Orchestrator". It coordinates two
lower-level parts (LLMService and ConversationRepository) and holds the business
rules from docs/api-contract.md. It knows nothing about HTTP.
"""

from dataclasses import dataclass
from uuid import UUID

from app.models.conversation import StoredMessage
from app.repositories.conversation_repository import (
    ConversationNotFoundError,
    ConversationRepository,
)
from app.services.llm_service import ChatMessage, LLMService

MAX_HISTORY_MESSAGES = 40  # context-window budget: older messages stay in the DB only
TITLE_MAX_LENGTH = 60


@dataclass(frozen=True)
class ChatTurn:
    """The result of one question/answer exchange."""

    conversation_id: UUID
    user_message: StoredMessage
    assistant_message: StoredMessage


def make_title(text: str) -> str:
    """First user message, cut to at most 60 characters."""
    text = text.strip()
    if len(text) <= TITLE_MAX_LENGTH:
        return text
    return text[: TITLE_MAX_LENGTH - 1].rstrip() + "…"


def build_prompt_messages(history: list[StoredMessage], new_text: str) -> list[ChatMessage]:
    """Turn stored history + the new question into the message list for the LLM."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in history]
    # After trimming to the last N messages the list could start with an assistant
    # reply; conversations should start with the user, so drop those.
    while messages and messages[0].role == "assistant":
        messages.pop(0)
    messages.append(ChatMessage(role="user", content=new_text))
    return messages


class ChatService:
    def __init__(self, llm: LLMService, repository: ConversationRepository) -> None:
        self._llm = llm
        self._repo = repository

    def send_message(self, text: str, conversation_id: UUID | None = None) -> ChatTurn:
        text = text.strip()

        # 1. Load earlier messages (only for an existing conversation).
        history: list[StoredMessage] = []
        if conversation_id is not None:
            if self._repo.get_conversation(conversation_id) is None:
                raise ConversationNotFoundError(conversation_id)
            history = self._repo.get_recent_messages(conversation_id, MAX_HISTORY_MESSAGES)

        # 2. Ask the LLM. If this raises, we stop here and NOTHING is saved.
        result = self._llm.chat(build_prompt_messages(history, text))

        # 3. Success: save everything.
        if conversation_id is None:
            conversation_id = self._repo.create_conversation(make_title(text)).id
        user_message = self._repo.add_message(conversation_id, "user", text)
        assistant_message = self._repo.add_message(
            conversation_id,
            "assistant",
            result.content,
            model=result.model,
            usage=result.usage,
        )
        return ChatTurn(conversation_id, user_message, assistant_message)
