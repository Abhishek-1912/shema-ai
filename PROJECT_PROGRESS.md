# Shema AI — Project Progress

## Completed Modules
_None yet._

## Current Module
**MODULE 01 — Development Environment**

## Completed Features
- [x] Verified tools: Python 3.13.17, pip 26.2.2, Node.js 24.21.0, npm 11.19.0, Git 2.52.0
- [x] Git configured (user name/email, default branch `main`)
- [x] Git repository initialized
- [x] Created `backend/` and `frontend/` folders (monorepo layout)
- [x] Added `.gitignore` (secrets, Python, Node, editor files)

## Pending Tasks (Module 01)
- [ ] First Git commit
- [ ] Python virtual environment in `backend/`
- [ ] Install FastAPI and run a "hello world" backend
- [ ] Create React + Vite + TypeScript app in `frontend/`
- [ ] Environment variables (`.env` / `.env.example`)
- [ ] Before Module 02: create OpenAI API key and add billing credits

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

## Next Implementation Step
Make the first Git commit, then create the Python virtual environment.
