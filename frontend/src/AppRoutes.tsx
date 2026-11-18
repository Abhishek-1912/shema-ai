import { Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout'
import AgentPage from './pages/AgentPage'
import ChatPage from './pages/ChatPage'
import RagPage from './pages/RagPage'
import WikiArticlePage from './pages/wiki/WikiArticlePage'
import WikiEditorPage from './pages/wiki/WikiEditorPage'
import WikiListPage from './pages/wiki/WikiListPage'

// The route table: which URL shows which page.
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        {/* ":conversationId?" = optional part of the URL: /chat or /chat/<id> */}
        <Route path="chat/:conversationId?" element={<ChatPage />} />
        <Route path="rag" element={<RagPage />} />
        <Route path="mcp" element={<AgentPage />} />
        <Route path="wiki" element={<WikiListPage />} />
        {/* "new" is listed before ":slug", but React Router ranks exact words above
            parameters anyway, so /wiki/new never means "the article called new". */}
        <Route path="wiki/new" element={<WikiEditorPage />} />
        <Route path="wiki/:slug" element={<WikiArticlePage />} />
        <Route path="wiki/:slug/edit" element={<WikiEditorPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  )
}
