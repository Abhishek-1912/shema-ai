# Shema AI — API Contract

The agreement between the React frontend and the FastAPI backend.
Both sides must match this document. Change it here first, then update both sides.

All endpoints are under `/api`. In development the frontend calls `/api/...` on its own
origin (`http://localhost:5173`) and the Vite dev server proxies it to `http://localhost:8000`.

**Version 2 — the backend owns the conversation history.**
The frontend sends only the new message (plus which conversation it belongs to).
The backend loads earlier messages from the database, adds the system prompt, calls the LLM,
and saves both the question and the answer.

> Until login is added (Module 09) there are no users: every conversation is visible to
> anyone who can reach the API.

---

## Shared shapes

### `Message`

```json
{
  "id": "9b1c...-uuid",
  "role": "assistant",
  "content": "Sure! For example, ...",
  "created_at": "2026-11-15T10:00:05.123456Z",
  "model": "gemini-3.5-flash-lite",
  "usage": {
    "input_tokens": 42,
    "output_tokens": 120,
    "thinking_tokens": 0,
    "total_tokens": 162
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Use as the React list key. |
| `role` | `"user"` \| `"assistant"` | |
| `content` | string | |
| `created_at` | string (ISO 8601 date-time, UTC) | |
| `model` | string \| `null` | Only for assistant messages; `null` for user messages. |
| `usage` | `TokenUsage` \| `null` | Only for assistant messages; `null` for user messages or if the provider did not report it. |

### `TokenUsage`

`{ "input_tokens": int, "output_tokens": int, "thinking_tokens": int, "total_tokens": int }`

### `ConversationSummary`

```json
{
  "id": "3f2a...-uuid",
  "title": "What is an LLM?",
  "created_at": "2026-11-15T10:00:00Z",
  "updated_at": "2026-11-15T10:05:00Z"
}
```

`title` is the first user message, trimmed and cut to 60 characters (with `…` if longer).

---

## `POST /api/chat`

Send one new message and get the AI's reply.

### Request body

```json
{
  "conversation_id": "3f2a...-uuid",
  "message": "Give me an example."
}
```

| Field | Type | Rules |
|---|---|---|
| `conversation_id` | string (UUID) \| `null` \| omitted | Omit or `null` to **start a new conversation**. Otherwise must be an existing conversation. |
| `message` | string | Not empty after trimming. Max 8000 characters. |

### What the backend does

1. Loads the conversation's earlier messages (if `conversation_id` was given).
2. Sends the system prompt + the most recent messages (up to 40) + the new message to the LLM.
3. **Only if the LLM succeeds:** creates the conversation (if new), saves the user message,
   then saves the assistant message. If the LLM call fails, **nothing is saved**.

### Success response — `200 OK`

```json
{
  "conversation_id": "3f2a...-uuid",
  "user_message": { "...": "Message (role user)" },
  "assistant_message": { "...": "Message (role assistant)" }
}
```

| Field | Type | Notes |
|---|---|---|
| `conversation_id` | string (UUID) | The new ID when a conversation was just created. Send it with the next message. |
| `user_message` | `Message` | The saved question. |
| `assistant_message` | `Message` | The saved answer, with `model` and `usage`. |

---

## `GET /api/conversations`

List conversations, most recently active first (max 50).

### Success response — `200 OK`

```json
{ "conversations": [ "ConversationSummary", "..." ] }
```

---

## `GET /api/conversations/{conversation_id}`

Load one conversation with all its messages, oldest first.

### Success response — `200 OK`

```json
{
  "id": "3f2a...-uuid",
  "title": "What is an LLM?",
  "created_at": "2026-11-15T10:00:00Z",
  "updated_at": "2026-11-15T10:05:00Z",
  "messages": [ "Message", "..." ]
}
```

---

## `DELETE /api/conversations/{conversation_id}`

Delete a conversation and all its messages.

### Success response — `204 No Content` (empty body)

---

## Error responses (all endpoints)

FastAPI's standard shape: `{ "detail": "<human-readable message>" }`.

| Status | When | Backend cause |
|---|---|---|
| `404` | `conversation_id` does not exist | Repository returned nothing |
| `422` | Request breaks the rules above (incl. a `conversation_id` that is not a UUID) | FastAPI/Pydantic validation (here `detail` is a list) |
| `429` | LLM rate limit / free-tier quota used up | `LLMRateLimitError` |
| `500` | Server misconfigured (bad API key, bad model name) | `LLMConfigurationError` |
| `502` | LLM answered but the result was unusable (e.g. empty reply) | `LLMServiceError` (base class) |
| `503` | LLM or database unreachable / timeout / overloaded | `LLMUnavailableError`, `RepositoryError` |

The frontend shows `detail` to the user when it is a string, otherwise a generic message.
Error messages must never contain API keys, database errors, or other internal details.

---

## Changes from version 1

| v1 | v2 |
|---|---|
| Request: `{ "messages": [...] }` (whole history) | Request: `{ "conversation_id", "message" }` (one new message) |
| Response: `{ "reply", "model", "usage" }` | Response: `{ "conversation_id", "user_message", "assistant_message" }` |
| Nothing saved | Everything saved in Supabase |
| — | New: `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}` |
