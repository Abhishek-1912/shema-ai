// Who wrote a message: the person using the app, or the AI.
export type MessageRole = 'user' | 'assistant'

// One message in a conversation.
export interface Message {
  id: string
  role: MessageRole
  content: string
}
