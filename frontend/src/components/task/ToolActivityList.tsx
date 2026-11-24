import type { ToolExecution } from '../../types/api'
import { formatDate, truncate } from '../../lib/format'

const statusTone: Record<string, string> = {
  succeeded: 'text-emerald-300',
  failed: 'text-red-300',
  blocked: 'text-amber-300',
  running: 'text-cyan-300',
  pending: 'text-slate-400',
}

export function ToolActivityList({ items }: { items: ToolExecution[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">No tool runs recorded.</p>
  }
  const ordered = [...items].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
  return (
    <ul className="divide-y divide-slate-800/80">
      {ordered.map((item) => (
        <li key={item.id} className="py-3 first:pt-0">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-sm text-slate-200">{item.tool_name}</span>
            <span className={`text-xs capitalize ${statusTone[item.status] ?? 'text-slate-400'}`}>
              {item.status}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatDate(item.created_at)}</p>
          {item.result_json ? (
            <p className="mt-2 rounded-lg bg-slate-950/50 p-2 font-mono text-xs text-slate-400">
              {truncate(item.result_json, 280)}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

export function filterToolRuns(items: ToolExecution[], prefix: string): ToolExecution[] {
  return items.filter((row) => row.tool_name.startsWith(prefix))
}