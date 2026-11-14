"""HTTP layer for chat: validate the request, call the service, map errors to status codes.

No AI logic lives here. The router only translates between HTTP and LLMService.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import (
    ChatMessage,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMService,
    LLMServiceError,
    LLMUnavailableError,
    get_llm_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    llm: Annotated[LLMService, Depends(get_llm_service)],
) -> ChatResponse:
    # Convert API messages (validated input) into service messages.
    messages = [ChatMessage(role=m.role, content=m.content) for m in request.messages]

    try:
        result = llm.chat(messages)
    except LLMRateLimitError as error:
        logger.warning("LLM rate limit: %s", error)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI is receiving too many requests. Please wait a moment and try again.",
        ) from error
    except LLMConfigurationError as error:
        # Details (model name etc.) go to the server log, not to the user.
        logger.error("LLM configuration problem: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI service is not configured correctly. Please contact the administrator.",
        ) from error
    except LLMUnavailableError as error:
        logger.warning("LLM unavailable: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is busy or unreachable right now. Please try again in a minute.",
        ) from error
    except LLMServiceError as error:
        logger.error("LLM returned an unexpected result: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an unexpected response. Please try again.",
        ) from error

    return ChatResponse(reply=result.content, model=result.model, usage=result.usage)
