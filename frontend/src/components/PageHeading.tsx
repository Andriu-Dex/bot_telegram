import React from 'react'

interface PageHeadingProps {
  eyebrow: string
  title: string
  description: string
  children?: React.ReactNode
}

export function PageHeading({ eyebrow, title, description, children }: PageHeadingProps) {
  return (
    <div className="page-heading">
      <div className="page-heading-content">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="page-heading-actions">{children}</div>}
    </div>
  )
}

