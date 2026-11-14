# Design — Learning Tabs + "Under the hood" panel

Date: 2026-11-15 · Status: waiting for approval · Scope: frontend only

## Why
Shema AI is being built to **learn** four concepts: LLM, RAG, MCP and LLM Wiki.
The UI should mirror that: one tab per concept, and each tab shows not only the
feature working but **what happened inside it**.

## Goals
1. A sidebar with four tabs: **LLM Chat**, **RAG**, **MCP**, **LLM Wiki**.
2. Each tab has its own web address: `/chat`, `/rag`, `/mcp`, `/wiki`. `/` goes to `/chat`.
   Back button, refresh and bookmarks work.
3. **LLM Chat tab** = the existing chat + an **"Under the hood" panel** on the right that shows
   the last request:
   - the exact list of messages sent to the backend (proves "memory" = resending history)
   - model name
   - tokens: input, output, thinking, total
   - time taken (measured in the browser)
   - on failure: HTTP status and error message
4. **RAG / MCP / LLM Wiki tabs** = short page explaining the concept in simple English,
   marked "Coming in Module 04 / 05 / 06".
5. Switching tabs does **not** erase the conversation.

## Non-goals (for now)
- Showing the system prompt (needs a backend change — added later, see Approaches).
- Saving conversations (Module 02 Task 5 / Supabase).
- Any real RAG, MCP or Wiki functionality.
- Polished mobile layout (must not break on a narrow screen, but desktop is the focus).

## Anti-goals (would be a failure even if it "works")
- The panel slows down or breaks the chat.
- Backend or `docs/api-contract.md` changes in this task.
- Business logic inside React components.

## Approaches considered
**Tab switching**
- **React Router (chosen)** — real URLs, Back button, refresh, bookmarks; already in the planned stack.
- `useState` active tab — simpler, but no URLs and would be replaced later. Rejected.

**Panel data**
- **A. Frontend-only data first (chosen by user)** — use what the frontend already has
  (sent messages, response `model` + `usage`, browser-measured time). No backend wait.
  System prompt added later via an optional contract field.
- B. Backend returns the system prompt now — complete from day one, but blocks on the backend
  tab, and exposing system prompts is a prompt-injection concern (Module 09).

## Decisions made by Claude (please check)
- **Conversation state lives above the routes** (a React context provider around the layout),
  so leaving `/chat` and coming back keeps the chat. If it lived inside the chat page,
  switching tabs would unmount it and wipe the messages.
- `useChat` additionally records a `lastExchange` object (request messages, response model/usage,
  duration, error/status). The panel is a pure display component that receives it as a prop.
- Panel can be hidden/shown with a button; shown by default.
- Sidebar entries show the module number (e.g. "RAG · Module 04").
- Library: `react-router` (current stable version, verified before install).

## Testing
- Routing: each URL shows the right page; `/` redirects to `/chat`; active tab is highlighted.
- Switching tabs and returning keeps messages.
- Panel: shows messages sent, model, tokens, time; shows the error state; empty state before
  the first message.
- `useChat`: records `lastExchange` on success and on failure.
- All existing tests keep passing; build and lint clean; manual check in the browser.

## Left to the builder
Exact styling, icons, wording of the concept pages (simple English, beginner level).
