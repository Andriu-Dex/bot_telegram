import React from 'react'
import { Lead, sentiments } from '../api'

interface BadgeProps {
  lead: Lead
  className?: string
}

export function Badge({ lead, className = '' }: BadgeProps) {
  const sentimentKey = lead.sentiment || 'interesado'
  const label = sentiments[sentimentKey] || sentimentKey

  return (
    <span
      className={`badge ${sentimentKey} ${className}`.trim()}
      title={lead.sentiment_reason || label}
    >
      <span className="dot" aria-hidden="true" />
      <span className="badge-text">{label}</span>
    </span>
  )
}

