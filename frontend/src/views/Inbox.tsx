import React, { useEffect, useRef, useState } from 'react'
import {
  Check,
  MessageCircle,
  Pause,
  Play,
  Search,
  Send,
  ShieldCheck,
  User,
  Bot,
  UserCheck,
  CheckCheck,
  Clock,
  AlertCircle
} from 'lucide-react'
import { api, post, Course, Lead, Message, stages, sentiments, date } from '../api'
import { Badge } from '../components/Badge'
import { Empty } from '../components/EmptyState'
import { PageHeading } from '../components/PageHeading'

interface InboxProps {
  leads: Lead[]
  courses: Course[]
  selected: number | null
  select: (id: number) => void
  version: number
  report: (e: unknown) => void
  refresh: () => Promise<void>
}

export function Inbox({
  leads,
  courses,
  selected,
  select,
  version,
  report,
  refresh
}: InboxProps) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [messages, setMessages] = useState<Message[]>([])
  const [messagesLeadId, setMessagesLeadId] = useState<number | null>(null)

  const lead = leads.find(l => l.id === selected)

  useEffect(() => {
    if (!selected) return
    let alive = true
    api<Message[]>(`/leads/${selected}/messages`)
      .then(m => {
        if (alive) { setMessages(m); setMessagesLeadId(selected) }
      })
      .catch(report)
    return () => {
      alive = false
    }
  }, [selected, version, report])

  const filtered = leads.filter(l => {
    const courseTitle = courses.find(c => c.id === l.course_id)?.title || ''
    const matchSearch = `${l.name} ${courseTitle}`.toLowerCase().includes(search.toLowerCase())
    const matchFilter =
      filter === 'all' || (filter === 'human' ? l.handoff : l.sentiment === filter)
    return matchSearch && matchFilter
  })

  return (
    <div className="inbox-view">
      <PageHeading
        eyebrow="BANDEJA COMPARTIDA"
        title="Conversaciones"
        description="Escucha, acompaña y toma el control cuando sea necesario."
      />

      <div className="inbox">
        <section className="conversation-list">
          <div className="list-controls">
            <label className="search">
              <Search size={16} />
              <input
                aria-label="Buscar prospecto"
                placeholder="Buscar persona o curso…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </label>
            <select
              aria-label="Filtrar conversaciones"
              value={filter}
              onChange={e => setFilter(e.target.value)}
            >
              <option value="all">Todas las conversaciones</option>
              <option value="human">Requieren atención humana</option>
              {Object.entries(sentiments).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>

          <div className="conversation-items-scroll">
            {filtered.length ? (
              filtered.map(l => (
                <button
                  className={`conversation-item ${l.id === selected ? 'selected' : ''}`}
                  key={l.id}
                  onClick={() => select(l.id)}
                  type="button"
                >
                  <div className="conversation-title">
                    <span className={`avatar ${l.handoff ? 'warm' : ''}`}>
                      {l.name.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="conversation-title-text">
                      <strong>{l.name}</strong>
                      <small>
                        {l.channel === 'simulator' ? 'Simulador' : 'Telegram'} · {date(l.updated_at)}
                      </small>
                    </div>
                    {l.handoff && (
                      <span className="handoff-pause-pill" title="Atención humana activa">
                        <Pause size={13} />
                      </span>
                    )}
                  </div>
                  <p>{l.summary || 'Nueva consulta recibida'}</p>
                  <Badge lead={l} />
                </button>
              ))
            ) : (
              <Empty
                title="Sin conversaciones"
                text="Las nuevas consultas aparecerán aquí en cuanto lleguen."
              />
            )}
          </div>
        </section>

        {lead ? (
          <LeadConversation
            key={lead.id}
            lead={lead}
            courses={courses}
            messages={messagesLeadId===lead.id ? messages : []}
            report={report}
            refresh={refresh}
          />
        ) : (
          <div className="conversation-placeholder">
            <div className="placeholder-icon-wrap">
              <MessageCircle size={40} />
            </div>
            <h2>Todo empieza por escuchar</h2>
            <p>Selecciona una conversación del listado para ver su historia y acompañar al prospecto.</p>
          </div>
        )}
      </div>
    </div>
  )
}

function LeadConversation({
  lead,
  courses,
  messages,
  report,
  refresh
}: {
  lead: Lead
  courses: Course[]
  messages: Message[]
  report: (e: unknown) => void
  refresh: () => Promise<void>
}) {
  const [draft, setDraft] = useState({
    stage: lead.stage,
    owner: lead.owner,
    notes: lead.notes,
    next_action: lead.next_action
  })
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!dirty) {
      setDraft({
        stage: lead.stage,
        owner: lead.owner,
        notes: lead.notes,
        next_action: lead.next_action
      })
    }
  }, [lead.stage, lead.owner, lead.notes, lead.next_action, dirty])

  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const container = end.current?.parentElement
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  }, [messages])

  const patch = async (handoff: boolean, values = draft, saveDraft = true) => {
    setBusy(true)
    try {
      await api(`/leads/${lead.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ ...values, handoff })
      })
      if (saveDraft) setDirty(false)
      await refresh()
    } catch (e) {
      report(e)
    } finally {
      setBusy(false)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    try {
      const result = await api<Message>(`/leads/${lead.id}/reply`, post({ text }))
      if (result.delivery === 'failed') {
        report(
          Error(
            'El mensaje quedó guardado pero no se entregó. Revisa Telegram antes de reenviar.'
          )
        )
      }
      setText('')
      await refresh()
    } catch (e) {
      report(e)
    } finally {
      setBusy(false)
    }
  }

  const deliveryLabels: Record<string, string> = {
    delivered: 'Entregado',
    saved: 'Guardado',
    failed: 'Falló la entrega',
    pending: 'Pendiente',
    handoff_pending: 'Pendiente',
    cancelled: 'Cancelado'
  }

  return (
    <>
      <section className="chat">
        <div className="chat-header">
          <div className="chat-header-info">
            <div className="chat-header-title">
              <strong>{lead.name}</strong>
              <span className={`channel-pill ${lead.channel}`}>
                {lead.channel === 'simulator' ? 'Simulador' : 'Telegram'}
              </span>
            </div>
            <small>
              Estado de atención:{' '}
              <strong className={lead.handoff ? 'status-human' : 'status-bot'}>
                {lead.handoff ? 'Atención humana (IA en pausa)' : 'Asistente activo'}
              </strong>
            </small>
          </div>

          <button
            className={lead.handoff ? 'secondary btn-handover' : 'primary btn-handover'}
            disabled={busy}
            onClick={() => void patch(!lead.handoff, {stage:lead.stage,owner:lead.owner,notes:lead.notes,next_action:lead.next_action}, false)}
            type="button"
          >
            {lead.handoff ? <Play size={15} /> : <Pause size={15} />}
            <span>{lead.handoff ? 'Reanudar IA' : 'Tomar control'}</span>
          </button>
        </div>

        <div className="chat-messages">
          {messages.map(m => {
            const roleClass = m.role // 'user' | 'assistant' | 'advisor'
            const roleLabel =
              m.role === 'user'
                ? lead.name
                : m.role === 'advisor'
                ? 'Asesor de admisiones'
                : 'Asistente CTT'
            const deliveryText =
              m.role !== 'user'
                ? ` · ${deliveryLabels[m.delivery] || m.delivery}`
                : ''

            return (
              <div className={`message ${roleClass}`} key={m.id}>
                <div className="message-header">
                  <span className="message-role-icon">
                    {m.role === 'user' ? (
                      <User size={13} />
                    ) : m.role === 'advisor' ? (
                      <UserCheck size={13} />
                    ) : (
                      <Bot size={13} />
                    )}
                  </span>
                  <span className="message-label">{roleLabel}</span>
                </div>
                <p>{m.text}</p>
                <small className="message-meta">
                  <Clock size={11} />
                  <span>
                    {date(m.created_at)}
                    {deliveryText}
                  </span>
                </small>
              </div>
            )
          })}
          <div ref={end} />
        </div>

        <form className="composer" onSubmit={handleSendMessage}>
          <label className="sr-only" htmlFor="advisor-reply">
            Respuesta del asesor
          </label>
          <textarea
            id="advisor-reply"
            maxLength={4000}
            placeholder="Escribe como asesor. Al enviar, la IA se pausa automáticamente…"
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <button
            className="primary icon-button"
            disabled={busy || !text.trim()}
            aria-label="Enviar respuesta"
            type="submit"
          >
            <Send size={17} />
          </button>
        </form>

        <div className="composer-note">
          <ShieldCheck size={13} />
          <span>Los mensajes se envían bajo la misma identidad del bot.</span>
        </div>
      </section>

      <aside className="lead-details">
        <div className="lead-details-header">
          <Badge lead={lead} />
          <p className="subtle">{lead.sentiment_reason}</p>
        </div>

        <div className="lead-section">
          <h3>Contexto para el asesor</h3>
          <p className="briefing">
            {lead.summary || 'El resumen aparecerá después de la primera consulta.'}
          </p>

          <label>
            Curso de interés
            <div className="field-readonly">
              {courses.find(c => c.id === lead.course_id)?.title || 'Por definir'}
            </div>
          </label>

          {Object.entries(lead.profile || {}).map(([k, v]) => (
            <div className="profile-entry" key={k}>
              <span className="profile-key">{k}</span>
              <p className="profile-val">{v}</p>
            </div>
          ))}
        </div>

        <div className="lead-section">
          <h3>Seguimiento comercial</h3>

          <label>
            Etapa
            <select
              value={draft.stage}
              onChange={e => {
                setDirty(true)
                setDraft({ ...draft, stage: e.target.value })
              }}
            >
              {Object.entries(stages).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>

          <label>
            Asesor responsable
            <input
              maxLength={150}
              value={draft.owner}
              onChange={e => {
                setDirty(true)
                setDraft({ ...draft, owner: e.target.value })
              }}
              placeholder="Asignar responsable"
            />
          </label>

          <label>
            Próxima acción
            <input
              maxLength={500}
              value={draft.next_action}
              onChange={e => {
                setDirty(true)
                setDraft({ ...draft, next_action: e.target.value })
              }}
              placeholder="¿Qué sigue?"
            />
          </label>

          <label>
            Notas internas
            <textarea
              value={draft.notes}
              maxLength={10000}
              onChange={e => {
                setDirty(true)
                setDraft({ ...draft, notes: e.target.value })
              }}
              placeholder="Contexto para tu equipo"
            />
          </label>

          <button
            className="primary full"
            disabled={busy}
            onClick={() => void patch(lead.handoff, draft)}
            type="button"
          >
            <Check size={16} />
            <span>Guardar seguimiento</span>
          </button>
        </div>
      </aside>
    </>
  )
}

