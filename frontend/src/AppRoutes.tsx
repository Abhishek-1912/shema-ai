import { Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import ConceptPage from './pages/ConceptPage'
import { mcpConcept, ragConcept, wikiConcept } from './pages/concepts'

// The route table: which URL shows which page.
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="rag" element={<ConceptPage {...ragConcept} />} />
        <Route path="mcp" element={<ConceptPage {...mcpConcept} />} />
        <Route path="wiki" element={<ConceptPage {...wikiConcept} />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  )
}
