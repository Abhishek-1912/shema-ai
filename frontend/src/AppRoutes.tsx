import { Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout'
import AgentPage from './pages/AgentPage'
import ChatPage from './pages/ChatPage'
import ConceptPage from './pages/ConceptPage'
import RagPage from './pages/RagPage'
import { wikiConcept } from './pages/concepts'

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
        <Route path="wiki" element={<ConceptPage {...wikiConcept} />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  )
}
