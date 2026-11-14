# Shema AI — Project Progress

## Completed Modules
- **MODULE 01 — Development Environment** ✅

## Current Module
**MODULE 02 — LLM Fundamentals** (not started)

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

## Known Issues
_None._

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
| Chat model: `gemini-3.8-flash` (fallback: `gemini-2.5-flash`) | Newest stable Flash model on the key's model list; avoid `-preview` and moving `-latest` aliases. Free-tier quota to be confirmed with first real call in Module 02 |

## Next Implementation Step
Module 02, Task 1: LLM fundamentals (tokens, prompts, temperature), then the first Python script that sends a chat message to Gemini through the OpenAI SDK.
