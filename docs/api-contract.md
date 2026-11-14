# Shema AI — API Contract

The agreement between the React frontend and the FastAPI backend.
Both sides must match this document. Change it here first, then update both sides.

All endpoints are under `/api`. In development the frontend calls `/api/...` on its own
origin (`http://localhost:5173`) and the Vite dev server proxies it to `http://localhost:8000`.

---

## `POST /api/chat`

Send the conversation so far and get the AI's next reply.

The LLM has **no memory between calls**, so the frontend sends the **whole conversation**
every time, oldest message first. The last message is the new user question.
The backend adds the system prompt itself — the frontend never sends one.

### Request body

```json
{
  "messages": [
    { "role": "user", "content": "What is an LLM?" },
    { "role": "assistant", "content": "An LLM is ..." },
    { "role": "user", "content": "Give me an example." }
  ]
}
```

| Field | Type | Rules |
|---|---|---|
| `messages` | array | At least 1 item. Last item must have `role: "user"`. |
| `messages[].role` | `"user"` \| `"assistant"` | Nothing else allowed (no `"system"` from the client). |
| `messages[].content` | string | Not empty after trimming. |

### Success response — `200 OK`

```json
{
  "reply": "Sure! For example, ...",
  "model": "gemini-3.8-flash",
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
| `reply` | string | The assistant's answer (maps to `LLMResult.content`). |
| `model` | string | Model that produced the answer. |
| `usage` | object \| `null` | Token counts (maps to `TokenUsage`); `null` if the provider did not report them. |

### Error responses

FastAPI's standard shape: `{ "detail": "<human-readable message>" }`.

| Status | When | Backend cause |
|---|---|---|
| `422` | Request body breaks the rules above | FastAPI/Pydantic validation (here `detail` is a list) |
| `429` | Rate limit / free-tier quota used up | `LLMRateLimitError` |
| `500` | Server misconfigured (bad API key, bad model name) | `LLMConfigurationError` |
| `502` | Provider answered but the result was unusable (e.g. empty reply, unexpected HTTP error) | `LLMServiceError` (base class) |
| `503` | Provider unreachable / outage / timeout / overloaded | `LLMUnavailableError` |

The frontend shows `detail` to the user when it is a string, otherwise a generic message.
Error messages must never contain the API key or other secrets.
