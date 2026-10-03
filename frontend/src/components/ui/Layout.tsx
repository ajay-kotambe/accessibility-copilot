import type { ReactNode } from 'react'

export function Divider({ className = '' }: { className?: string }) {
  return <hr className={`border-0 border-t border-[var(--color-line)] ${className}`} />
}

export function SectionHeading({
  index,
  title,
  lede,
  className = '',
}: {
  index?: string
  title: string
  lede?: string
  className?: string
}) {
  return (
    <div className={`max-w-2xl ${className}`}>
      {index && (
        <div className="mb-5 flex items-center gap-3">
          <span className="tech-label text-[var(--color-primary-text)]">{index}</span>
          <span className="h-px w-10 bg-[var(--color-line-strong)]" aria-hidden="true" />
        </div>
      )}
      <h2 className="editorial text-3xl sm:text-4xl md:text-[2.75rem]">{title}</h2>
      {lede && <p className="mt-5 max-w-xl text-[1.0625rem] leading-relaxed text-[var(--color-body)]">{lede}</p>}
    </div>
  )
}

/** Page-level container so every page shares one measure and gutter. */
export function Container({
  children,
  className = '',
  as: Tag = 'div',
}: {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'header' | 'footer' | 'main' | 'nav'
}) {
  return <Tag className={`mx-auto w-full max-w-[1240px] px-5 sm:px-8 lg:px-10 ${className}`}>{children}</Tag>
}
