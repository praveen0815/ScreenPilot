import type { TaskEventWire } from '../../types/api'
import { formatDate } from '../../lib/format'

export function TaskEventTimeline({ events }: { events: TaskEventWire[] }) {
  if (!events.length) {
    return <p className="text-sm text-slate-500">No realtime events yet.</p>
  }
  return (
    <ul className="relative space-y-3 border-l border-slate-700/80 pl-6" aria-label="Task event stream">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span className="absolute -left-[1.6rem] top-1.5 h-2.5 w-2.5 rounded-full bg-emerald-500/90 ring-4 ring-[#0a0f1a]" />
          <p className="text-sm font-medium text-slate-200">
            <span className="text-cyan-400">#{event.sequence}</span> {event.type.replaceAll('_', ' ')}
          </p>
          <p className="text-xs text-slate-500">{formatDate(event.occurred_at)}</p>
          {event.payload.message ? (
            <p className="mt-1 text-sm text-slate-400">{event.payload.message}</p>
          ) : null}
          {event.payload.tool_name ? (
            <p className="text-xs text-slate-500">Tool: {event.payload.tool_name}</p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}