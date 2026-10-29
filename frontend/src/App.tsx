import React, { useCallback, useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import { api, Course, Lead, Status, token } from './api'
import { Sidebar, View } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Login } from './views/Login'
import { Overview } from './views/Overview'
import { Inbox } from './views/Inbox'
import { Courses } from './views/Courses'
import { Simulator } from './views/Simulator'
import { Configuration } from './views/Settings'

export function App() {
  const [logged, setLogged] = useState(!!token())
  const [view, setView] = useState<View>('overview')
  const [leads, setLeads] = useState<Lead[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [status, setStatus] = useState<Status>({
    telegram_configured: false,
    llm_configured: false
  })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [live, setLive] = useState(false)
  const [version, setVersion] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => { window.scrollTo({top:0,left:0,behavior:'auto'}) }, [view])

  const report = useCallback((e: unknown) => {
    setError(e instanceof Error ? e.message : String(e))
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [l, c, s] = await Promise.all([
        api<Lead[]>('/leads'),
        api<Course[]>('/courses'),
        api<Status>('/status')
      ])
      setLeads(l)
      setCourses(c)
      setStatus(s)
      setVersion(v => v + 1)
    } catch (e) {
      report(e)
    }
  }, [report])

  // Handle session expiration
  useEffect(() => {
    const expired = () => setLogged(false)
    window.addEventListener('session-expired', expired)
    return () => window.removeEventListener('session-expired', expired)
  }, [])

  // Initial load
  useEffect(() => {
    if (logged) {
      void refresh()
    }
  }, [logged, refresh])

  // Server-Sent Events (SSE) stream for live updates
  useEffect(() => {
    if (!logged) return

    const controller = new AbortController()
    let active = true

    async function connect() {
      while (active) {
        try {
          const response = await fetch('/api/events', {
            headers: { Authorization: `Bearer ${token()}` },
            signal: controller.signal
          })

          if (response.status === 401) {
            setLogged(false)
            return
          }

          if (!response.ok || !response.body) {
            throw Error('Conexión de eventos interrumpida')
          }

          setLive(true)
          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''

          while (active) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            let boundary: number

            while ((boundary = buffer.indexOf('\n\n')) >= 0) {
              const event = buffer.slice(0, boundary)
              buffer = buffer.slice(boundary + 2)
              if (event.startsWith('data:')) {
                await refresh()
              }
            }
          }
        } catch (e) {
          if (controller.signal.aborted) return
        }

        setLive(false)
        // Wait before reconnecting
        await new Promise(resolve => setTimeout(resolve, 2500))
      }
    }

    void connect()
    return () => {
      active = false
      controller.abort()
      setLive(false)
    }
  }, [logged, refresh])

  // Auto-dismiss notice
  useEffect(() => {
    if (notice) {
      const t = setTimeout(() => setNotice(''), 5000)
      return () => clearTimeout(t)
    }
  }, [notice])

  const openLead = (id: number) => {
    setSelected(id)
    setView('inbox')
  }

  const handleLogout = () => {
    sessionStorage.removeItem('ctt_token')
    setLogged(false)
  }

  if (!logged) {
    return <Login onLogin={() => setLogged(true)} />
  }

  return (
    <div className="shell">
      <Sidebar
        view={view}
        setView={setView}
        status={status}
        leads={leads}
        onLogout={handleLogout}
      />

      <main>
        <Topbar view={view} live={live} />

        {error && (
          <div className="alert error" role="alert">
            <span>{error}</span>
            <button
              aria-label="Cerrar alerta"
              onClick={() => setError('')}
              type="button"
              className="alert-close-btn"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {notice && (
          <div className="alert success" role="status">
            <Check size={16} />
            <span>{notice}</span>
          </div>
        )}

        <div className={`page ${view === 'inbox' ? 'inbox-page' : ''}`}>
          {view === 'overview' && (
            <Overview
              leads={leads}
              courses={courses}
              openLead={openLead}
              setView={setView}
            />
          )}

          {view === 'inbox' && (
            <Inbox
              leads={leads}
              courses={courses}
              selected={selected}
              select={setSelected}
              version={version}
              report={report}
              refresh={refresh}
            />
          )}

          {view === 'courses' && (
            <Courses
              courses={courses}
              report={report}
              refresh={refresh}
              notify={setNotice}
            />
          )}

          {view === 'simulator' && (
            <Simulator
              report={report}
              refresh={refresh}
              openLead={openLead}
              status={status}
              version={version}
            />
          )}

          {view === 'settings' && <Configuration status={status} />}
        </div>

        <footer>
          <div className="footer-brand">
            <strong>CTT-FISEI</strong>
            <span>Atención que conecta. Educación que transforma.</span>
          </div>
          <span className="footer-timezone">Hora de Ecuador · UTC−5</span>
        </footer>
      </main>
    </div>
  )
}

