"""HTTP layer for chat. No business logic: validate → call ChatService → shape the response.

Errors are NOT caught here; app/core/errors.py turns them into HTTP status codes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.repositories.conversation_repository import (
    ConversationRepository,
    get_conversation_repository,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import MessageOut
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService, get_llm_service

router = APIRouter(prefix="/api", tags=["chat"])


def get_chat_service(
    llm: Annotated[LLMService, Depends(get_llm_service)],
    repository: Annotated[ConversationRepository, Depends(get_conversation_repository)],
) -> ChatService:
    """FastAPI builds ChatService from its two dependencies (like Spring constructor injection)."""
    return ChatService(llm, repository)


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    turn = chat_service.send_message(request.message, request.conversation_id)
    return ChatResponse(
        conversation_id=turn.conversation_id,
        user_message=MessageOut.from_stored(turn.user_message),
        assistant_message=MessageOut.from_stored(turn.assistant_message),
    )
