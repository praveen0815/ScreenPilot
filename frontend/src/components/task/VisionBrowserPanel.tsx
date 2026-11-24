import type { ToolExecution } from '../../types/api'
import { filterToolRuns } from './ToolActivityList'
import { truncate } from '../../lib/format'

function tryParseJson(raw: string | null): Record<string, unknown> | null {
  if (!raw) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as unknown
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : null
  } catch {
    return null
  }
}

export function BrowserSessionPanel({ runs }: { runs: ToolExecution[] }) {
  const browser = filterToolRuns(runs, 'tool.browser.')
  const shots = browser.filter((r) => r.tool_name.includes('screenshot') && r.status === 'succeeded')
  if (!browser.length) {
    return (
      <p className="text-sm text-slate-500">
        No browser tool activity. Enable browser automation in the backend to see session data here.
      </p>
    )
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Browser actions only — sensitive page content is truncated. Full DOM/credentials are not shown.
      </p>
      <ul className="space-y-3">
        {browser.map((run) => (
          <li key={run.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <p className="font-mono text-sm text-slate-200">{run.tool_name}</p>
            <p className="mt-1 text-xs text-slate-500">{run.status}</p>
            {run.result_json ? (
              <pre className="mt-2 max-h-32 overflow-auto text-xs text-slate-400">
                {truncate(run.result_json, 400)}
              </pre>
            ) : null}
          </li>
        ))}
      </ul>
      {shots.length ? (
        <div>
          <h4 className="text-sm font-medium text-slate-300">Screenshot metadata</h4>
          <ul className="mt-2 space-y-2">
            {shots.map((run) => {
              const data = tryParseJson(run.result_json)
              const bytes = data?.byte_length ?? data?.size
              return (
                <li key={run.id} className="text-xs text-slate-500">
                  Capture recorded
                  {typeof bytes === 'number' ? ` (${bytes} bytes)` : ''}
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function VisionPanel({ runs }: { runs: ToolExecution[] }) {
  const vision = filterToolRuns(runs, 'tool.vision.')
  if (!vision.length) {
    return (
      <p className="text-sm text-slate-500">
        No vision/OCR tool runs for this task. Vision tools appear when enabled on the server.
      </p>
    )
  }
  return (
    <ul className="space-y-3">
      {vision.map((run) => {
        const data = tryParseJson(run.result_json)
        const text =
          typeof data?.text === 'string'
            ? data.text
            : typeof data?.summary === 'string'
              ? data.summary
              : run.result_json
        return (
          <li key={run.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <p className="font-mono text-sm text-cyan-300/90">{run.tool_name}</p>
            <p className="mt-2 text-sm text-slate-300" title="Untrusted observed content">
              {truncate(String(text ?? '—'), 500)}
            </p>
            <p className="mt-2 text-xs text-slate-600">OCR/vision output is treated as untrusted data.</p>
          </li>
        )
      })}
    </ul>
  )
}