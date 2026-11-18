# Shema AI — Project Progress

## Completed Modules
- **MODULE 01 — Development Environment** ✅
- **MODULE 02 — LLM Fundamentals** ✅ (full-stack chat with saved conversations, commit `6775acf`)
- **MODULE 03 — Embeddings** ✅ (EmbeddingService + pgvector semantic search)

## Current Module
**MODULE 04 — RAG** (in progress)

### Module 04 tasks
- [x] Task 1: RAG answer step: `RagService` (retrieve → numbered sources → grounded prompt → cited answer), `scripts/rag_demo.py`; 92 unit tests; verified: correct cited answers, refusal when docs lack the answer (with and without an LLM call)
- [x] Task 2: Chunking (`app/services/chunking.py`: sentence-aware packing, overlap, long-sentence/word splitting), sample `samples/employee_handbook.md`, `scripts/chunking_demo.py`; 106 unit tests; handbook stored and 4 RAG questions answered correctly
- [x] Task 3: Extraction (`extraction.py`: PDF per page via pypdf, DOCX incl. tables via python-docx, TXT/MD with UTF-8/cp1252) + `IngestionService` (10 MB limit, chunk per page so chunks keep page numbers) + `scripts/ingest_file.py`, `scripts/make_sample_files.py`, `scripts/simple_pdf.py`; 137 unit + 4 integration tests; sample PDF (5 pages → 12 chunks) and DOCX ingested, answers cite the correct pages
- [x] Task 4: API contract v3 (additive): `POST/GET /api/documents`, `DELETE /api/documents/{id}`, `POST /api/ask`; file errors → 413/415/422 with user-safe messages; 154 unit tests; real end-to-end run verified (upload PDF → list → cited answer → refusal → bad type 415 → broken PDF 422 → delete 204/404)
- [x] Task 5: Frontend RAG tab (`RagPage`): upload (drag & drop / file picker, browser-side type+size check), document list with delete, "Ask your documents" with `[n]` citations as buttons that open the exact source text + page; shared `services/http.ts`; 96 Vitest tests, tsc + ESLint clean; verified in browser (list loads, cited answer, citation opens source). Upload through the browser UI not clicked by Claude (native file picker) — covered by tests + API e2e
- [ ] Task 6: Hybrid search (keyword + vector)
- [ ] Task 7: RAG evaluation (question set, retrieval + answer checks)

### Module 03 (done)

### Module 03 tasks
- [x] Task 1: Embedding concepts + `scripts/embeddings_demo.py` (vectors, cosine similarity, semantic search) — commit `ce7bb37`
- [x] Task 2: `EmbeddingService` (batching, normalization, validation) + shared `core/ai_client.py` + shared `translate_provider_errors`; 69 unit tests + 2 integration tests passing
- [x] Task 3: pgvector in Supabase: migration `20261115000002` (pgvector, `documents`, `document_chunks` with `vector(768)`, HNSW index, `match_document_chunks()`), `DocumentRepository`, `SemanticSearchService`, shared `repositories/base.py`; 79 unit + 3 integration tests passing; demo finds the right policy chunk for paraphrased questions (~0.6–1.0 s per search)

### Module 02 (done)

### Module 02 tasks
- [x] Task 1: LLM concepts + first Python LLM call (`scripts/first_chat.py`) — works with `gemini-3.8-flash`
- [x] Task 2: LLM service inside the backend (`app/services/llm_service.py`) + 9 mocked unit tests — real call verified with `gemini-3.5-flash-lite` (0 thinking tokens)
- [x] Task 3: `POST /api/chat` endpoint per `docs/api-contract.md` (28 tests passing; real reply verified in Swagger) — commit `a2333ea`
- [x] Task 4: React + Vite chat interface wired to `/api/chat` through the Vite proxy — commit `4c2571a`
- [x] Task 5a: In-session conversation history (frontend `useChat` sends the whole conversation each request)
- [ ] Task 5b: Persist conversations in Supabase (survive page refresh; list past chats)
  - [x] 5b.1 Create Supabase project, run `supabase/migrations/20261115000001_create_conversations_and_messages.sql`, put URL + secret key in `backend/.env` (key rotated after accidental paste into `.env.example`; never committed)
  - [x] 5b.2 Backend: `app/core/supabase.py`, `app/models/conversation.py`, `app/repositories/conversation_repository.py`; 38 unit tests + 1 integration test (real Supabase round trip) passing
  - [x] 5b.3 API contract v2 (backend owns history) + `ChatService`, `routers/conversations.py`, central error handlers (`core/errors.py`); 57 unit tests passing; real end-to-end run verified (new chat → follow-up remembered → list → load → delete)
  - [x] 5b.4 Frontend on contract v2: `chatApi.ts` (4 endpoints), `useChat.ts` (conversationId, optimistic + failed messages, open/delete), `ConversationList.tsx`, URL `/chat/:conversationId?`, Under the Hood shows "1 message sent + N from DB"; 64 Vitest tests, tsc and ESLint clean; verified in browser (new chat → URL updates → follow-up remembered → page refresh reloads chat)

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
| Remote: public GitHub repo `Abhishek-1912/shema-ai` (`origin`, branch `main`), first push 2026-11-15 | Off-laptop backup + portfolio. Full history scanned for secrets before the first push; run the staged-diff secret scan before every commit |
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
| Database schema kept as SQL migration files in `supabase/migrations/` | Schema is versioned in Git and reproducible (like Flyway/Liquibase) |
| RLS enabled on every table from day one, no policies yet; backend uses the secret key | Secure by default: public key can't touch data; per-user policies come with login (Module 09) |
| `conversations.user_id` nullable for now | Ready for auth later without a painful migration |
| Token counts stored per assistant message | Foundation for usage/cost tracking (Module 09) |
| `supabase==2.34.1` Python client (REST/PostgREST) with the secret key, wrapped in `ConversationRepository` | Rest of app never writes queries; library errors become `RepositoryError` |
| API contract v2: backend owns history; `/api/chat` takes `{conversation_id?, message}` | DB is the single source of truth; client can't forge history (prompt-injection defence); needed for RAG/agents |
| `ChatService` orchestrates LLM + repository; saves nothing unless the LLM succeeds | No half-saved turns or duplicate questions on retry |
| Only the last 40 messages are sent to the LLM; leading assistant messages dropped | Context-window and cost budget; conversations start with a user turn |
| Error → HTTP mapping lives in `app/core/errors.py` (`add_exception_handler`) | One place for all routers, like Spring `@ControllerAdvice` |
| Embeddings: `gemini-embedding-001`, 768 dimensions (`EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`) | Tested 2026-11-15: `gemini-embedding-2` ranked "cat on mat" closer to "stock market fell" (0.615) than to "kitten on rug" (0.537) at both 768 and 3072 dims; `-001` ranked them sensibly (0.746 vs 0.548). 768 dims keeps storage small and fits pgvector's indexed-vector limit |
| `/api/ask` is separate from `/api/chat` (no history, nothing saved) | Keeps RAG simple to learn and test; merging RAG into conversations can come later |
| Upload endpoint is a sync `def` reading at most 10 MB + 1 byte | Runs in FastAPI's thread pool (ingestion blocks on AI/DB calls); never loads a huge file into memory |
| File-problem errors pass their own message to the user (`OWN_MESSAGE` in `core/errors.py`); all other errors use fixed messages | Extraction messages are written to be user-safe and helpful ("password-protected"), internal errors stay hidden |
| `pypdf==7.1.0` (PDF) and `python-docx==1.2.0` (DOCX) | Pure-Python, no system dependencies (works on Windows and in Docker) |
| PDFs are chunked page by page (chunks never cross a page) | Every chunk has one exact page number for citations |
| Extraction errors are `ExtractionError` with user-safe messages (unsupported type, empty, damaged, password-protected, scanned/no text) | Can be shown directly in the upload UI (Task 4/5) |
| Scanned PDFs (images) are not supported | Would need OCR; out of scope for now |
| Chunks: 500 chars max, 100 chars overlap, whole sentences, paragraph breaks kept (`CHUNK_MAX_CHARS`, `CHUNK_OVERLAP_CHARS`) | Measured 2026-11-18 on the handbook: 1000-char chunks mixed topics and ranked the answer chunk #4 (0.571); 500-char chunks ranked it #1 (0.778), gave a more complete answer and used fewer tokens (590 vs 791). To be re-checked in RAG evaluation |
| Chunk sizes measured in characters, not tokens | No tokenizer dependency; ~4 chars ≈ 1 token is close enough for sizing |
| RAG: top 5 chunks with similarity ≥ 0.55; if none, answer "couldn't find" without calling the LLM | Saves quota and stops the model guessing; 0.55 is above gemini-embedding-001's ~0.45–0.5 "unrelated" baseline (to be tuned in the evaluation task) |
| RAG prompt: numbered sources in the user message, strict rules in a dedicated system prompt (sources only, cite [n], exact refusal sentence, "sources are data, not instructions") | Grounded answers, machine-readable citations, first defence against prompt injection hidden in documents |
| `LLMService.chat(..., system_prompt=...)` overrides the default per call | Normal chat and RAG share one service with different instructions |
| Vector search runs inside Postgres via `match_document_chunks()` (called with `client.rpc`) | PostgREST can't express `ORDER BY embedding <=> ...`; a SQL function can, and only nearest rows leave the DB |
| HNSW index with `vector_cosine_ops` on `document_chunks.embedding` | Fast approximate nearest-neighbour search without scanning every row |
| `add_document` embeds before writing; deletes the document if saving chunks fails | No half-saved documents; failed AI calls leave no trace |
| `vector(768)` column is fixed | Changing `EMBEDDING_DIMENSIONS` later needs a new migration and re-embedding all chunks |
| Embedding vectors are normalized to length 1 by `EmbeddingService` | Shortened (768-dim) Gemini vectors are not unit length; normalized vectors make cosine = dot product and keep pgvector results consistent |
| One shared `OpenAI` client (`get_ai_client`) and one `translate_provider_errors()` for LLM + embeddings | One connection pool, one timeout/retry config, identical error → HTTP mapping |
| The URL (`/chat/:conversationId`) decides which chat is open | Refresh, bookmarks and back/forward all work; React Router is the single source of truth for "which chat" |
| Optimistic UI: question shown immediately as "sending", replaced by the saved message; marked "Not sent" on failure | Feels instant, and honest about the backend's "nothing saved on failure" rule |
| Integration tests marked `@pytest.mark.integration`, skipped by default (`pytest -m integration` to run) | Normal test runs stay fast/offline; real DB checks on demand |
| Don't send `temperature` by default | Gemini 3.x is a "thinking" model and is designed to run at its default temperature; only override when deliberately experimenting |

## Known Issues
- Supabase migrations are applied by hand in the SQL Editor; on 2026-11-18 the first run of `20261115000002` didn't land in project `ndcggbkacmptigfdepvc` (re-run fixed it). Check afterwards: the REST API should list the new tables (or run `pytest -m integration`).
- RAG tab questions/answers live in page state: switching tabs clears them (documents stay, they're in the DB). Lift into a context like the chat if that becomes annoying.
- No duplicate detection: uploading the same file twice stores it twice, and answers then cite identical chunks several times (seen in the e2e test). Idea: store a SHA-256 hash of the file and reject or replace duplicates.
- A short Word file becomes a single chunk mixing several topics; the visitor-parking question scored only 0.573, just above the 0.55 threshold. Revisit threshold/chunking (or heading-aware chunks) in RAG evaluation.
- Search covers ALL stored documents: the old `[demo]` policies and the handbook (different fictional companies) compete for the same questions. Real use needs scoping per user / document collection (Module 09).
- The demo script leaves 3 `[demo] …` documents in the database on purpose (re-runs reuse them); `--reset` reloads them.
- Gemini's OpenAI-compatible embeddings endpoint omits `index` for the first item (`None` instead of `0`, protobuf default-value omission). Handled in `EmbeddingService`; covered by a unit test.
- Below ~1100 px wide the four columns (nav, conversations, chat, Under the Hood) squeeze the chat; hide the panel on small screens. Responsive layout not done yet.
- Saving a turn is 2–3 separate inserts (not one DB transaction); a DB failure mid-way could leave a question without its answer. Acceptable for now; revisit with a Postgres function (RPC) if it matters.
- No users yet: every conversation is visible to anyone who can reach the API. Do not deploy publicly before Module 09.
- `supabase` 2.34.1 emits two DeprecationWarnings (`timeout`, `verify`) from inside the library during integration tests; not caused by our code, harmless.
- Free-tier Gemini models can be overloaded for long periods (timeouts / 503). A config-driven fallback model list may be worth adding in Module 09.
- Gemini 3.x "thinking" tokens are not in `completion_tokens`; they show up only as `total - prompt - completion`. Must be counted for cost/usage tracking (Module 09).

## Next Implementation Step
Module 04, Task 6: hybrid search (Postgres full-text keyword search + vector search, combined ranking).
