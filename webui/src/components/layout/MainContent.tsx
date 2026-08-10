import { Terminal } from '@/components/console/Terminal'
import { useLogWebSocket } from '@/hooks/useWebSocket'

export function MainContent() {
  // Connect to WebSocket for logs
  useLogWebSocket()

  return (
    <main className="flex-shrink-0 flex flex-col overflow-hidden min-h-0 relative z-10">
      <Terminal />
    </main>
  )
}
