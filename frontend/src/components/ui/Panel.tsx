import type { ReactNode } from 'react'

export function DarkPanel({
  children,
  className = '',
  as: Tag = 'div',
}: {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'aside'
}) {
  return (
    <Tag data-surface="dark" className={`bg-[var(--color-ink)] text-[var(--color-ink-text)] ${className}`}>
      {children}
    </Tag>
  )
}

export function PanelHeader({
  title,
  meta,
  children,
}: {
  title: string
  meta?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--color-ink-line)] px-5 py-3.5 sm:px-6">
      <h2 className="tech-label text-[var(--color-ink-text)]">{title}</h2>
      <div className="flex items-center gap-3">
        {meta}
        {children}
      </div>
    </div>
  )
}
