import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { LiveEngineer, LiveSessionForm } from './LiveEngineer'

type Page = 'home' | 'new-session' | 'engineer' | 'demo-engineer' | 'setup' | 'history' | 'compare'
type IconName =
  | 'home'
  | 'plus'
  | 'layers'
  | 'sliders'
  | 'settings'
  | 'car'
  | 'arrow'
  | 'mic'
  | 'clip'
  | 'send'
  | 'chevron'
  | 'check'
  | 'warning'
  | 'spark'
  | 'refresh'
  | 'close'
  | 'compare'
  | 'upload'
  | 'more'

type Message = {
  id: number
  role: 'engineer' | 'driver'
  content: string
}

const sessions = [
  {
    car: 'Porsche 992 GT3 R',
    track: 'Nürburgring Nordschleife',
    simulator: 'Assetto Corsa Competizione',
    version: 'Setup V4',
    date: 'Hoje, 15:42',
    accent: true,
  },
  {
    car: 'Ferrari 296 GT3',
    track: 'Spa-Francorchamps',
    simulator: 'Assetto Corsa Competizione',
    version: 'Setup V2',
    date: 'Ontem, 10:15',
    accent: false,
  },
  {
    car: 'BMW M4 GT3',
    track: 'Monza',
    simulator: 'iRacing',
    version: 'Setup V1',
    date: 'Há 3 dias',
    accent: false,
  },
]

const setupGroups = [
  {
    title: 'Pneus',
    fields: [
      ['Pressão dianteira', '27.4 psi'],
      ['Pressão traseira', '27.1 psi'],
      ['Cambagem dianteira', '-3.6°'],
      ['Toe traseiro', '0.12°'],
    ],
  },
  {
    title: 'Eletrônica',
    fields: [
      ['Traction control', '4'],
      ['ABS', '3'],
      ['ECU Map', '1'],
      ['Preload', '80 Nm'],
    ],
  },
  {
    title: 'Aderência mecânica',
    fields: [
      ['ARB dianteira', '5'],
      ['ARB traseira', '3'],
      ['Wheel rate dianteiro', '145000 N/m'],
      ['Wheel rate traseiro', '155000 N/m'],
    ],
  },
  {
    title: 'Aerodinâmica',
    fields: [
      ['Asa traseira', '9'],
      ['Altura dianteira', '56 mm'],
      ['Altura traseira', '71 mm'],
      ['Brake ducts', '3 / 3'],
    ],
  },
]

const initialMessages: Message[] = [
  {
    id: 1,
    role: 'engineer',
    content:
      'Setup carregado com sucesso. Antes de alterarmos qualquer coisa, faça cerca de 5 voltas consistentes. Foque em entender o carro, não em buscar a volta perfeita.',
  },
  {
    id: 2,
    role: 'engineer',
    content:
      'Depois, me conte onde o problema acontece: entrada, meio ou saída da curva; baixa, média ou alta velocidade; frenagem, tração, estabilidade ou zebras.',
  },
  {
    id: 3,
    role: 'driver',
    content:
      'A traseira parece instável nas curvas rápidas, especialmente quando faço pequenas correções no volante.',
  },
]

const navItems: { page: Page; label: string; icon: IconName }[] = [
  { page: 'home', label: 'Início', icon: 'home' },
  { page: 'new-session', label: 'Nova sessão', icon: 'plus' },
  { page: 'history', label: 'Sessões', icon: 'layers' },
  { page: 'setup', label: 'Setups', icon: 'sliders' },
]

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, string> = {
    home: 'M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5h-5v-6h-5v6h-5A1.5 1.5 0 0 1 3 19.5z',
    plus: 'M12 5v14M5 12h14',
    layers: 'm12 3 8 4.5-8 4.5-8-4.5L12 3Zm-8 9 8 4.5 8-4.5M4 16.5 12 21l8-4.5',
    sliders: 'M4 6h16M8 12h12M4 18h16M7 4v4m9 2v4m-5 2v4',
    settings: 'M12 15.25A3.25 3.25 0 1 0 12 8.75a3.25 3.25 0 0 0 0 6.5ZM19.4 15a1.72 1.72 0 0 0 .34 1.9l.06.06-2.1 2.1-.06-.06a1.72 1.72 0 0 0-1.9-.34 1.72 1.72 0 0 0-1.04 1.58v.08h-3v-.08A1.72 1.72 0 0 0 10.66 18.66a1.72 1.72 0 0 0-1.9.34l-.06.06-2.1-2.1.06-.06A1.72 1.72 0 0 0 7 15a1.72 1.72 0 0 0-1.58-1.04h-.08v-3h.08A1.72 1.72 0 0 0 7 9.92a1.72 1.72 0 0 0-.34-1.9L6.6 7.96l2.1-2.1.06.06a1.72 1.72 0 0 0 1.9.34 1.72 1.72 0 0 0 1.04-1.58V4.6h3v.08a1.72 1.72 0 0 0 1.04 1.58 1.72 1.72 0 0 0 1.9-.34l.06-.06 2.1 2.1-.06.06a1.72 1.72 0 0 0-.34 1.9 1.72 1.72 0 0 0 1.58 1.04h.08v3h-.08A1.72 1.72 0 0 0 19.4 15Z',
    car: 'M5 16.5h14l-1.15-5.1A2.5 2.5 0 0 0 15.4 9.5H8.6a2.5 2.5 0 0 0-2.45 1.9L5 16.5ZM4 16.5h16v2.25A1.25 1.25 0 0 1 18.75 20H5.25A1.25 1.25 0 0 1 4 18.75V16.5Zm3-3.5h.01M17 13h.01',
    arrow: 'M5 12h14m-6-6 6 6-6 6',
    mic: 'M12 14.5a3 3 0 0 0 3-3v-5a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3ZM5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-3 0h6',
    clip: 'm20.5 11.5-8.3 8.3a4 4 0 0 1-5.7-5.7l8.3-8.3a2.75 2.75 0 0 1 3.9 3.9l-8.3 8.3a1.5 1.5 0 0 1-2.1-2.1l7.65-7.65',
    send: 'm21 3-7.2 18-3.55-7.25L3 10.2 21 3Zm-10.7 10.75L15 9',
    chevron: 'm9 18 6-6-6-6',
    check: 'm5 12 4.2 4.2L19 6.5',
    warning: 'M12 3 2.8 19a1.3 1.3 0 0 0 1.12 2h16.16A1.3 1.3 0 0 0 21.2 19L12 3Zm0 6v5m0 3h.01',
    spark: 'm12 2 1.65 6.35L20 10l-6.35 1.65L12 18l-1.65-6.35L4 10l6.35-1.65L12 2Zm7 14 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z',
    refresh: 'M20 11a8.1 8.1 0 0 0-15.15-3L3 11m-1-4v4h4m-2 2a8.1 8.1 0 0 0 15.15 3L21 13m1 4v-4h-4',
    close: 'm6 6 12 12M18 6 6 18',
    compare: 'M8 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3m8-16h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3M9 8h6M9 12h6m-6 4h6',
    upload: 'M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5',
    more: 'M5 12h.01M12 12h.01M19 12h.01',
  }

  return (
    <svg
      aria-hidden="true"
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  )
}

function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action}
    </div>
  )
}

function Recommendation({
  applied,
  onApply,
}: {
  applied: boolean
  onApply: () => void
}) {
  return (
    <section className={`recommendation ${applied ? 'recommendation--applied' : ''}`}>
      <div className="recommendation__heading">
        <div className="recommendation__badge"><Icon name={applied ? 'check' : 'spark'} size={15} /></div>
        <div>
          <p className="eyebrow">Recomendação do engenheiro</p>
          <h3>{applied ? 'Alterações aplicadas ao Setup V4' : 'Estabilidade traseira em alta'}</h3>
        </div>
        <span className="confidence">{applied ? 'Aplicado' : 'Confiança alta'}</span>
      </div>

      <div className="recommendation__body">
        <div className="recommendation__section">
          <span>Diagnóstico</span>
          <p>
            A perda de confiança parece ocorrer em pequenas correções a alta velocidade.
            Vamos aumentar a estabilidade aerodinâmica traseira sem alterar de forma
            significativa o equilíbrio mecânico.
          </p>
        </div>

        <div className="recommendation__section">
          <span>Alterações recomendadas</span>
          <div className="changes">
            <Change parameter="Asa traseira" before="8" after="9" />
            <Change parameter="Altura traseira" before="70 mm" after="71 mm" />
            <Change parameter="Toe traseiro" before="0.10°" after="0.12°" />
          </div>
        </div>

        <div className="recommendation__columns">
          <div className="recommendation__section">
            <span>Por quê</span>
            <p>Mais apoio traseiro torna o carro mais previsível nas curvas rápidas e nas mudanças de direção.</p>
          </div>
          <div className="recommendation__section">
            <span>Plano de teste</span>
            <p><strong>5 voltas</strong><br />Observe Schwedenkreuz, mudanças rápidas de direção e velocidade final.</p>
          </div>
        </div>

        <div className="tradeoff">
          <Icon name="warning" size={16} />
          <p>A asa extra aumenta o arrasto e pode reduzir levemente a velocidade na Döttinger Höhe.</p>
        </div>
      </div>

      {!applied && (
        <div className="recommendation__actions">
          <button className="button button--primary" onClick={onApply}>
            <Icon name="check" size={16} /> Aplicar alterações
          </button>
          <button className="button button--secondary">Manter setup atual</button>
        </div>
      )}
    </section>
  )
}

function Change({ parameter, before, after }: { parameter: string; before: string; after: string }) {
  return (
    <div className="change-row">
      <span>{parameter}</span>
      <div><b>{before}</b><Icon name="arrow" size={14} /><strong>{after}</strong></div>
    </div>
  )
}

function SessionSidebar({
  version,
  setPage,
}: {
  version: string
  setPage: (page: Page) => void
}) {
  return (
    <aside className="session-sidebar">
      <div className="sidebar-section">
        <p className="section-label">Sessão</p>
        <div className="session-context">
          <span className="sim-chip">ACC</span>
          <div>
            <strong>Nürburgring Nordschleife</strong>
            <p>Porsche 992 GT3 R</p>
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-heading">
          <p className="section-label">Setup atual</p>
          <button className="icon-button" aria-label="Mais opções"><Icon name="more" size={17} /></button>
        </div>
        <button className="setup-version" onClick={() => setPage('setup')}>
          <span>{version}</span>
          <Icon name="chevron" size={15} />
        </button>
        <button className="text-button" onClick={() => setPage('setup')}>Ver setup</button>
      </div>

      <div className="sidebar-section">
        <div className="section-heading">
          <p className="section-label">Alterações de setup</p>
          <button className="text-button" onClick={() => setPage('history')}>Ver tudo</button>
        </div>
        <ol className="version-list">
          <li><span>V1</span><p>Setup de base</p></li>
          <li><span>V2</span><p>Asa traseira +1</p></li>
          <li><span>V3</span><p>ARB traseira -1<br />Toe traseiro +0.02</p></li>
        </ol>
        <button className="button button--secondary button--full" onClick={() => setPage('compare')}>
          <Icon name="compare" size={15} /> Comparar versões
        </button>
      </div>
    </aside>
  )
}

function Home({
  setPage,
  connected,
  toggleConnection,
}: {
  setPage: (page: Page) => void
  connected: boolean
  toggleConnection: () => void
}) {
  return (
    <main className="content content--home">
      <PageTitle
        eyebrow="Virtual Race Engineer"
        title="Bem-vindo de volta"
        description="Construa, teste e refine seu setup com seu engenheiro virtual."
        action={
          <button className="button button--primary button--new" onClick={() => setPage('new-session')}>
            <Icon name="plus" size={17} /> Nova sessão
          </button>
        }
      />

      <section className="home-section">
        <p className="section-label">Exemplos de sessões · demonstração visual</p>
        <div className="sessions-card">
          {sessions.map((session) => (
            <button className="session-row" key={session.car} onClick={() => setPage('demo-engineer')}>
              <span className="car-icon"><Icon name="car" size={18} /></span>
              <span className="session-row__details">
                <strong>{session.car}</strong>
                <span>{session.track}<i />{session.simulator}</span>
              </span>
              <span className="session-row__meta">
                <b className={session.accent ? 'tag tag--accent' : 'tag'}>{session.version}</b>
                <small>{session.date}</small>
              </span>
              <span className="continue">Continuar</span>
            </button>
          ))}
        </div>
      </section>

      <section className={`connection ${connected ? 'connection--ready' : ''}`}>
        <div className="connection__icon"><Icon name={connected ? 'check' : 'warning'} size={18} /></div>
        <div>
          <strong>{connected ? 'IA local conectada' : 'A IA local não está em execução'}</strong>
          <p>{connected ? 'Ollama está pronto para iniciar uma sessão.' : 'Inicie o Ollama para continuar.'}</p>
        </div>
        <button className="button button--secondary" onClick={toggleConnection}>
          <Icon name={connected ? 'refresh' : 'refresh'} size={15} />
          {connected ? 'Verificar conexão' : 'Tentar novamente'}
        </button>
      </section>
    </main>
  )
}

function NewSession({ setPage }: { setPage: (page: Page) => void }) {
  const [type, setType] = useState('Desenvolvimento de setup')
  const [setupName, setSetupName] = useState<string | null>(null)
  const [simulator, setSimulator] = useState('Assetto Corsa Competizione')

  return (
    <main className="content content--form">
      <PageTitle
        eyebrow="Criar sessão"
        title="Nova sessão"
        description="Conte ao seu engenheiro o que você vai pilotar hoje."
      />

      <section className="session-form">
        <div className="form-grid">
          <Field label="Simulador">
            <select value={simulator} onChange={(event) => setSimulator(event.target.value)}>
              <option>Assetto Corsa Competizione</option>
              <option>iRacing</option>
            </select>
          </Field>
          <Field label="Carro">
            <select>
              <option>Porsche 992 GT3 R</option>
              <option>Ferrari 296 GT3</option>
              <option>BMW M4 GT3</option>
            </select>
          </Field>
          <Field label="Pista">
            <select>
              <option>Nürburgring Nordschleife</option>
              <option>Spa-Francorchamps</option>
              <option>Monza</option>
            </select>
          </Field>
        </div>

        <div className="form-block">
          <label>Tipo de sessão</label>
          <div className="session-types">
            {['Treino', 'Hotlap', 'Classificação', 'Corrida', 'Desenvolvimento de setup'].map((item) => (
              <button
                key={item}
                className={`session-type ${type === item ? 'session-type--selected' : ''}`}
                onClick={() => setType(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="form-block">
          <div className="upload-heading">
            <label>Setup atual</label>
            <span>Opcional, mas recomendado</span>
          </div>
          <label className={`upload-zone ${setupName ? 'upload-zone--loaded' : ''}`}>
            <input
              type="file"
              accept=".json,.sto,.ini"
              onChange={(event) => setSetupName(event.target.files?.[0]?.name ?? null)}
            />
            <span className="upload-zone__icon"><Icon name={setupName ? 'check' : 'upload'} size={22} /></span>
            <strong>{setupName ? 'Setup carregado' : 'Solte seu arquivo de setup aqui'}</strong>
            <p>{setupName ?? 'ou procure arquivos de setup'}</p>
            {!setupName && <small>Formatos compatíveis: .json, .sto, .ini</small>}
          </label>
          {setupName && <button className="text-button text-button--standalone">Ver setup importado</button>}
        </div>

        <button className="button button--primary button--start" onClick={() => setPage('engineer')}>
          Iniciar sessão de engenharia <Icon name="arrow" size={17} />
        </button>
      </section>

      <p className="form-footnote">
        {simulator} · O setup original será preservado como a primeira versão da sessão.
      </p>
    </main>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="field"><label>{label}</label>{children}</div>
}

function Engineer({
  setPage,
  applied,
  onApply,
}: {
  setPage: (page: Page) => void
  applied: boolean
  onApply: () => void
}) {
  const [messages, setMessages] = useState(initialMessages)
  const [message, setMessage] = useState('')
  const [thinking, setThinking] = useState(false)
  const [listening, setListening] = useState(false)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!message.trim()) return
    setMessages((current) => [...current, { id: Date.now(), role: 'driver', content: message.trim() }])
    setMessage('')
    setThinking(true)
    window.setTimeout(() => {
      setThinking(false)
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: 'engineer',
          content: 'Entendi. Esse comportamento confirma que devemos começar pela estabilidade aerodinâmica traseira e preservar a aderência mecânica em baixa velocidade.',
        },
      ])
    }, 800)
  }

  return (
    <main className="engineering-layout">
      <div className="chat-pane">
        <header className="session-header">
          <div>
            <h1>Porsche 992 GT3 R</h1>
            <p>Nürburgring Nordschleife <i /> ACC <i /> Desenvolvimento de setup</p>
          </div>
          <span className="tag tag--accent">{applied ? 'Setup V4' : 'Setup V3'}</span>
        </header>

        <div className="chat-scroll">
          <div className="chat-date">Sessão de hoje</div>
          {messages.map((item) => (
            <article className={`message message--${item.role}`} key={item.id}>
              <span className="message__author">{item.role === 'engineer' ? 'Engenheiro' : 'Piloto'}</span>
              <p>{item.content}</p>
            </article>
          ))}
          <Recommendation applied={applied} onApply={onApply} />
          {thinking && (
            <div className="thinking">
              <span><i /><i /><i /></span>
              Analisando setup, características da pista e feedback do piloto...
            </div>
          )}
        </div>

        <form className="composer" onSubmit={submit}>
          <button
            type="button"
            className={`composer-icon ${listening ? 'composer-icon--listening' : ''}`}
            onClick={() => setListening((current) => !current)}
            aria-label="Gravar mensagem"
          >
            <Icon name="mic" size={19} />
          </button>
          <button type="button" className="composer-icon" aria-label="Anexar arquivo">
            <Icon name="clip" size={19} />
          </button>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={listening ? 'Ouvindo...' : 'Conte ao seu engenheiro o que o carro está fazendo...'}
            rows={1}
          />
          <button className="send-button" aria-label="Enviar mensagem"><Icon name="send" size={18} /></button>
          {listening && <span className="listening-status">Ouvindo<span className="wave"><i /><i /><i /><i /></span></span>}
        </form>
      </div>
      <SessionSidebar version={applied ? 'V4' : 'V3'} setPage={setPage} />
    </main>
  )
}

function SetupPage({ setPage, applied }: { setPage: (page: Page) => void; applied: boolean }) {
  return (
    <main className="content content--setup">
      <PageTitle
        eyebrow="Setup atual"
        title={`Porsche 992 GT3 R — ${applied ? 'V4' : 'V3'}`}
        description="Valores atuais importados e alterações da última recomendação."
        action={<button className="button button--secondary" onClick={() => setPage('compare')}><Icon name="compare" size={16} /> Comparar versões</button>}
      />

      <div className="setup-grid">
        {setupGroups.map((group) => (
          <section className="setup-card" key={group.title}>
            <h2>{group.title}</h2>
            <div>
              {group.fields.map(([label, value]) => {
                const changed = (label === 'Asa traseira' || label === 'Altura traseira' || label === 'Toe traseiro') && applied
                return (
                  <div className="setup-field" key={label}>
                    <span>{label}</span>
                    {changed ? <b className="value-change">{label === 'Asa traseira' ? '8 → 9' : label === 'Altura traseira' ? '70 → 71 mm' : '0.10 → 0.12°'}</b> : <strong>{value}</strong>}
                  </div>
                )
              })}
            </div>
          </section>
        ))}
      </div>
      <div className="setup-footer">
        <button className="button button--secondary" onClick={() => setPage('history')}>Ver histórico de versões</button>
        <button className="button button--primary" onClick={() => setPage('engineer')}>Voltar ao engenheiro <Icon name="arrow" size={16} /></button>
      </div>
    </main>
  )
}

function History({ setPage, applied }: { setPage: (page: Page) => void; applied: boolean }) {
  const versions = useMemo(() => [
    { name: 'V1', title: 'Setup de base', note: 'Setup importado', feedback: null },
    { name: 'V2', title: 'Asa traseira  +1', note: 'Primeiro ajuste de estabilidade em alta', feedback: 'A traseira ficou mais previsível no setor rápido.' },
    { name: 'V3', title: 'ARB traseira e toe', note: 'ARB traseira 4 → 3 · Toe traseiro 0.10 → 0.12', feedback: 'A tração melhorou, mas o carro gira menos na entrada.' },
    ...(applied ? [{ name: 'V4', title: 'Estabilidade traseira em alta', note: 'Asa traseira 8 → 9 · Altura traseira 70 → 71 mm', feedback: 'Aguardando as voltas de teste.' }] : []),
  ], [applied])

  return (
    <main className="content content--history">
      <PageTitle
        eyebrow="Evolução da sessão"
        title="Histórico de setups"
        description="Cada versão mantém as alterações e o feedback que motivaram o próximo teste."
        action={<button className="button button--secondary" onClick={() => setPage('compare')}><Icon name="compare" size={16} /> Comparar setups</button>}
      />
      <section className="timeline">
        {versions.map((version, index) => (
          <article className={`timeline-item ${index === versions.length - 1 ? 'timeline-item--current' : ''}`} key={version.name}>
            <div className="timeline-marker"><span>{version.name}</span></div>
            <div className="timeline-content">
              <div><p className="eyebrow">{index === versions.length - 1 ? 'Versão atual' : 'Versão anterior'}</p><h2>{version.title}</h2></div>
              <p>{version.note}</p>
              {version.feedback && <blockquote>“{version.feedback}”</blockquote>}
              {index !== versions.length - 1 && <button className="text-button">Restaurar esta versão</button>}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}

function Compare({ setPage, applied }: { setPage: (page: Page) => void; applied: boolean }) {
  const [changedOnly, setChangedOnly] = useState(true)
  const comparison = [
    ['Asa traseira', '8', applied ? '9' : '8', applied ? '+1' : '—'],
    ['ARB traseira', '4', '3', '-1'],
    ['Toe traseiro', '0.10°', '0.12°', '+0.02°'],
    ['Altura traseira', '70 mm', applied ? '71 mm' : '70 mm', applied ? '+1 mm' : '—'],
    ['ABS', '3', '3', '—'],
  ]
  const rows = changedOnly ? comparison.filter((row) => row[3] !== '—') : comparison

  return (
    <main className="content content--compare">
      <PageTitle
        eyebrow="Análise de versões"
        title="Comparar setups"
        description="Porsche 992 GT3 R · Nürburgring Nordschleife"
        action={<button className="button button--secondary" onClick={() => setPage('history')}>Ver histórico</button>}
      />
      <section className="comparison-card">
        <div className="comparison-top">
          <div className="compare-selector"><span>Setup base</span><button>V2 <Icon name="chevron" size={15} /></button></div>
          <div className="vs">vs</div>
          <div className="compare-selector"><span>Setup atual</span><button>{applied ? 'V4' : 'V3'} <Icon name="chevron" size={15} /></button></div>
          <label className="toggle"><input type="checkbox" checked={changedOnly} onChange={() => setChangedOnly((value) => !value)} /><span /> Mostrar somente alterados</label>
        </div>
        <div className="comparison-table">
          <div className="comparison-table__row comparison-table__head"><span>Parâmetro</span><span>V2</span><span>{applied ? 'V4' : 'V3'}</span><span>Alteração</span></div>
          {rows.map((row) => <div className="comparison-table__row" key={row[0]}><strong>{row[0]}</strong><span>{row[1]}</span><span>{row[2]}</span><b className={row[3] === '—' ? '' : 'delta'}>{row[3]}</b></div>)}
        </div>
      </section>
      <button className="button button--primary" onClick={() => setPage('engineer')}>Continuar com o engenheiro <Icon name="arrow" size={16} /></button>
    </main>
  )
}

export default function App() {
  const [page, setPage] = useState<Page>('home')
  const [connected, setConnected] = useState(false)
  const [applied, setApplied] = useState(false)
  const [connectionDetail, setConnectionDetail] = useState('Verificando IA local...')
  const [sessionId, setSessionId] = useState<string | null>(() => {
    try { return localStorage.getItem('vre.sessionId') } catch { return null }
  })
  async function checkConnection() {
    setConnectionDetail('Verificando IA local...')
    try {
      const health = await api.health()
      setConnected(health.available)
      setConnectionDetail(health.detail)
    } catch (cause) {
      setConnected(false)
      setConnectionDetail(cause instanceof Error ? cause.message : 'Falha de conexão.')
    }
  }
  useEffect(() => { void checkConnection() }, [])
  function created(id: string) {
    setSessionId(id)
    try { localStorage.setItem('vre.sessionId', id) } catch { /* Sessão continua em memória. */ }
    setPage('engineer')
  }

  const content = () => {
    if (page === 'home') return <><Home setPage={setPage} connected={connected} toggleConnection={() => void checkConnection()} />
      <div className="live-home-actions"><p role="status">{connectionDetail}</p>
        {sessionId && <button className="button button--primary" onClick={() => setPage('engineer')}>Retomar minha sessão local</button>}
      </div></>
    if (page === 'new-session') return <LiveSessionForm onCreated={created} />
    if (page === 'engineer') return sessionId ? <LiveEngineer key={sessionId} sessionId={sessionId} /> : <LiveSessionForm onCreated={created} />
    if (page === 'demo-engineer') return <Engineer setPage={setPage} applied={applied} onApply={() => setApplied(true)} />
    if (page === 'setup') return <SetupPage setPage={setPage} applied={applied} />
    if (page === 'history') return <History setPage={setPage} applied={applied} />
    return <Compare setPage={setPage} applied={applied} />
  }

  return (
    <div className="app-shell">
      <aside className="app-rail">
        <button className="brand" onClick={() => setPage('home')} aria-label="Virtual Race Engineer">
          <svg viewBox="0 0 28 28" aria-hidden="true"><path d="M6 19.5 10.1 7l3.9 6.2L17.9 7 22 19.5H6Z" /></svg>
        </button>
        <nav>
          {navItems.map((item) => (
            <button
              className={`rail-button ${page === item.page ? 'rail-button--active' : ''}`}
              onClick={() => setPage(item.page)}
              key={item.page}
              aria-label={item.label}
              title={item.label}
            >
              <Icon name={item.icon} size={19} />
            </button>
          ))}
        </nav>
        <div className="rail-bottom">
          <button className="rail-button" aria-label="Aparência"><Icon name="spark" size={18} /></button>
          <button className="rail-button" aria-label="Configurações"><Icon name="settings" size={18} /></button>
        </div>
      </aside>
      <div className="app-main">
        {['demo-engineer', 'setup', 'history', 'compare'].includes(page) && <div className="demo-notice">Demonstração visual com dados fictícios. Para usar a IA local, crie uma nova sessão.</div>}
        {content()}
      </div>
      <button className="help-button">?</button>
    </div>
  )
}
