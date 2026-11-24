import type { AgentExecution } from '../../types/api'
import { formatDate } from '../../lib/format'

export function ExecutionTimeline({ runs }: { runs: AgentExecution[] }) {
  if (!runs.length) {
    return <p className="text-sm text-slate-500">No execution records yet.</p>
  }
  const ordered = [...runs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
  return (
    <ul className="relative space-y-4 border-l border-slate-700/80 pl-6" aria-label="Execution timeline">
      {ordered.map((run) => (
        <li key={run.id} className="relative">
          <span className="absolute -left-[1.6rem] top-1.5 h-2.5 w-2.5 rounded-full bg-cyan-500 ring-4 ring-[#0a0f1a]" />
          <p className="text-sm font-medium capitalize text-slate-200">{run.status}</p>
          <p className="text-xs text-slate-500">{formatDate(run.started_at ?? run.created_at)}</p>
          {run.outcome_message ? (
            <p className="mt-1 text-sm text-slate-400">{run.outcome_message}</p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}