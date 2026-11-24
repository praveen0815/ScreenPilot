import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listTasks } from '../api/services'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { TaskStatusBadge } from '../components/task/TaskStatusBadge'
import type { AgentTask } from '../types/api'
import { formatDate } from '../lib/format'

export function TaskHistoryPage() {
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setTasks(await listTasks())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks.')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const ordered = [...tasks].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Task history</h1>
        <p className="mt-1 text-sm text-slate-400">All tasks for your account.</p>
      </header>
      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}
      <Card>
        {ordered.length ? (
          <ul className="divide-y divide-slate-800">
            {ordered.map((task) => (
              <li key={task.id} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                <Link to={`/tasks/${task.id}`} className="min-w-0 flex-1 hover:text-cyan-300">
                  <p className="text-sm text-slate-200">{task.instruction}</p>
                  <p className="mt-1 text-xs text-slate-500">{formatDate(task.created_at)}</p>
                </Link>
                <TaskStatusBadge status={task.status} />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No tasks" description="Use Agent chat to create your first task." />
        )}
      </Card>
    </div>
  )
}