import React from 'react'
import { ChevronRight } from 'lucide-react'
import { View } from './Sidebar'

interface TopbarProps {
  view: View
  live: boolean
}

const viewLabels: Record<View, string> = {
  overview: 'Resumen',
  inbox: 'Conversaciones',
  courses: 'Catálogo de cursos',
  simulator: 'Simulador',
  settings: 'Configuración'
}

export function Topbar({ view, live }: TopbarProps) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>Workspace</span>
        <ChevronRight size={14} className="breadcrumb-separator" />
        <strong>{viewLabels[view]}</strong>
      </div>
      <div className="topbar-actions">
        <span className={`live ${live ? 'connected' : ''}`}>
          <span className="dot" aria-hidden="true" />
          {live ? 'En tiempo real' : 'Reconectando…'}
        </span>
      </div>
    </header>
  )
}

