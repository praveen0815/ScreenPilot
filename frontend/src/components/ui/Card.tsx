import type { ReactNode } from 'react'

export function Card({
  title,
  description,
  children,
  className = '',
}: {
  title?: string
  description?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-800/80 bg-slate-900/50 p-5 shadow-lg shadow-black/20 backdrop-blur-sm ${className}`}
    >
      {title ? (
        <header className="mb-4">
          <h2 className="text-base font-semibold text-slate-100">{title}</h2>
          {description ? <p className="mt-1 text-sm text-slate-400">{description}</p> : null}
        </header>
      ) : null}
      {children}
    </section>
  )
}