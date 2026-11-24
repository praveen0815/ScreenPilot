import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { approveTask, getTask, listTasks, rejectApproval } from '../api/services'
import { ApprovalCard } from '../components/approval/ApprovalCard'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import type { AgentTask, AgentTaskDetail } from '../types/api'

type ApprovalRow = { task: AgentTask; detail: AgentTaskDetail }

export function ApprovalsPage() {
  const [rows, setRows] = useState<ApprovalRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const tasks = await listTasks()
      const waiting = tasks.filter((t) => t.status === 'awaiting_approval')
      const details = await Promise.all(waiting.map(async (task) => ({ task, detail: await getTask(task.id) })))
      setRows(details)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals.')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Approval center</h1>
        <p className="mt-1 text-sm text-slate-400">Review high-risk plans before the agent executes.</p>
      </header>
      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}
      {rows.length ? (
        <div className="space-y-4">
          {rows.map(({ task, detail }) => {
            const pending = detail.approval_requests.find((a) => a.status === 'pending')
            if (!pending) {
              return null
            }
            return (
              <div key={task.id} className="space-y-2">
                <Link to={`/tasks/${task.id}`} className="text-sm text-cyan-400 hover:underline">
                  {task.instruction.slice(0, 120)}
                </Link>
                <ApprovalCard
                  approval={pending}
                  busy={busyId === task.id}
                  onApprove={() => {
                    setBusyId(task.id)
                    void approveTask(task.id)
                      .then(() => load())
                      .finally(() => setBusyId(null))
                  }}
                  onReject={(reason) => {
                    setBusyId(task.id)
                    void rejectApproval(task.id, pending.id, reason)
                      .then(() => load())
                      .finally(() => setBusyId(null))
                  }}
                />
              </div>
            )
          })}
        </div>
      ) : (
        <Card>
          <EmptyState title="No pending approvals" description="When a plan needs approval, it will appear here." />
        </Card>
      )}
    </div>
  )
}