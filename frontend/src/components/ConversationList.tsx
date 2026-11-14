import { Link, NavLink } from 'react-router'
import type { ConversationSummary } from '../types/chat'

interface ConversationListProps {
  conversations: ConversationSummary[]
  onDelete: (id: string) => void
}

// The list of saved chats. Each chat is a link to /chat/<id>, so the URL always
// says which conversation is open (and a page refresh reopens it).
function ConversationList({ conversations, onDelete }: ConversationListProps) {
  return (
    <section
      aria-label="Conversations"
      className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white"
    >
      <div className="p-3">
        <Link
          to="/chat"
          className="block rounded-lg bg-blue-600 px-3 py-2 text-center font-medium text-white hover:bg-blue-700"
        >
          + New chat
        </Link>
      </div>

      {conversations.length === 0 ? (
        <p className="px-4 text-sm text-slate-400">No saved conversations yet.</p>
      ) : (
        <ul className="flex-1 space-y-1 overflow-y-auto px-2 pb-3">
          {conversations.map((conversation) => (
            <li key={conversation.id} className="group flex items-center gap-1">
              <NavLink
                to={`/chat/${conversation.id}`}
                title={conversation.title}
                className={({ isActive }) =>
                  `min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-sm ${
                    isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-100'
                  }`
                }
              >
                {conversation.title}
              </NavLink>
              <button
                type="button"
                aria-label={`Delete conversation "${conversation.title}"`}
                onClick={() => {
                  if (window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) {
                    onDelete(conversation.id)
                  }
                }}
                className="rounded px-2 py-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default ConversationList
