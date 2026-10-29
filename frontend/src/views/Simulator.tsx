import React, { useEffect, useState } from 'react'
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  User,
  Clock,
  Sparkle,
  Radio
} from 'lucide-react'
import { api, post, Course, Lead, Message, Status, date, providerState } from '../api'
import { PageHeading } from '../components/PageHeading'

interface SimulatorProps {
  report: (e: unknown) => void
  refresh: () => Promise<void>
  openLead: (id: number) => void
  status: Status
  version: number
}

export function Simulator({
  report,
  refresh,
  openLead,
  status,
  version
}: SimulatorProps) {
  const [session, setSession] = useState(
    () => sessionStorage.getItem('ctt_simulator') || crypto.randomUUID()
  )
  const [name, setName] = useState('Visitante de prueba')
  const [text, setText] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [leadId, setLeadId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState('')
  const ai=providerState(status)

  useEffect(() => {
    sessionStorage.setItem('ctt_simulator', session)
  }, [session])

  useEffect(() => {
    let alive = true
    api<Lead[]>('/leads')
      .then(async leads => {
        const lead = leads.find(
          l => (l as Lead & { external_id: string }).external_id === session && l.channel === 'simulator'
        )
        if (lead) {
          const m = await api<Message[]>(`/leads/${lead.id}/messages`)
          if (alive) {
            setLeadId(lead.id)
            setMessages(m)
          }
        }
      })
      .catch(report)
    return () => {
      alive = false
    }
  }, [session, version, report])

  const send = async (value: string) => {
    if (!value.trim()) return
    setBusy(true)
    try {
      const r = await api<{ lead_id: number; mode: string }>(
        '/simulator/messages',
        post({
          external_id: session,
          message_id: crypto.randomUUID(),
          name: name.trim() || 'Visitante de prueba',
          text: value
        })
      )
      setLeadId(r.lead_id)
      setMode(r.mode)
      setText('')
      const updatedMessages = await api<Message[]>(`/leads/${r.lead_id}/messages`)
      setMessages(updatedMessages)
      await refresh()
    } catch (e) {
      report(e)
    } finally {
      setBusy(false)
    }
  }

  const handleResetSession = () => {
    setSession(crypto.randomUUID())
    setLeadId(null)
    setMessages([])
    setMode('')
  }

  const suggestions = [
    'Quiero aprender Python desde cero',
    '¿Qué cursos tienen?',
    'Me interesa GitHub, pero tengo poco tiempo'
  ]

  const modeDescriptions: Record<string, string> = {
    llm: 'IA conversacional con herramientas',
    human: 'Atención humana (IA pausada)',
    fallback: 'Catálogo de respaldo',
    rules: 'Catálogo / reglas automáticas',
    catalog: 'Catálogo verificado',
    scope: 'Límite de alcance',
    clarification: 'Aclaración del curso',
    policy: 'Política de atención',
    cached: 'Mensaje ya procesado'
  }

  return (
    <div className="simulator-view">
      <PageHeading
        eyebrow="PRUEBA EL RECORRIDO COMPLETO"
        title="Una conversación de prueba"
        description="El mismo motor de atención que usa Telegram, directamente aquí."
      >
        <button className="secondary" onClick={handleResetSession} type="button" disabled={busy}>
          <Plus size={16} />
          <span>Nueva conversación</span>
        </button>
      </PageHeading>

      <div className="simulator-layout">
        <section className="panel simulator-chat">
          <div className="chat-header">
            <div className="bot-heading">
              <span className="brand-mark bot-avatar-mark">
                <Bot size={20} />
              </span>
              <div>
                <strong>Asistente CTT-FISEI</strong>
                <small>
                  {ai.detail}
                </small>
              </div>
            </div>
            <span className="badge interesado">
              <span className="dot" />
              <span>Prueba</span>
            </span>
          </div>

          <div className="chat-messages">
            {messages.length ? (
              messages.map(m => {
                const roleClass = m.role
                const roleLabel =
                  m.role === 'user' ? name : m.role === 'advisor' ? 'Asesor' : 'Asistente CTT'
                return (
                  <div className={`message ${roleClass}`} key={m.id}>
                    <span className="message-label">{roleLabel}</span>
                    <p>{m.text}</p>
                    <small className="message-meta">
                      <Clock size={11} />
                      <span>{date(m.created_at)}</span>
                    </small>
                  </div>
                )
              })
            ) : (
              <div className="sim-welcome">
                <span className="assistant-icon">
                  <Sparkles size={26} />
                </span>
                <h2>Encuentra tu próximo paso.</h2>
                <p>
                  Pregunta por los cursos, comparte una duda o prueba la derivación a un asesor.
                </p>
                <div className="sim-suggestions-grid">
                  {suggestions.map(s => (
                    <button
                      key={s}
                      onClick={() => void send(s)}
                      disabled={busy}
                      type="button"
                      className="sim-suggestion-btn"
                    >
                      <span>{s}</span>
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {busy && (
              <div className="thinking">
                <span className="dot green" />
                <span>El asistente está preparando la respuesta…</span>
              </div>
            )}
          </div>

          <form
            className="composer"
            onSubmit={e => {
              e.preventDefault()
              void send(text)
            }}
          >
            <input
              aria-label="Mensaje de prueba"
              placeholder="Escribe tu consulta…"
              value={text}
              maxLength={4000}
              onChange={e => setText(e.target.value)}
            />
            <button
              className="primary icon-button"
              disabled={busy || !text.trim()}
              aria-label="Enviar consulta"
              type="submit"
            >
              <Send size={17} />
            </button>
          </form>
          {mode==='human' && <p className="composer-note" role="status">Mensaje registrado para el asesor. La IA está pausada hasta que el equipo pulse «Reanudar IA».</p>}
        </section>

        <aside className="simulator-guide">
          <div className="guide-card panel">
            <span className="eyebrow">DEL CHAT AL SEGUIMIENTO</span>
            <h2>Comprueba cada paso</h2>

            <label className="guide-label">
              Nombre del visitante
              <input
                value={name}
                maxLength={200}
                onChange={e => setName(e.target.value)}
                placeholder="Nombre para la prueba"
              />
            </label>

            <div className="guide-stepper">
              <ol>
                <li>Pregunta por un curso y su pénsum.</li>
                <li>Comparte tu objetivo y experiencia.</li>
                <li>Plantea una objeción de precio.</li>
                <li>Solicita inscripción o un asesor.</li>
                <li>Retoma el hilo desde Conversaciones.</li>
              </ol>
            </div>

            {leadId && (
              <button
                className="primary full btn-view-lead"
                onClick={() => openLead(leadId)}
                type="button"
              >
                <span>Ver prospecto</span>
                <ArrowRight size={16} />
              </button>
            )}

            {mode && (
              <div className="mode-pill-card">
                <Radio size={13} />
                <p className="subtle">
                  Motor de la última respuesta:{' '}
                  <strong>{modeDescriptions[mode] || mode}</strong>
                </p>
              </div>
            )}

            <div className="info-strip guide-info-strip">
              <ShieldCheck size={18} />
              <p>
                Esta prueba crea un prospecto identificado como Simulador. Puedes usarlo para
                demostrar la intervención humana y el handover en vivo.
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

