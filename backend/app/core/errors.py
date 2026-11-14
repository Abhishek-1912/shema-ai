"""Turn our own exceptions into HTTP responses, in ONE place for every router.

Like Spring's @ControllerAdvice + @ExceptionHandler. Routers just let errors bubble up.
Users get a fixed, safe message; the real details go only to the server log.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.repositories.conversation_repository import ConversationNotFoundError, RepositoryError
from app.services.llm_service import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

# exception class → (HTTP status, message shown to the user, log level)
# FastAPI picks the most specific match, so subclasses win over LLMServiceError.
ERROR_MAP: dict[type[Exception], tuple[int, str, int]] = {
    ConversationNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "Conversation not found.",
        logging.INFO,
    ),
    LLMRateLimitError: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "The AI is receiving too many requests. Please wait a moment and try again.",
        logging.WARNING,
    ),
    LLMConfigurationError: (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "The AI service is not configured correctly. Please contact the administrator.",
        logging.ERROR,
    ),
    LLMServiceError: (
        status.HTTP_502_BAD_GATEWAY,
        "The AI service returned an unexpected response. Please try again.",
        logging.ERROR,
    ),
    LLMUnavailableError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The AI service is busy or unreachable right now. Please try again in a minute.",
        logging.WARNING,
    ),
    RepositoryError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Could not reach the database. Please try again in a minute.",
        logging.ERROR,
    ),
}


def register_exception_handlers(app: FastAPI) -> None:
    for error_class, (status_code, user_message, log_level) in ERROR_MAP.items():

        def handler(
            request: Request,
            error: Exception,
            status_code: int = status_code,
            user_message: str = user_message,
            log_level: int = log_level,
        ) -> JSONResponse:
            logger.log(log_level, "%s %s -> %s: %s", request.method, request.url.path, status_code, error)
            return JSONResponse(status_code=status_code, content={"detail": user_message})

        app.add_exception_handler(error_class, handler)
