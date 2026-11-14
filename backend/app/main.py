from fastapi import FastAPI

from app.core.errors import register_exception_handlers
from app.routers import chat, conversations

app = FastAPI(
    title="Shema AI API",
    version="0.2.0",
    description="Backend for the Shema AI knowledge assistant.",
)

register_exception_handlers(app)
app.include_router(chat.router)
app.include_router(conversations.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello from Shema AI"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
