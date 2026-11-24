import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import {
  approveTask,
  cancelTask,
  getTask,
  rejectApproval,
  resumeTask,
  runTask,
  fetchTaskMemory,
} from '../api/services'
import { ApprovalCard } from '../components/approval/ApprovalCard'
import { ExecutionTimeline } from '../components/task/ExecutionTimeline'
import { TaskEventTimeline } from '../components/task/TaskEventTimeline'
import { useTaskEventStream } from '../hooks/useTaskEventStream'
import { PlanStepsList, taskProgress } from '../components/task/PlanStepsList'
import { filterToolRuns, ToolActivityList } from '../components/task/ToolActivityList'
import { TaskStatusBadge } from '../components/task/TaskStatusBadge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { LoadingScreen } from '../components/ui/LoadingScreen'
import type { AgentTaskDetail, TaskMemoryResponse } from '../types/api'
import { formatDate, truncate } from '../lib/format'

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'tools', label: 'Tool activity' },
  { id: 'browser', label: 'Browser' },
  { id: 'vision', label: 'Vision' },
] as const

type TabId = (typeof tabs)[number]['id']

export function TaskDetailPage() {
  const { taskId = '' } = useParams()
  const [search, setSearch] = useSearchParams()
  const tab = (search.get('view') as TabId) ?? 'overview'

  const [detail, setDetail] = useState<AgentTaskDetail | null>(null)
  const [memory, setMemory] = useState<TaskMemoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const withBusy = async (fn: () => Promise<void>) => {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  const load = useCallback(async () => {
    if (!taskId) {
      return
    }
    setError(null)
    try {
      const row = await getTask(taskId)
      setDetail(row)
      try {
        setMemory(await fetchTaskMemory(taskId))
      } catch {
        setMemory(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task.')
    }
  }, [taskId])

  const { events: liveEvents, connection: liveConnection } = useTaskEventStream(taskId, (event) => {
    if (
      [
        'task_completed',
        'task_failed',
        'task_cancelled',
        'approval_required',
        'task_paused',
        'plan_generated',
        'tool_completed',
      ].includes(event.type)
    ) {
      void load()
    }
  })

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (liveConnection === 'connected') {
      return
    }
    if (!detail || !['running', 'planning', 'awaiting_approval', 'paused'].includes(detail.status)) {
      return
    }
    const timer = window.setInterval(() => void load(), 8000)
    return () => window.clearInterval(timer)
  }, [detail, load, liveConnection])

  const currentStep = useMemo(() => {
    if (!detail) {
      return undefined
    }
    return detail.steps.find((s) => s.status === 'running')?.sequence
  }, [detail])

  const browserRuns = useMemo(
    () => filterToolRuns(detail?.tool_executions ?? [], 'tool.browser.'),
    [detail],
  )
  const visionRuns = useMemo(
    () => filterToolRuns(detail?.tool_executions ?? [], 'tool.vision.'),
    [detail],
  )

  if (!taskId) {
    return <ErrorBanner message="Missing task id." />
  }

  if (!detail && !error) {
    return <LoadingScreen label="Loading task…" />
  }

  if (!detail) {
    return <ErrorBanner message={error ?? 'Task not found.'} onRetry={() => void load()} />
  }

  const pending = detail.approval_requests.find((a) => a.status === 'pending')

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/tasks" className="text-sm text-slate-500 hover:text-cyan-400">
            ← Task history
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-white">Task details</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">{detail.instruction}</p>
        </div>
        <TaskStatusBadge status={detail.status} />
      </div>

      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}

      <div className="flex flex-wrap gap-2">
        {detail.status === 'pending' ? (
          <Button disabled={busy} onClick={() => void withBusy(() => runTask(taskId).then(() => load()))}>
            Run
          </Button>
        ) : null}
        {['paused', 'awaiting_approval'].includes(detail.status) ? (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => void withBusy(() => resumeTask(taskId).then(() => load()))}
          >
            Resume
          </Button>
        ) : null}
        {!['completed', 'failed', 'cancelled'].includes(detail.status) ? (
          <Button
            variant="danger"
            disabled={busy}
            onClick={() => void withBusy(() => cancelTask(taskId).then(() => load()))}
          >
            Cancel
          </Button>
        ) : null}
      </div>

      <nav className="flex flex-wrap gap-2 border-b border-slate-800 pb-2" aria-label="Task views">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSearch({ view: item.id })}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              tab === item.id ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {pending ? (
        <ApprovalCard
          approval={pending}
          busy={busy}
          onApprove={() => void withBusy(() => approveTask(taskId).then(() => load()))}
          onReject={(reason) =>
            void withBusy(() => rejectApproval(taskId, pending.id, reason).then(() => load()))
          }
        />
      ) : null}

      {tab === 'overview' ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Live plan">
            <p className="mb-3 text-xs text-slate-500">
              Progress {taskProgress(detail.steps)}% · Updated {formatDate(detail.updated_at)}
            </p>
            <PlanStepsList steps={detail.steps} currentSequence={currentStep} />
          </Card>
          <Card title="Summary">
            {detail.outcome_message ? (
              <p className="text-sm text-slate-300">{detail.outcome_message}</p>
            ) : (
              <p className="text-sm text-slate-500">No outcome message yet.</p>
            )}
            {memory?.task_summary ? (
              <p className="mt-3 border-t border-slate-800 pt-3 text-sm text-slate-400">
                {memory.task_summary}
              </p>
            ) : null}
          </Card>
        </div>
      ) : null}

      {tab === 'timeline' ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card
            title="Realtime events"
            description={
              liveConnection === 'connected'
                ? 'Live stream connected'
                : `Stream: ${liveConnection}`
            }
          >
            <TaskEventTimeline events={liveEvents} />
          </Card>
          <Card title="Agent executions">
            <ExecutionTimeline runs={detail.agent_executions} />
          </Card>
        </div>
      ) : null}

      {tab === 'tools' ? (
        <Card title="Tool activity">
          <ToolActivityList items={detail.tool_executions} />
        </Card>
      ) : null}

      {tab === 'browser' ? (
        <Card title="Browser session activity" description="Summaries only — raw page content is not shown.">
          {browserRuns.length ? (
            <ToolActivityList items={browserRuns} />
          ) : (
            <p className="text-sm text-slate-500">No browser tools have run on this task.</p>
          )}
        </Card>
      ) : null}

      {tab === 'vision' ? (
        <Card title="Vision & OCR" description="Redacted previews from tool results.">
          {visionRuns.length ? (
            <ul className="space-y-3">
              {visionRuns.map((run) => (
                <li key={run.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                  <p className="font-mono text-sm text-slate-200">{run.tool_name}</p>
                  <p className="mt-2 text-xs text-slate-500">{formatDate(run.created_at)}</p>
                  {run.result_json ? (
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
                      {truncate(redactSecrets(run.result_json), 500)}
                    </pre>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No vision or OCR tools have run on this task.</p>
          )}
          {memory?.recent_tool_results.length ? (
            <div className="mt-6 border-t border-slate-800 pt-4">
              <p className="text-xs font-medium text-slate-400">Memory excerpts</p>
              <ul className="mt-2 space-y-2">
                {memory.recent_tool_results.slice(0, 5).map((entry) => (
                  <li key={entry.id} className="text-xs text-slate-500">
                    {truncate(entry.content, 200)}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}

function redactSecrets(text: string): string {
  return text.replace(/(password|token|secret|api[_-]?key)/gi, '[redacted]')
}