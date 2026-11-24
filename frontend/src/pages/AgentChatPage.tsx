import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  approveTask,
  cancelTask,
  createTask,
  fetchTaskMemory,
  getTask,
  rejectApproval,
  resumeTask,
  runAgent,
  runTask,
} from '../api/services'
import { ApprovalCard } from '../components/approval/ApprovalCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { PlanStepsList, taskProgress } from '../components/task/PlanStepsList'
import { TaskStatusBadge } from '../components/task/TaskStatusBadge'
import type { AgentTaskDetail, MemoryEntry } from '../types/api'

type ChatLine = { role: 'user' | 'agent'; text: string; at: string }

export function AgentChatPage() {
  const [instruction, setInstruction] = useState('')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AgentTaskDetail | null>(null)
  const [chat, setChat] = useState<ChatLine[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshTask = useCallback(async (id: string) => {
    const row = await getTask(id)
    setDetail(row)
    return row
  }, [])

  const appendMemory = useCallback(async (id: string) => {
    try {
      const memory = await fetchTaskMemory(id)
      const lines: ChatLine[] = memory.conversation.map((entry: MemoryEntry) => ({
        role: entry.kind.includes('user') ? 'user' : 'agent',
        text: entry.content,
        at: entry.created_at,
      }))
      if (lines.length) {
        setChat(lines)
      }
    } catch {
      // optional
    }
  }, [])

  async function onSend(event: FormEvent) {
    event.preventDefault()
    const text = instruction.trim()
    if (!text) {
      return
    }
    setBusy(true)
    setError(null)
    setChat((prev) => [...prev, { role: 'user', text, at: new Date().toISOString() }])
    setInstruction('')
    try {
      const run = await runAgent(text)
      setTaskId(run.task_id)
      await refreshTask(run.task_id)
      setChat((prev) => [
        ...prev,
        { role: 'agent', text: run.outcome.message, at: new Date().toISOString() },
      ])
      if (run.status === 'awaiting_approval') {
        setChat((prev) => [
          ...prev,
          {
            role: 'agent',
            text: 'This plan requires your approval before execution.',
            at: new Date().toISOString(),
          },
        ])
      }
      await appendMemory(run.task_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run failed.')
    } finally {
      setBusy(false)
    }
  }

  async function onNewTask() {
    const text = instruction.trim() || 'Summarize application status'
    setBusy(true)
    setError(null)
    try {
      const created = await createTask(text)
      setTaskId(created.id)
      const run = await runTask(created.id)
      await refreshTask(created.id)
      setChat([
        { role: 'user', text, at: new Date().toISOString() },
        { role: 'agent', text: run.outcome.message, at: new Date().toISOString() },
      ])
      await appendMemory(created.id)
      setInstruction('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create task.')
    } finally {
      setBusy(false)
    }
  }

  async function onCancel() {
    if (!taskId) {
      return
    }
    setBusy(true)
    try {
      await cancelTask(taskId)
      await refreshTask(taskId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed.')
    } finally {
      setBusy(false)
    }
  }

  async function onResume() {
    if (!taskId) {
      return
    }
    setBusy(true)
    try {
      const run = await resumeTask(taskId)
      await refreshTask(run.task_id)
      setChat((prev) => [
        ...prev,
        { role: 'agent', text: run.outcome.message, at: new Date().toISOString() },
      ])
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Resume failed.'
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  const pendingApproval = detail?.approval_requests.find((a) => a.status === 'pending')

  useEffect(() => {
    if (!taskId || !detail) {
      return
    }
    if (!['running', 'planning'].includes(detail.status)) {
      return
    }
    const timer = window.setInterval(() => {
      void refreshTask(taskId)
    }, 4000)
    return () => window.clearInterval(timer)
  }, [taskId, detail, refreshTask])

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Agent chat</h1>
        <p className="mt-1 text-sm text-slate-400">
          Describe a task; the agent plans and executes through your API.
        </p>
      </header>

      {error ? <ErrorBanner message={error} /> : null}

      <Card>
        <div className="max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-950/50 p-4" aria-live="polite">
          {chat.length ? (
            chat.map((line, idx) => (
              <div
                key={`${line.at}-${idx}`}
                className={`flex ${line.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                    line.role === 'user' ? 'bg-cyan-500/20 text-cyan-50' : 'bg-slate-800 text-slate-200'
                  }`}
                >
                  {line.text}
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">No messages yet. Send an instruction to start.</p>
          )}
        </div>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={(e) => void onSend(e)}>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={2}
            placeholder="e.g. Check application status and summarize for the team"
            className="min-h-[3rem] flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40"
            aria-label="Task instruction"
          />
          <div className="flex flex-col gap-2 sm:w-40">
            <Button type="submit" disabled={busy}>
              {busy ? 'Running…' : 'Run agent'}
            </Button>
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void onNewTask()}>
              New task
            </Button>
          </div>
        </form>
      </Card>

      {detail ? (
        <Card title="Task progress">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <TaskStatusBadge status={detail.status} />
            {taskId ? (
              <Link to={`/tasks/${taskId}`} className="text-sm text-cyan-400 hover:underline">
                Open details
              </Link>
            ) : null}
            <div className="ml-auto flex flex-wrap gap-2">
              {detail.status === 'paused' || detail.status === 'awaiting_approval' ? (
                <Button variant="secondary" disabled={busy} onClick={() => void onResume()}>
                  Resume
                </Button>
              ) : null}
              {!['completed', 'failed', 'cancelled'].includes(detail.status) ? (
                <Button variant="danger" disabled={busy} onClick={() => void onCancel()}>
                  Cancel
                </Button>
              ) : null}
            </div>
          </div>
          <div className="mb-3 h-2 rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-cyan-500 transition-all"
              style={{ width: `${taskProgress(detail.steps)}%` }}
            />
          </div>
          <PlanStepsList steps={detail.steps} />
        </Card>
      ) : null}

      {pendingApproval && taskId ? (
        <ApprovalCard
          approval={pendingApproval}
          busy={busy}
          onApprove={() => void approveTask(taskId).then(() => refreshTask(taskId))}
          onReject={(reason) =>
            void rejectApproval(taskId, pendingApproval.id, reason).then(() => refreshTask(taskId))
          }
        />
      ) : null}
    </div>
  )
}