import { BrowserRouter } from 'react-router'
import { AppRoutes } from './AppRoutes'
import { ChatProvider } from './context/ChatContext'

function App() {
  return (
    <BrowserRouter>
      <ChatProvider>
        <AppRoutes />
      </ChatProvider>
    </BrowserRouter>
  )
}

export default App
