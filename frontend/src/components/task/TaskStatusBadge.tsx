import type { TaskStatus } from '../../types/api'

const tone: Record<TaskStatus, string> = {
  pending: 'bg-slate-700/60 text-slate-200',
  planning: 'bg-blue-500/20 text-blue-200 ring-blue-400/30',
  awaiting_approval: 'bg-amber-500/20 text-amber-100 ring-amber-400/40',
  running: 'bg-cyan-500/20 text-cyan-100 ring-cyan-400/40 animate-pulse',
  paused: 'bg-violet-500/20 text-violet-100 ring-violet-400/30',
  completed: 'bg-emerald-500/20 text-emerald-200 ring-emerald-400/30',
  failed: 'bg-red-500/20 text-red-200 ring-red-400/30',
  cancelled: 'bg-slate-600/40 text-slate-300',
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ${tone[status]}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}