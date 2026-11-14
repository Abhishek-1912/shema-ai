# Shema AI — Project Progress

## Completed Modules
- **MODULE 01 — Development Environment** ✅

## Current Module
**MODULE 02 — LLM Fundamentals** (in progress)

### Module 02 tasks
- [x] Task 1: LLM concepts + first Python LLM call (`scripts/first_chat.py`) — works with `gemini-3.8-flash`
- [x] Task 2: LLM service inside the backend (`app/services/llm_service.py`) + 9 mocked unit tests — real call verified with `gemini-3.5-flash-lite` (0 thinking tokens)
- [ ] Task 3: `POST /api/chat` endpoint per `docs/api-contract.md` (`app/schemas/chat.py`, `app/routers/chat.py`, 15 API tests; 28 total passing). Real call returned 429 (free-tier rate limit) on 2026-11-15: error mapping verified, a successful real reply still to be confirmed
- [ ] Task 4: React + Vite chat interface
- [ ] Task 5: Conversation history

## Completed Features
- [x] Verified tools: Python 3.13.17, pip 26.2.2, Node.js 24.21.0, npm 11.19.0, Git 2.52.0
- [x] Git configured (user name/email, default branch `main`)
- [x] Git repository initialized
- [x] Created `backend/` and `frontend/` folders (monorepo layout)
- [x] Added `.gitignore` (secrets, Python, Node, editor files)

## Pending Tasks (Module 01)
- [x] First Git commit (`4ac533c`)
- [x] Python virtual environment in `backend/.venv`
- [x] Installed FastAPI 0.163.0 and ran the "hello world" backend (`/`, `/health`, `/docs`)
- [x] `requirements.txt` + first pytest tests (3 passing)
- [x] Second Git commit (`72b334f`)
- [x] Environment variables: `app/core/config.py` (pydantic-settings), `.env.example`, `.cursorignore`, config tests (6 tests passing)
- [x] Created Gemini API key and local `.env`; key verified with `scripts/list_models.py`
- [ ] Create React + Vite + TypeScript app in `frontend/` (moved to Module 02, when we build the chat UI)

## Technical Decisions
| Decision | Why |
|---|---|
| Monorepo (`backend/` + `frontend/` in one repo) | One place to track the whole app; two separate apps talking over HTTP |
| Python 3.13 (not 3.14) | Best compatibility with AI libraries right now |
| Node.js 24 LTS | Long-term-support version, stable for Vite/React |
| Editor: Cursor | User preference |
| Secrets only in `.env`, never committed | Prevent API key leaks |
| LLM provider: Google Gemini API free tier, called through the OpenAI Python SDK (`base_url` = Gemini's OpenAI-compatible endpoint) | No budget for paid OpenAI; Gemini free tier covers chat, embeddings and tool calling; switching to OpenAI later = change `.env` only |
| Not using Ollama (local models) | Laptop has 7.8 GB RAM + integrated GPU — too slow for useful local models |
| Test only with public documents | Gemini free tier may use submitted data to improve Google products |
| Config via `pydantic-settings` (`Settings` class, `get_settings()` cached) | Typed, validated config — app fails fast at startup if a required variable is missing; like Spring `@ConfigurationProperties` |
| API key stored as `SecretStr` | Prevents the key from appearing in logs/prints by accident |
| Generic `LLM_*` variable names (not `GEMINI_*`) | Provider can be switched by editing `.env` only |
| `.cursorignore` excludes `.env` | Keeps secrets out of the editor's AI context |
| Chat model: `gemini-3.5-flash-lite` for now (was `gemini-3.8-flash`) | On 2026-11-15 `gemini-3.8-flash` was overloaded on the free tier (timeouts up to 470 s, HTTP 503); `gemini-3.5-flash-lite` answered in ~1 s. `gemini-2.5-flash` returns 404 "no longer available to new users", so it is NOT a fallback. Model is `.env`-only, so switching back is one line |
| LLM timeout 30 s (`LLM_TIMEOUT_SECONDS`), SDK `max_retries=2` | Fail within ~1.5 min instead of hanging; timeouts and 503 become `LLMUnavailableError` with a clear message |
| `openai==3.51.0` SDK | Pinned version installed in venv |
| All LLM calls go through `LLMService` (constructor-injected `OpenAI` client) | One place to change provider/logging; injection makes mocking in tests possible |
| Service raises its own errors (`LLMRateLimitError`, `LLMConfigurationError`, `LLMUnavailableError`) | Rest of the app doesn't depend on OpenAI SDK exception types |
| Unit tests mock the client, never call Gemini | Fast, free, offline, deterministic |
| `docs/api-contract.md` is the source of truth for frontend↔backend | Change the contract first, then both sides. Added `502` for unusable provider results (`LLMServiceError` base) |
| Router has no AI logic; maps service errors → HTTP (429/500/502/503) with fixed user-safe messages, details only in server logs | Separation of concerns; never leak model names/keys to users |
| Tests swap the service with `app.dependency_overrides` | FastAPI's built-in way to inject fakes (like `@MockBean`) |
| Don't send `temperature` by default | Gemini 3.x is a "thinking" model and is designed to run at its default temperature; only override when deliberately experimenting |

## Known Issues
- Free-tier Gemini models can be overloaded for long periods (timeouts / 503). A config-driven fallback model list may be worth adding in Module 09.
- Gemini 3.x "thinking" tokens are not in `completion_tokens`; they show up only as `total - prompt - completion`. Must be counted for cost/usage tracking (Module 09).

## Next Implementation Step
Confirm a real 200 reply from `POST /api/chat` once the rate limit resets, then connect the existing React frontend (`frontend/`, uses the Vite `/api` proxy) and test the full chat in the browser.
