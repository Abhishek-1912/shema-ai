import { NavLink, Outlet } from 'react-router'
import { useChatContext } from '../context/useChatContext'

// The frame around every page: sidebar on the left, the current page on the right.
function Layout() {
  const { conversationId } = useChatContext()

  const tabs = [
    // Coming back to the chat tab reopens the conversation you left.
    { to: conversationId ? `/chat/${conversationId}` : '/chat', label: 'LLM Chat', module: 'Module 02' },
    { to: '/rag', label: 'RAG', module: 'Module 04' },
    { to: '/mcp', label: 'MCP', module: 'Module 05' },
    { to: '/wiki', label: 'LLM Wiki', module: 'Module 06' },
    { to: '/research', label: 'Research', module: 'Module 07' },
  ]

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <nav className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-6 px-2">
          <p className="text-xl font-semibold">Shema AI</p>
          <p className="text-xs text-slate-500">Your AI knowledge assistant</p>
        </div>

        <ul className="space-y-1">
          {tabs.map((tab) => (
            <li key={tab.label}>
              <NavLink
                to={tab.to}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 ${
                    isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-100'
                  }`
                }
              >
                <span className="block font-medium">{tab.label}</span>
                <span className="block text-xs text-slate-500">{tab.module}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* The page that matches the current URL is drawn here. */}
      <Outlet />
    </div>
  )
}

export default Layout
