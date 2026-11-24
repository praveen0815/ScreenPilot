import type { TaskStep } from '../../types/api'

const stepTone: Record<string, string> = {
  planned: 'border-slate-700',
  running: 'border-cyan-500/50 bg-cyan-500/5',
  completed: 'border-emerald-500/40 bg-emerald-500/5',
  failed: 'border-red-500/40 bg-red-500/5',
  skipped: 'border-slate-600 border-dashed opacity-80',
}

export function PlanStepsList({ steps, currentSequence }: { steps: TaskStep[]; currentSequence?: number }) {
  const ordered = [...steps].sort((a, b) => a.sequence - b.sequence)
  if (!ordered.length) {
    return <p className="text-sm text-slate-500">No plan steps yet.</p>
  }
  return (
    <ol className="space-y-3" aria-label="Plan steps">
      {ordered.map((step) => {
        const active = currentSequence === step.sequence
        return (
          <li
            key={step.id}
            className={`rounded-xl border px-4 py-3 transition ${stepTone[step.status] ?? 'border-slate-700'} ${active ? 'ring-2 ring-cyan-400/50' : ''}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-mono text-cyan-400/90">Step {step.sequence}</span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs capitalize ring-1 ring-inset ${
                  step.status === 'completed'
                    ? 'text-emerald-300 ring-emerald-500/30'
                    : step.status === 'failed'
                      ? 'text-red-300 ring-red-500/30'
                      : step.status === 'skipped'
                        ? 'text-slate-400 ring-slate-500/30'
                        : 'text-slate-300 ring-slate-500/30'
                }`}
              >
                {step.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-200">{step.description}</p>
            {step.tool_name ? (
              <p className="mt-1 font-mono text-xs text-slate-500">{step.tool_name}</p>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

export function taskProgress(steps: TaskStep[]): number {
  if (!steps.length) {
    return 0
  }
  const done = steps.filter((s) => ['completed', 'skipped', 'failed'].includes(s.status)).length
  return Math.round((done / steps.length) * 100)
}