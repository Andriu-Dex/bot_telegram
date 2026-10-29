import React from 'react'
import {
  BookOpen,
  ChevronRight,
  Command,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  Radio,
  Settings,
  Sparkles,
  LucideIcon
} from 'lucide-react'
import { Lead, Status } from '../api'

export type View = 'overview' | 'inbox' | 'courses' | 'simulator' | 'settings'

interface SidebarProps {
  view: View
  setView: (v: View) => void
  status: Status
  leads: Lead[]
  onLogout: () => void
}

export function Sidebar({ view, setView, status, leads, onLogout }: SidebarProps) {
  const humanCount = leads.filter(l => l.handoff).length

  const navItems: [View, LucideIcon, string, number | null][] = [
    ['overview', LayoutDashboard, 'Resumen', null],
    ['inbox', MessageCircle, 'Conversaciones', humanCount > 0 ? humanCount : null],
    ['courses', BookOpen, 'Catálogo de cursos', null],
    ['simulator', Sparkles, 'Simulador', null]
  ]

  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#resumen"
        onClick={e => {
          e.preventDefault()
          setView('overview')
        }}
      >
        <span className="brand-mark">
          <Command size={22} strokeWidth={2.2} />
        </span>
        <div className="brand-text">
          <span className="brand-name">
            ctt<span className="brand-light">connect</span>
          </span>
          <small className="brand-tagline">FISEI · UNIVERSIDAD TÉCNICA DE AMBATO</small>
        </div>
      </a>

      <div className="workspace">
        <span className="workspace-icon">CT</span>
        <div className="workspace-info">
          <span className="workspace-title">Centro de capacitación</span>
          <small>Espacio de admisiones</small>
        </div>
        <ChevronRight size={15} className="workspace-chevron" />
      </div>

      <span className="nav-caption">ESPACIO DE TRABAJO</span>

      <nav>
        {navItems.map(([id, Icon, label, count]) => {
          const isActive = view === id
          return (
            <button
              key={id}
              className={isActive ? 'active' : ''}
              onClick={() => setView(id)}
              type="button"
              aria-label={label}
              aria-current={isActive ? 'page' : undefined}
              title={label}
            >
              <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
              <span className="nav-label">{label}</span>
              {count !== null && <b>{count}</b>}
            </button>
          )
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="channel-card">
          <span className={`dot ${status.telegram_configured ? 'green' : ''}`} />
          <div className="channel-info">
            <span className="channel-title">Telegram</span>
            <small>
              {status.telegram_configured
                ? 'Credenciales configuradas'
                : 'Pendiente de conectar'}
            </small>
          </div>
          <Radio size={15} className="channel-icon" />
        </div>

        <button
          className={view === 'settings' ? 'active' : ''}
          onClick={() => setView('settings')}
          type="button"
          aria-label="Configuración"
          title="Configuración"
        >
          <Settings size={18} />
          <span className="nav-label">Configuración</span>
        </button>

        <div className="user">
          <span className="avatar">AD</span>
          <div className="user-info">
            <span className="user-name">Administrador</span>
            <small>Equipo de admisiones</small>
          </div>
          <button
            aria-label="Cerrar sesión"
            onClick={onLogout}
            type="button"
            className="user-logout"
            title="Cerrar sesión"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}

