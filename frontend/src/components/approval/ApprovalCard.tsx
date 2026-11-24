import { useState } from 'react'

import type { ApprovalRequest } from '../../types/api'
import { formatDate } from '../../lib/format'
import { Button } from '../ui/Button'

type ApprovalPlanDisplay = {
  goal?: string
  steps?: Array<{ sequence: number; description: string; tool_name: string; risk: string }>
}

function parseDisplay(json: string | null): ApprovalPlanDisplay | null {
  if (!json) {
    return null
  }
  try {
    return JSON.parse(json) as ApprovalPlanDisplay
  } catch {
    return null
  }
}

export function ApprovalCard({
  approval,
  onApprove,
  onReject,
  busy,
}: {
  approval: ApprovalRequest
  onApprove: () => void
  onReject: (reason: string) => void
  busy?: boolean
}) {
  const [reason, setReason] = useState('')
  const display = parseDisplay(approval.display_json)
  const pending = approval.status === 'pending'

  return (
    <article className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-amber-200/90">Approval required</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">{approval.category}</h3>
          {approval.detail ? <p className="mt-1 text-sm text-slate-400">{approval.detail}</p> : null}
        </div>
        <span className="rounded-full bg-slate-900 px-2 py-1 text-xs capitalize text-slate-300">
          {approval.status}
        </span>
      </div>
      {approval.expires_at ? (
        <p className="mt-3 text-xs text-slate-500">Expires {formatDate(approval.expires_at)}</p>
      ) : null}
      {display?.steps?.length ? (
        <ul className="mt-4 space-y-2 border-t border-amber-500/10 pt-4">
          {display.steps.map((step) => (
            <li key={step.sequence} className="text-sm text-slate-300">
              <span className="text-cyan-400/90">#{step.sequence}</span> {step.description}
              <span className="ml-2 text-xs text-slate-500">({step.risk} risk)</span>
            </li>
          ))}
        </ul>
      ) : null}
      {pending ? (
        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Button disabled={busy} onClick={onApprove}>
            Approve plan
          </Button>
          <div className="flex flex-1 flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Rejection reason (optional)"
              className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
              aria-label="Rejection reason"
            />
            <Button variant="danger" disabled={busy} onClick={() => onReject(reason)}>
              Reject
            </Button>
          </div>
        </div>
      ) : null}
    </article>
  )
}