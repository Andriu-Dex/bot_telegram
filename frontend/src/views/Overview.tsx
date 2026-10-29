import React from 'react'
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  Sparkles,
  Users,
  Zap,
  MessageCircle,
  TrendingUp,
  Activity
} from 'lucide-react'
import { Course, Lead, stages } from '../api'
import { View } from '../components/Sidebar'
import { Badge } from '../components/Badge'
import { Empty } from '../components/EmptyState'
import { PageHeading } from '../components/PageHeading'

interface OverviewProps {
  leads: Lead[]
  courses: Course[]
  openLead: (id: number) => void
  setView: (v: View) => void
}

export function Overview({ leads, courses, openLead, setView }: OverviewProps) {
  const hot = leads.filter(l => l.sentiment === 'caliente')
  const human = leads.filter(l => l.handoff)
  const enrolled = leads.filter(l => l.stage === 'inscrito')

  const ranking = courses
    .map(c => ({
      course: c,
      count: leads.filter(l => l.course_id === c.id).length
    }))
    .filter(c => c.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 4)

  const metricsData = [
    {
      label: 'Prospectos registrados',
      value: leads.length,
      icon: Users,
      note: 'Todos los canales',
      color: 'mint',
      indicator: '+ total'
    },
    {
      label: 'Listos para avanzar',
      value: hot.length,
      icon: Zap,
      note: 'Intención de inscripción',
      color: 'peach',
      indicator: 'Alta prioridad'
    },
    {
      label: 'Necesitan un asesor',
      value: human.length,
      icon: MessageCircle,
      note: 'IA en pausa',
      color: 'lavender',
      indicator: human.length > 0 ? 'Requiere atención' : 'Al día'
    },
    {
      label: 'Inscripciones confirmadas',
      value: enrolled.length,
      icon: Check,
      note: 'Verificadas por el equipo',
      color: 'blue',
      indicator: 'Cierre exitoso'
    }
  ]

  const funnelColors = ['#10b981', '#059669', '#0d9488', '#0284c7', '#2563eb']

  return (
    <div className="overview-view">
      <PageHeading
        eyebrow="TU CENTRO DE OPERACIONES"
        title="Una vista clara. Más oportunidades."
        description="Acompaña cada consulta hasta su próximo paso."
      >
        <button className="secondary action-btn-assistant" onClick={() => setView('simulator')}>
          <Sparkles size={16} />
          <span>Probar asistente</span>
          <ArrowUpRight size={15} />
        </button>
      </PageHeading>

      <div className="metrics">
        {metricsData.map(({ label, value, icon: Icon, note, color, indicator }) => (
          <article className="metric" key={label}>
            <div className="metric-header">
              <span className="metric-label">{label}</span>
              <span className={`metric-icon ${color}`}>
                <Icon size={18} />
              </span>
            </div>
            <strong className="metric-value">{value.toString().padStart(2, '0')}</strong>
            <div className="metric-footer">
              <small>{note}</small>
              <span className="metric-indicator-pill">{indicator}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="overview-grid">
        <section className="panel priority-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">EL SIGUIENTE PASO IMPORTA</span>
              <h2>Conversaciones que necesitan atención</h2>
            </div>
            <button className="text-button" onClick={() => setView('inbox')}>
              <span>Ver todas</span>
              <ArrowRight size={15} />
            </button>
          </div>

          {!leads.length ? (
            <Empty
              title="Tu próxima conversación empieza aquí"
              text="Prueba el simulador o conecta Telegram. Las consultas aparecerán en este espacio en tiempo real."
            />
          ) : (
            <div className="lead-list">
              {leads
                .filter(l => l.stage !== 'cerrado')
                .slice(0, 5)
                .map(l => (
                  <button
                    className="lead-row"
                    key={l.id}
                    onClick={() => openLead(l.id)}
                    type="button"
                  >
                    <span className={`avatar ${l.handoff ? 'warm' : ''}`}>
                      {l.name.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="lead-row-info">
                      <strong>{l.name}</strong>
                      <small>
                        {courses.find(c => c.id === l.course_id)?.title ||
                          'Explorando opciones de capacitación'}
                      </small>
                    </div>
                    <Badge lead={l} />
                    <ChevronRight size={16} />
                  </button>
                ))}
            </div>
          )}
        </section>

        <section className="panel funnel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">DEL INTERÉS A LA ACCIÓN</span>
              <h2>Embudo de admisiones</h2>
            </div>
            <TrendingUp size={18} className="panel-header-icon" />
          </div>

          <div className="funnel-body">
            {Object.entries(stages)
              .filter(([k]) => k !== 'cerrado')
              .map(([key, label], i) => {
                const count = leads.filter(l => l.stage === key).length
                const percent = leads.length > 0 ? Math.round((count / leads.length) * 100) : 0
                return (
                  <div className="funnel-row" key={key}>
                    <div className="funnel-row-top">
                      <span>
                        <i style={{ background: funnelColors[i % funnelColors.length] }} />
                        {label}
                      </span>
                      <div className="funnel-stats">
                        <strong>{count}</strong>
                        {leads.length > 0 && <small className="funnel-pct">{percent}%</small>}
                      </div>
                    </div>
                    <div className="track">
                      <span
                        style={{
                          width: `${percent}%`,
                          background: funnelColors[i % funnelColors.length]
                        }}
                      />
                    </div>
                  </div>
                )
              })}
          </div>
          <p className="subtle">La matrícula se confirma por un asesor.</p>
        </section>

        <section className="panel courses-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">LO QUE BUSCAN APRENDER</span>
              <h2>Cursos con más interés</h2>
            </div>
            <BookOpen size={18} className="panel-header-icon" />
          </div>

          <div className="ranking-body">
            {ranking.length ? (
              ranking.map(({ course, count }, i) => (
                <div className="rank-row" key={course.id}>
                  <span className="rank-index">0{i + 1}</span>
                  <div className="rank-info">
                    <strong>{course.title}</strong>
                    <small>
                      {count} prospecto{count !== 1 ? 's' : ''}
                    </small>
                  </div>
                  <ArrowUpRight size={17} className="rank-arrow" />
                </div>
              ))
            ) : (
              <p className="no-data">
                Los cursos aparecerán cuando los prospectos expresen interés en la conversación.
              </p>
            )}
          </div>
        </section>

        <section className="assistant-card">
          <div className="assistant-card-inner">
            <span className="assistant-icon">
              <Bot size={24} />
            </span>
            <div className="assistant-card-content">
              <span className="eyebrow">AUTOMATIZACIÓN CON CRITERIO HUMANO</span>
              <h2>
                Tu equipo y la IA,<br />
                en la misma conversación.
              </h2>
              <p>
                El asistente orienta y califica automáticamente. Tu equipo interviene cuando
                más importa y retoma el control en un clic.
              </p>
              <button
                className="assistant-card-btn"
                onClick={() => setView('inbox')}
                type="button"
              >
                <span>Ir a conversaciones</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
          <span className="decor-circle" aria-hidden="true" />
        </section>
      </div>
    </div>
  )
}

