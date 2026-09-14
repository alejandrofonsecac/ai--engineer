import { FormEvent, useEffect, useRef, useState } from 'react'
import { api, ChatMessage, Session, SessionInput } from './api'

export function LiveSessionForm({ onCreated }: { onCreated: (id: string) => void }) {
  const [form, setForm] = useState<SessionInput>({
    simulator: 'ACC', car: 'Porsche 992 GT3 R', track: 'Nürburgring Nordschleife',
    session_type: 'Desenvolvimento de setup',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const session = await api.create(form)
      onCreated(session.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível criar a sessão.')
    } finally { setBusy(false) }
  }
  return (
    <main className="content content--form">
      <div className="page-title"><div>
        <p className="eyebrow">Virtual Race Engineer</p>
        <h1>Nova sessão</h1>
        <p className="page-description">Conte ao seu engenheiro o que você vai pilotar hoje.</p>
      </div></div>
      <form className="session-form" onSubmit={submit}>
        <div className="form-grid">
          <div className="field"><label htmlFor="simulator">Simulador</label>
            <select id="simulator" value={form.simulator} disabled={busy}
              onChange={e => setForm({ ...form, simulator: e.target.value as SessionInput['simulator'] })}>
              <option value="ACC">Assetto Corsa Competizione</option><option value="iRacing">iRacing</option>
            </select>
          </div>
          <div className="field"><label htmlFor="car">Carro</label>
            <input id="car" required minLength={2} maxLength={120} value={form.car} disabled={busy}
              onChange={e => setForm({ ...form, car: e.target.value })} />
          </div>
          <div className="field"><label htmlFor="track">Pista</label>
            <input id="track" required minLength={2} maxLength={120} value={form.track} disabled={busy}
              onChange={e => setForm({ ...form, track: e.target.value })} />
          </div>
        </div>
        <div className="field form-block"><label htmlFor="sessionType">Tipo de sessão</label>
          <select id="sessionType" value={form.session_type} disabled={busy}
            onChange={e => setForm({ ...form, session_type: e.target.value })}>
            {['Treino', 'Hotlap', 'Classificação', 'Corrida', 'Desenvolvimento de setup'].map(type => <option key={type}>{type}</option>)}
          </select>
        </div>
        <div className="connection">
          <div><strong>Nenhum setup carregado</strong>
            <p>A importação de ACC/iRacing ainda está em desenvolvimento. Nesta etapa, o engenheiro analisa seu relato e orienta observações, sem alterar valores.</p>
          </div>
        </div>
        {error && <p className="api-error" role="alert">{error}</p>}
        <button className="button button--primary button--start" disabled={busy}>
          {busy ? 'Criando sessão...' : 'Iniciar sessão de engenharia'}
        </button>
      </form>
    </main>
  )
}

export function LiveEngineer({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const end = useRef<HTMLDivElement>(null)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    Promise.all([api.session(sessionId), api.messages(sessionId)]).then(([data, history]) => {
      if (active) { setSession(data); setMessages(history) }
    }).catch(cause => { if (active) setError(cause.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [sessionId, reload])
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [messages, busy])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || busy || !session) return
    setBusy(true)
    setError('')
    try {
      const result = await api.send(sessionId, content)
      if (!mounted.current) return
      setMessages(previous => [...previous, { role: 'user', content }, { role: 'assistant', content: result.engineer_message }])
      setDraft('')
    } catch (cause) {
      if (mounted.current) setError(cause instanceof Error ? cause.message : 'Falha ao enviar.')
    } finally { if (mounted.current) setBusy(false) }
  }

  return (
    <main className="engineering-layout live-layout">
      <div className="chat-pane">
        <header className="session-header"><div>
          <h1>{session?.car ?? 'Carregando sessão...'}</h1>
          <p>{session?.track} · {session?.simulator} · {session?.session_type}</p>
        </div><span className="tag">Sessão local</span></header>
        <div className="chat-scroll">
          <p className="chat-date">Conversa salva neste computador · últimas 100 mensagens</p>
          {!loading && !messages.length && <article className="message">
            <span className="message__author">Início da sessão</span>
            <p>Faça cerca de 5 voltas consistentes e descreva o que sente. Em qual fase da curva o problema aparece e em qual velocidade?</p>
          </article>}
          {messages.map((message, index) => <article key={index}
            className={'message message--' + (message.role === 'user' ? 'driver' : 'engineer')}>
            <span className="message__author">{message.role === 'user' ? 'Piloto' : 'Engenheiro'}</span>
            <p className="live-message">{message.content}</p>
          </article>)}
          {busy && <div className="thinking" role="status"><span><i /><i /><i /></span>Analisando seu relato. A resposta local pode levar alguns minutos...</div>}
          {error && <div className="api-error" role="alert"><p>{error}</p>
            <button className="button button--secondary" disabled={busy} onClick={() => setReload(n => n + 1)}>Recarregar conversa</button>
          </div>}
          <div ref={end} />
        </div>
        <form className="composer live-composer" onSubmit={submit}>
          <textarea aria-label="Feedback do piloto" placeholder="Conte ao engenheiro o que o carro está fazendo..."
            maxLength={1200} rows={2} value={draft} disabled={busy || loading || !session}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} />
          <button className="button button--primary" disabled={busy || loading || !session || !draft.trim()}>
            {busy ? 'Aguarde...' : 'Enviar'}
          </button>
        </form>
      </div>
      <aside className="session-sidebar"><p className="section-label">Contexto da sessão</p>
        <div className="sidebar-section session-context"><div>
          <strong>{session?.simulator}</strong><p>{session?.car}</p><p>{session?.track}</p>
        </div></div>
        <p className="section-label">Setup atual</p>
        <p className="page-description">Não importado</p>
        <p className="form-footnote">Análise de sintomas e planos de observação. Alterações de valores aguardam validação dos parâmetros do simulador.</p>
      </aside>
    </main>
  )
}

