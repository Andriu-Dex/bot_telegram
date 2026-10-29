import React, { useState } from 'react'
import {
  ArrowUpRight,
  BookOpen,
  Calendar,
  Check,
  CircleHelp,
  Clock,
  DollarSign,
  ExternalLink,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  Users,
  X
} from 'lucide-react'
import { api, post, Course, date } from '../api'
import { Empty } from '../components/EmptyState'
import { PageHeading } from '../components/PageHeading'

interface CoursesProps {
  courses: Course[]
  report: (e: unknown) => void
  refresh: () => Promise<void>
  notify: (s: string) => void
}

export function Courses({ courses, report, refresh, notify }: CoursesProps) {
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [detail, setDetail] = useState<Course | null>(null)
  const [filterMode, setFilterMode] = useState<'all' | 'published' | 'pending'>('all')

  const review = async (c: Course, approved: boolean, accept_pending = false) => {
    setBusy(true)
    try {
      await api(`/courses/${c.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ approved, accept_pending })
      })
      setDetail(null)
      notify(approved ? 'Curso publicado para el asistente' : 'Curso retirado del asistente')
      await refresh()
    } catch (e) {
      report(e)
    } finally {
      setBusy(false)
    }
  }

  const handleSync = async () => {
    setBusy(true)
    try {
      const r = await api<{ fetched: number; changed: number; errors: string[] }>(
        '/courses/sync',
        post({})
      )
      notify(`${r.fetched} fichas importadas · ${r.changed} por revisar · ${r.errors.length} errores`)
      await refresh()
    } catch (e) {
      report(e)
    } finally {
      setBusy(false)
    }
  }

  const publishedCount = courses.filter(c => c.approved).length
  const pendingCount = courses.filter(c => !c.approved || c.pending).length

  const filteredCourses = courses.filter(c => {
    const matchesSearch = c.title.toLowerCase().includes(search.toLowerCase())
    if (!matchesSearch) return false
    if (filterMode === 'published') return c.approved
    if (filterMode === 'pending') return !c.approved || c.pending
    return true
  })
  const preview = detail ? {...detail, ...detail.pending} : null

  return (
    <div className="courses-view">
      <PageHeading
        eyebrow="INFORMACIÓN VERIFICABLE"
        title="Catálogo de cursos"
        description="Importa, revisa y publica la información que utilizará el asistente."
      >
        <button className="primary" disabled={busy} onClick={handleSync} type="button">
          <RefreshCw size={17} className={busy ? 'spin' : ''} />
          <span>{busy ? 'Importando…' : 'Sincronizar catálogo'}</span>
        </button>
      </PageHeading>

      <div className="catalog-toolbar">
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Buscar cursos"
            placeholder="Buscar en el catálogo…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </label>

        <div className="catalog-stats-pills">
          <button
            type="button"
            className={`catalog-filter-pill ${filterMode === 'all' ? 'active' : ''}`}
            onClick={() => setFilterMode('all')}
          >
            Todos ({courses.length})
          </button>
          <button
            type="button"
            className={`catalog-filter-pill ${filterMode === 'published' ? 'active' : ''}`}
            onClick={() => setFilterMode('published')}
          >
            Publicados ({publishedCount})
          </button>
          <button
            type="button"
            className={`catalog-filter-pill ${filterMode === 'pending' ? 'active' : ''}`}
            onClick={() => setFilterMode('pending')}
          >
            Por revisar ({pendingCount})
          </button>
          <span className="catalog-toolbar-summary">
            {publishedCount} publicados · {pendingCount} por revisar
          </span>
        </div>
      </div>

      {!courses.length ? (
        <section className="panel">
          <Empty
            title="Conecta el catálogo oficial"
            text="Pulsa Sincronizar catálogo para importar las fichas públicas del CTT-FISEI. Revisa cada ficha antes de aprobarla."
          />
        </section>
      ) : !filteredCourses.length ? (
        <section className="panel"><Empty title="No hay cursos que coincidan" text="Prueba con otro nombre o cambia el filtro del catálogo." /></section>
      ) : (
        <div className="course-grid">
          {filteredCourses.map(c => {
            const editionMatch = c.source_url.split('/').pop()?.replace('.php', '').toUpperCase()
            return (
              <article className="course-card" key={c.id}>
                <div className="course-top">
                  <span className="course-icon">
                    <BookOpen size={20} />
                  </span>
                  <span className={`badge ${c.approved ? 'interesado' : 'dudoso'}`}>
                    <span className="dot" />
                    <span>
                      {c.pending ? 'Cambios por revisar' : c.approved ? 'Publicado' : 'Por revisar'}
                    </span>
                  </span>
                </div>

                <div className="course-card-meta">
                  <small className="course-edition">
                    EDICIÓN {editionMatch || 'OFICIAL'} · {c.hours}
                  </small>
                </div>

                <h2>{c.title}</h2>
                <p>{c.content.replace(/^DESCRIPCIÓN\s*/, '').slice(0, 150)}…</p>

                <div className="course-bottom">
                  <span className={`availability ${c.status === 'ABIERTO' ? 'open' : ''}`}>
                    <span className="availability-dot" />
                    {c.status}
                  </span>
                  <button
                    className="text-button course-review-btn"
                    onClick={() => setDetail(c)}
                    type="button"
                  >
                    <span>Revisar ficha</span>
                    <ArrowUpRight size={15} />
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}

      <div className="info-strip">
        <CircleHelp size={17} />
        <p>
          “Abierto” refleja la etiqueta de la web. Revisa fechas y requisitos; los cupos se confirman
          con el centro.
        </p>
        <a
          href="https://ctt-talleresfisei.uta.edu.ec/course.php"
          target="_blank"
          rel="noreferrer"
          className="external-source-link"
        >
          <span>Fuente oficial</span>
          <ArrowUpRight size={14} />
        </a>
      </div>

      {detail && preview && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Revisión de curso"
            onClick={e => e.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label="Cerrar ficha"
              onClick={() => setDetail(null)}
              type="button"
            >
              <X size={18} />
            </button>

            <div className="modal-header">
              <span className="eyebrow">REVISIÓN DE FUENTE</span>
              <h2>{preview.title}</h2>
              <div className="modal-meta">
                <span className="subtle">Última importación: {date(detail.synced_at)}</span>
                <a
                  href={detail.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="modal-source-link"
                >
                  <span>Abrir ficha oficial</span>
                  <ArrowUpRight size={14} />
                </a>
              </div>
            </div>

            {detail.pending && (
              <div className="alert success">
                <Check size={16} />
                <span>
                  Se muestran los cambios importados. La versión anterior sigue publicada hasta que
                  los aceptes.
                </span>
              </div>
            )}

            <div className="modal-structured-preview">
              <div className="modal-chips-row">
                <span className="modal-chip">
                  <Clock size={13} />
                  <strong>Carga:</strong> {preview.hours}
                </span>
                <span
                  className={`modal-chip availability-chip ${
                    preview.status === 'ABIERTO' ? 'open' : ''
                  }`}
                >
                  <span className="dot" />
                  <strong>Estado:</strong> {preview.status}
                </span>
              </div>

              <div className="modal-content-box">
                <pre>{preview.content}</pre>
              </div>

              <div className="modal-registration-box">
                <p>
                  <strong>Inscripción: </strong>
                  <SafeLink url={preview.registration_url} />
                </p>
              </div>
            </div>

            <div className="modal-actions">
              <button
                className="secondary"
                disabled={busy}
                onClick={() => void review(detail, false)}
                type="button"
              >
                Retirar del asistente
              </button>
              <button
                className="primary"
                disabled={busy}
                onClick={() => void review(detail, true, !!detail.pending)}
                type="button"
              >
                <Check size={16} />
                <span>
                  {detail.pending ? 'Aceptar cambios y publicar' : 'Aprobar y publicar'}
                </span>
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function SafeLink({ url }: { url: string }) {
  return url.startsWith('https://') ? (
    <a href={url} target="_blank" rel="noreferrer" className="registration-safelink">
      <span>Enlace oficial de formulario</span>
      <ArrowUpRight size={14} />
    </a>
  ) : (
    <span className="safelink-disabled">No publicado</span>
  )
}

