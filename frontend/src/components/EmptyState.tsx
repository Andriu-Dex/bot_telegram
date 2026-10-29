import React from 'react'
import { LucideIcon, MessageCircle } from 'lucide-react'

interface EmptyStateProps {
  title: string
  text: string
  icon?: LucideIcon
  action?: React.ReactNode
}

export function Empty({ title, text, icon: Icon = MessageCircle, action }: EmptyStateProps) {
  return (
    <div className="empty">
      <div className="empty-icon-wrap">
        <Icon size={28} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action && <div className="empty-action">{action}</div>}
    </div>
  )
}

