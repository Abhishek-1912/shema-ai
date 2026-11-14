"""HTTP layer for listing, loading and deleting conversations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.repositories.conversation_repository import (
    ConversationNotFoundError,
    ConversationRepository,
    get_conversation_repository,
)
from app.schemas.conversation import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
)
from app.schemas.message import MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

Repository = Annotated[ConversationRepository, Depends(get_conversation_repository)]

MAX_CONVERSATIONS = 50


@router.get("", response_model=ConversationListResponse)
def list_conversations(repository: Repository) -> ConversationListResponse:
    conversations = repository.list_conversations(limit=MAX_CONVERSATIONS)
    return ConversationListResponse(
        conversations=[ConversationSummary.from_model(c) for c in conversations]
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, repository: Repository) -> ConversationDetail:
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    messages = repository.get_messages(conversation_id)
    return ConversationDetail(
        **ConversationSummary.from_model(conversation).model_dump(),
        messages=[MessageOut.from_stored(m) for m in messages],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: UUID, repository: Repository) -> Response:
    if repository.get_conversation(conversation_id) is None:
        raise ConversationNotFoundError(conversation_id)

    repository.delete_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
