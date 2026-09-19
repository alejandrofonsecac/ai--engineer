export type Session = {
  id: string
  simulator: 'ACC' | 'iRacing'
  car: string
  track: string
  session_type: string
  current_setup_version: number
  has_setup: boolean
}
export type ChatMessage = { role: 'user' | 'assistant'; content: string }
export type Health = { available: boolean; model: string; detail: string }
export type SetupFileInput = { filename: string; content: Record<string, unknown> }
export type SessionInput = Pick<Session, 'simulator' | 'car' | 'track' | 'session_type'> & {
  setup_file?: SetupFileInput
}

// O navegador só acessa FastAPI. Ollama é uma dependência privada do backend.
const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

async function request<T>(path: string, options: RequestInit = {}, timeout = 10000): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(base + path, {
      ...options, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
    const body = await response.json()
    if (!response.ok) {
      throw new Error(typeof body.detail === 'string' ? body.detail : 'Dados inválidos. Confira os campos da sessão.')
    }
    return body as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Tempo de espera excedido. A resposta pode continuar no backend; recarregue a conversa antes de reenviar.')
    }
    if (error instanceof TypeError) {
      throw new Error('Backend inacessível. Inicie o FastAPI em 127.0.0.1:8000.')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

export const api = {
  health: () => request<Health>('/health/llm'),
  create: (session: SessionInput) => request<Session>('/sessions', { method: 'POST', body: JSON.stringify(session) }),
  session: (id: string) => request<Session>('/sessions/' + encodeURIComponent(id)),
  messages: (id: string) => request<ChatMessage[]>('/sessions/' + encodeURIComponent(id) + '/messages'),
  send: (id: string, content: string) => request<{ engineer_message: string }>(
    '/sessions/' + encodeURIComponent(id) + '/messages',
    { method: 'POST', body: JSON.stringify({ content }) }, 210000,
  ),
}
