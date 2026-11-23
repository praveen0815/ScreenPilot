interface StatusCardProps {
  title: string
  value: string
  detail?: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
}

const toneClasses: Record<NonNullable<StatusCardProps['tone']>, string> = {
  neutral: 'border-slate-700 bg-slate-900/60 text-slate-100',
  success: 'border-emerald-600/50 bg-emerald-950/40 text-emerald-100',
  warning: 'border-amber-600/50 bg-amber-950/40 text-amber-100',
  danger: 'border-rose-600/50 bg-rose-950/40 text-rose-100',
}

export function StatusCard({ title, value, detail, tone = 'neutral' }: StatusCardProps) {
  return (
    <article className={`rounded-xl border p-4 ${toneClasses[tone]}`}>
      <p className="text-sm uppercase tracking-wide opacity-80">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      {detail ? <p className="mt-2 text-sm opacity-75">{detail}</p> : null}
    </article>
  )
}