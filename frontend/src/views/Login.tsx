import React, { useState } from 'react'
import { ArrowRight, Command, ShieldCheck, Sparkles, CheckCircle2 } from 'lucide-react'
import { api, post } from '../api'

interface LoginProps {
  onLogin: () => void
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await api<{ token: string }>('/auth/login', post({ username, password }))
      sessionStorage.setItem('ctt_token', data.token)
      onLogin()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-art">
        <div className="login-art-header">
          <span className="brand-mark">
            <Command size={24} />
          </span>
          <span className="eyebrow">CTT-FISEI / ADMISIONES</span>
        </div>

        <div className="login-art-body">
          <h1>
            Cada conversación,<br />
            una nueva<br />
            <em>oportunidad.</em>
          </h1>
          <p>
            Plataforma inteligente de atención y seguimiento para el CTT-FISEI. Conecta a los
            prospectos con los programas de capacitación que impulsan su carrera.
          </p>

          <div className="login-feature-list">
            <div className="login-feature-item">
              <CheckCircle2 size={16} />
              <span>Calificación automática con IA conversacional</span>
            </div>
            <div className="login-feature-item">
              <CheckCircle2 size={16} />
              <span>Intervención humana inmediata y derivación de asesores</span>
            </div>
            <div className="login-feature-item">
              <CheckCircle2 size={16} />
              <span>Catálogo oficial verificado y sincronizado</span>
            </div>
          </div>
        </div>

        <div className="login-art-footer">
          <small>UNIVERSIDAD TÉCNICA DE AMBATO · FISEI</small>
        </div>

        <div className="login-orbit" aria-hidden="true">
          <Command size={120} />
        </div>
      </div>

      <div className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form-header">
            <span className="brand-mark">
              <Command size={26} />
            </span>
            <h2>Bienvenido a CTT Connect</h2>
            <p>Ingresa a tu espacio de atención y seguimiento.</p>
          </div>

          <label>
            Usuario
            <input
              autoComplete="username"
              required
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
            />
          </label>

          <label>
            Contraseña
            <input
              autoComplete="current-password"
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••••••"
            />
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="primary" disabled={busy} type="submit">
            <span>{busy ? 'Ingresando…' : 'Iniciar sesión'}</span>
            <ArrowRight size={17} />
          </button>

          <small className="login-security-notice">
            <ShieldCheck size={15} />
            <span>Acceso exclusivo para el equipo de admisiones</span>
          </small>
        </form>
      </div>
    </div>
  )
}

