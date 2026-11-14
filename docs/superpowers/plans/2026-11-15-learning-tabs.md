# Learning Tabs + "Under the hood" Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sidebar with four learning tabs (LLM Chat, RAG, MCP, LLM Wiki) on their own URLs, and an "Under the hood" panel on the LLM Chat tab that shows the last request's internals.

**Architecture:** `useChat` additionally records a `lastExchange`. A `ChatProvider` context holds one `useChat()` instance above the router outlet so the conversation survives tab switches. React Router renders a `Layout` (sidebar + `<Outlet/>`) with `/chat`, `/rag`, `/mcp`, `/wiki`; `ChatPage` shows the chat plus a pure `UnderTheHoodPanel`.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Tailwind 4, react-router 8.5.x (new), Vitest 5 + Testing Library.

**Spec:** `docs/superpowers/specs/2026-11-15-learning-tabs-design.md`

## Global Constraints

- Frontend only. No changes to `backend/`, `docs/api-contract.md` or `PROJECT_PROGRESS.md` (owned by the backend tab).
- No business logic in components; data/logic in hooks, components display props.
- URLs: `/chat`, `/rag`, `/mcp`, `/wiki`; `/` redirects to `/chat`.
- Sidebar labels: "LLM Chat · Module 02", "RAG · Module 04", "MCP · Module 05", "LLM Wiki · Module 06".
- Panel shown by default, toggle button hides/shows it.
- Use `import type` for type-only imports (`verbatimModuleSyntax`).
- Do not commit unless the user asks (user commits themselves).
- User is a beginner: after each task, explain the new concepts and wait for confirmation.

## Review Focus

1. Navigating away from `/chat` and back keeps all messages → test in Task 4 (`keeps the conversation when switching tabs`).
2. Unknown URL (e.g. `/xyz`) → redirect to `/chat`, not a blank page → test in Task 4.
3. Failed request (no HTTP response, `status: null`) → panel shows the error without a status code, chat still usable → test in Task 3.
4. `usage: null` from backend → panel shows "not reported" instead of crashing → test in Task 3.
5. Refreshing on `/rag` in the dev server → shows RAG page (Vite serves index.html for SPA routes by default) → manual check in Task 4.

---

### Task 1: `useChat` records `lastExchange`

**Files:**
- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/hooks/useChat.ts`
- Test: `frontend/src/hooks/useChat.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface LastExchange {
    sentMessages: ChatApiMessage[]
    durationMs: number
    response: ChatResponse | null      // null when the request failed
    error: { message: string; status: number | null } | null
  }
  // useChat() now returns { messages, isLoading, error, lastExchange: LastExchange | null, sendMessage }
  ```

- [ ] **Step 1: Write failing tests** in `useChat.test.ts`:
  - `records the last exchange on success`: mock `sendChat` resolving `{ reply: 'Hi', model: 'gemini-test', usage: { input_tokens: 5, output_tokens: 2, thinking_tokens: 0, total_tokens: 7 } }`; after `sendMessage('Hello')`: `lastExchange.sentMessages` equals `[{ role: 'user', content: 'Hello' }]`, `lastExchange.response.model === 'gemini-test'`, `lastExchange.error === null`, `lastExchange.durationMs >= 0`.
  - `records the last exchange on failure`: mock rejecting `new ChatApiError('Busy', 503)`; `lastExchange.response === null`, `lastExchange.error` equals `{ message: 'Busy', status: 503 }`.
  - Extend `starts empty...`: `lastExchange` is `null`.
- [ ] **Step 2: Run** `npm run test:run -- useChat` → the new tests FAIL.
- [ ] **Step 3: Implement.** Add `LastExchange` to `types/chat.ts`; in `useChat` add `useState<LastExchange | null>(null)`, measure with `performance.now()` around `sendChat`, set it in both success and catch branches. Non-`ChatApiError` errors record `status: null` and the generic message.
- [ ] **Step 4: Run** `npm run test:run` → all PASS.

### Task 2: `ChatProvider` context

**Files:**
- Create: `frontend/src/context/ChatContext.tsx`
- Test: `frontend/src/context/ChatContext.test.tsx`

**Interfaces:**
- Consumes: `useChat()` return type from Task 1.
- Produces:
  ```ts
  export function ChatProvider({ children }: { children: ReactNode }): JSX.Element
  export function useChatContext(): ReturnType<typeof useChat>   // throws if used outside ChatProvider
  ```

- [ ] **Step 1: Write failing tests:**
  - `gives children access to the chat`: a test component calling `useChatContext()` and rendering `messages.length` shows `0` inside `<ChatProvider>`.
  - `throws a clear error outside the provider`: `renderHook(() => useChatContext())` throws `/inside <ChatProvider>/`.
- [ ] **Step 2: Run** → FAIL (module missing).
- [ ] **Step 3: Implement** with `createContext<ReturnType<typeof useChat> | null>(null)`. ESLint `react-refresh/only-export-components` may warn about exporting a hook next to a component; if so, put `useChatContext` in `frontend/src/context/useChatContext.ts` and the context object in `chatContextValue.ts`.
- [ ] **Step 4: Run** tests, lint → PASS / clean.

### Task 3: `UnderTheHoodPanel`

**Files:**
- Create: `frontend/src/components/UnderTheHoodPanel.tsx`
- Test: `frontend/src/components/UnderTheHoodPanel.test.tsx`

**Interfaces:**
- Consumes: `LastExchange` (Task 1).
- Produces: `function UnderTheHoodPanel({ lastExchange }: { lastExchange: LastExchange | null }): JSX.Element` — pure display, `<aside aria-label="Under the hood">`.

- [ ] **Step 1: Write failing tests:**
  - `explains itself before the first message`: `lastExchange={null}` → text `/send a message/i`.
  - `shows what was sent and what came back`: 3 sent messages → each content visible and text `3 messages sent`; model `gemini-test` visible; tokens `5`, `2`, `0`, `7` visible next to labels Input / Output / Thinking / Total; duration `1234` ms rendered as `1.23 s`.
  - `shows usage as not reported when null`: `response.usage = null` → `/not reported/i`.
  - `shows an error with status`: error `{ message: 'Busy', status: 503 }` → `503` and `Busy` visible.
  - `shows an error without status`: `{ message: 'Cannot reach', status: null }` → `Cannot reach` visible, no `null` text.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Sections: "Messages sent" (role badge + content, scrollable), "Model", "Tokens" (4 values), "Time", "Error" (only if error). Include one sentence of explanation per section for the learner (e.g. under Messages sent: "The LLM has no memory — the whole conversation is sent every time.").
- [ ] **Step 4: Run** tests, build, lint → PASS / clean.

### Task 4: Router, sidebar, pages

**Files:**
- Modify: `frontend/package.json` (add `react-router`)
- Create: `frontend/src/components/Layout.tsx` (sidebar + `<Outlet/>`)
- Create: `frontend/src/pages/ChatPage.tsx` (MessageList + ChatInput + panel + toggle; reads `useChatContext()`)
- Create: `frontend/src/pages/ConceptPage.tsx` (`{ title, module, summary, points: string[] }` → "Coming in Module NN" page)
- Create: `frontend/src/AppRoutes.tsx` (route table, exported for tests)
- Modify: `frontend/src/App.tsx` (`<BrowserRouter><ChatProvider><AppRoutes/></ChatProvider></BrowserRouter>`)
- Test: `frontend/src/AppRoutes.test.tsx`

**Interfaces:**
- Consumes: `ChatProvider`, `useChatContext` (Task 2), `UnderTheHoodPanel` (Task 3), existing `MessageList`, `ChatInput`.
- Produces: `export function AppRoutes(): JSX.Element` — routes: `/` → `<Navigate to="/chat" replace/>`, `/chat`, `/rag`, `/mcp`, `/wiki` inside `Layout`, `*` → `<Navigate to="/chat" replace/>`.

- [ ] **Step 1: Install** `npm install react-router` and verify in `node_modules/react-router` that v8 still exports `BrowserRouter`, `MemoryRouter`, `Routes`, `Route`, `NavLink`, `Navigate`, `Outlet`. If any changed, use the v8 equivalent and note it.
- [ ] **Step 2: Write failing tests** (render `<MemoryRouter initialEntries={[path]}><ChatProvider><AppRoutes/></ChatProvider></MemoryRouter>`, `sendChat` mocked):
  - `redirects / to the chat`: chat textbox present.
  - `redirects unknown URLs to the chat`: `/xyz` → chat textbox present.
  - `shows each concept page`: `/rag` → heading `RAG` + `/Module 04/`; same for `/mcp` (05), `/wiki` (06).
  - `highlights the active tab`: on `/rag`, the RAG link has `aria-current="page"` (NavLink default).
  - `keeps the conversation when switching tabs`: send "Hello" (mock reply "Hi there"), click RAG link, click LLM Chat link → "Hello" and "Hi there" still visible.
  - `hides and shows the panel`: button `Hide under the hood` removes `aside[aria-label="Under the hood"]`; `Show under the hood` brings it back.
- [ ] **Step 3: Run** → FAIL.
- [ ] **Step 4: Implement.** Layout: left sidebar (`NavLink`s with the Global Constraints labels, active style via `className` callback), main area `<Outlet/>`, full height. Move header out of `App.tsx` into the sidebar. ChatPage: chat column + panel column (panel ~w-96, hidden below `lg` breakpoint is acceptable). Concept page texts: simple English, 2–4 bullets each (RAG: answers from your own documents; MCP: standard way to give the AI tools; Wiki: structured knowledge the AI maintains and cites).
- [ ] **Step 5: Run** `npm run test:run`, `npm run build`, `npm run lint` → all PASS / clean.
- [ ] **Step 6: Manual check** in browser at http://localhost:5173: click all tabs, Back button, refresh on `/rag` (stays on RAG), send a chat and see the panel fill in, switch tab and return (chat kept).
