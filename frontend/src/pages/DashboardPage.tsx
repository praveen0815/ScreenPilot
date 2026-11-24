import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { fetchCapabilities, listTasks } from '../api/services'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { taskProgress, PlanStepsList } from '../components/task/PlanStepsList'
import { TaskStatusBadge } from '../components/task/TaskStatusBadge'
import { ToolActivityList } from '../components/task/ToolActivityList'
import type { AgentTask, AgentTaskDetail, CapabilitiesResponse } from '../types/api'
import { getTask } from '../api/services'
import { formatDate } from '../lib/format'

export function DashboardPage() {
  const system = useSystemStatus()
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [activeDetail, setActiveDetail] = useState<AgentTaskDetail | null>(null)
  const [caps, setCaps] = useState<CapabilitiesResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [list, capabilities] = await Promise.all([listTasks(), fetchCapabilities()])
      setTasks(list)
      setCaps(capabilities)
      const active =
        list.find((t) => ['running', 'planning', 'awaiting_approval', 'paused'].includes(t.status)) ??
        list[0]
      if (active) {
        setActiveDetail(await getTask(active.id))
      } else {
        setActiveDetail(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard.')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const pendingApprovals = tasks.filter((t) => t.status === 'awaiting_approval')
  const recent = [...tasks].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  ).slice(0, 6)

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          Active work, system health, and agent readiness at a glance.
        </p>
      </header>

      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="!p-4">
          <p className="text-xs text-slate-500">Agent runtime</p>
          <p className="mt-2 text-lg font-medium text-cyan-300">
            {caps?.capabilities.find((c) => c.name === 'agent')?.state ?? '—'}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs text-slate-500">API health</p>
          <p className="mt-2 text-lg font-medium text-slate-100">{system.health?.status ?? '…'}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs text-slate-500">Approvals waiting</p>
          <p className="mt-2 text-lg font-medium text-amber-200">{pendingApprovals.length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs text-slate-500">Open tasks</p>
          <p className="mt-2 text-lg font-medium text-slate-100">{tasks.length}</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Active task">
          {activeDetail ? (
            <div className="space-y-4">
              <Demo active={activeDetail} />
            </div>
          ) : (
            <EmptyState title="No tasks yet" description="Start from Agent chat to run your first task." />
          )}
        </Card>
        <Card title="Recent tasks">
          {recent.length ? (
            <ul className="divide-y divide-slate-800">
              {recent.map((task) => (
                <li key={task.id} className="flex items-center justify-between gap-3 py-3">
                  <Link className="min-w-0 flex-1 text-sm text-cyan-300 hover:underline" to={`/tasks/${task.id}`}>
                    {task.instruction.slice(0, 80)}
                  </Link>
                  <TaskStatusBadge status={task.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No history" />
          )}
        </Card>
      </div>

      {activeDetail ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Plan progress">
            <div className="mb-4">
              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full bg-cyan-500 transition-all duration-500"
                  style={{ width: `${taskProgress(activeDetail.steps)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">{taskProgress(activeDetail.steps)}% complete</p>
            </div>
            <PlanStepsList steps={activeDetail.steps} />
          </Card>
          <Card title="Recent tool activity">
            <ToolActivityList items={activeDetail.tool_executions.slice(0, 8)} />
          </Card>
        </div>
      ) : null}
    </div>
  )
}

function Demo({ active }: { active: AgentTaskDetail }) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <TaskStatusBadge status={active.status} />
        <span className="text-xs text-slate-500">Updated {formatDate(active.updated_at)}</span>
      </div>
      <p className="text-sm text-slate-200">{active.instruction}</p>
      {active.outcome_message ? (
        <p className="text-sm text-slate-400">{active.outcome_message}</p>
      ) : null}
      <Link
        to={`/tasks/${active.id}`}
        className="inline-flex text-sm font-medium text-cyan-400 hover:text-cyan-300"
      >
        Open task details →
      </Link>
    </>
  )
}