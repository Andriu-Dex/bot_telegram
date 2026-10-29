import React from 'react'
import { MessageCircle, Send, ShieldCheck, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react'
import { Status, providerState } from '../api'
import { PageHeading } from '../components/PageHeading'

interface SettingsProps {
  status: Status
}

export function Configuration({ status }: SettingsProps) {
  const ai=providerState(status)
  const channels = [
    {
      title: 'Telegram',
      icon: Send,
      ok: status.telegram_configured,
      statusLabel: status.telegram_configured ? 'Configurado' : 'Pendiente',
      badgeClass: status.telegram_configured ? 'interesado' : 'dudoso',
      text: 'Configura TELEGRAM_BOT_TOKEN y ejecuta el worker. El bot recibe consultas privadas y el asesor responde con la misma identidad.',
      badgeDetails: status.telegram_configured ? 'Token presente; comprueba el worker' : 'Requiere token'
    },
    {
      title: 'Inteligencia artificial',
      icon: Sparkles,
      ok: ai.ok,
      statusLabel: ai.label,
      badgeClass: ai.ok ? 'interesado' : 'dudoso',
      text: 'Configura AI_PROVIDER_ID=gemini, AI_PROVIDER_API_KEY y AI_PROVIDER_MODEL. Incluye clasificación semántica, conversación con herramientas y resumen para el asesor.',
      badgeDetails: ai.detail
    },
    {
      title: 'WhatsApp',
      icon: MessageCircle,
      ok: false,
      statusLabel: 'Próxima integración',
      badgeClass: 'dudoso',
      text: 'Preparado para incorporar un adaptador de WhatsApp Business Platform. Requiere credenciales de Meta, webhook verificado, políticas de ventana de atención y pruebas del canal.',
      badgeDetails: 'Arquitectura lista'
    }
  ]

  return (
    <div className="settings-view">
      <PageHeading
        eyebrow="CANALES Y OPERACIÓN"
        title="Un solo equipo. Varios canales."
        description="La lógica de atención vive en el backend y se comparte entre los conectores."
      />

      <div className="settings-grid">
        {channels.map(({ title, icon: Icon, ok, statusLabel, badgeClass, text, badgeDetails }) => (
          <section className="panel setting-card" key={title}>
            <div className="setting-card-top">
              <span className={`setting-icon-box ${ok ? 'active' : ''}`}>
                <Icon size={24} />
              </span>
              <span className={`badge ${badgeClass}`}>
                <span className="dot" />
                <span>{statusLabel}</span>
              </span>
            </div>

            <h2>{title}</h2>
            {title==='Inteligencia artificial' && status.llm_model && <p>Modelo configurado: <strong>{status.llm_model}</strong></p>}
            <p>{text}</p>

            <div className="setting-card-footer">
              <span className="setting-detail-pill">
                {ok ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                <span>{badgeDetails}</span>
              </span>
            </div>
          </section>
        ))}
      </div>

      <section className="panel security-note">
        <div className="security-icon-box">
          <ShieldCheck size={28} />
        </div>
        <div>
          <h2>Configuración segura</h2>
          <p>
            Las claves se guardan en el archivo local .env y nunca se exponen al navegador. El
            dashboard requiere una sesión y el conector usa una credencial interna independiente.
            Consulta README.md para el despliegue y los límites de esta versión.
          </p>
        </div>
      </section>
    </div>
  )
}

