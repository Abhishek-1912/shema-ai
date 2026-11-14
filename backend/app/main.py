from fastapi import FastAPI

from app.routers import chat

app = FastAPI(
    title="Shema AI API",
    version="0.1.0",
    description="Backend for the Shema AI knowledge assistant.",
)

app.include_router(chat.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello from Shema AI"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
