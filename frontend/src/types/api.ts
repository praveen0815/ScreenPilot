export type HealthResponse = {
  status: 'ok'
  service: string
  version: string
}

export type CheckResult = {
  status: 'up' | 'down'
  detail?: string | null
}

export type ReadyResponse = {
  status: 'ready' | 'not_ready'
  checks: Record<string, CheckResult>
}

export type CapabilityStatus = {
  name: string
  state: 'unavailable' | 'mock' | 'available'
  detail: string
}

export type CapabilitiesResponse = {
  capabilities: CapabilityStatus[]
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export type UserProfile = {
  id: string
  email: string
  display_name: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
  updated_at: string
}

export type TaskStatus =
  | 'pending'
  | 'planning'
  | 'awaiting_approval'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type StepStatus = 'planned' | 'running' | 'completed' | 'failed' | 'skipped'

export type ToolExecutionStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'blocked'

export type ApprovalStatus = 'pending' | 'approved' | 'denied' | 'expired'

export type AgentTask = {
  id: string
  user_id: string
  instruction: string
  status: TaskStatus
  outcome_message: string | null
  cancel_requested: boolean
  pause_requested: boolean
  created_at: string
  updated_at: string
}

export type TaskStep = {
  id: string
  sequence: number
  description: string
  tool_name: string | null
  status: StepStatus
  created_at: string
  updated_at: string
}

export type AgentExecution = {
  id: string
  status: string
  outcome_message: string | null
  started_at: string | null
  ended_at: string | null
  created_at: string
}

export type ToolExecution = {
  id: string
  tool_name: string
  status: ToolExecutionStatus
  arguments_json: string | null
  result_json: string | null
  created_at: string
}

export type ApprovalRequest = {
  id: string
  category: string
  status: ApprovalStatus
  detail: string | null
  display_json: string | null
  expires_at: string | null
  decided_at: string | null
  rejection_reason: string | null
  created_at: string
  updated_at: string
}

export type AgentTaskDetail = AgentTask & {
  steps: TaskStep[]
  agent_executions: AgentExecution[]
  tool_executions: ToolExecution[]
  approval_requests: ApprovalRequest[]
}

export type AgentOutcome = {
  status: 'completed' | 'failed' | 'cancelled' | 'needs_user' | 'unavailable'
  message: string
}

export type RunTaskResponse = {
  task_id: string
  status: TaskStatus
  outcome: AgentOutcome
}

export type PendingApprovalsResponse = {
  task_id: string
  approvals: ApprovalRequest[]
}

export type ToolMetadata = {
  name: string
  version: string
  description: string
  risk: string
  required_permissions: string[]
  timeout_seconds: number
  input_schema: string
  output_schema: string
  available: boolean
}

export type ToolCatalogResponse = {
  tools: ToolMetadata[]
}

export type MemoryEntry = {
  id: string
  scope: string
  kind: string
  content: string
  content_chars: number
  expires_at: string | null
  created_at: string
}

export type TaskMemoryResponse = {
  task_id: string
  task_summary: string | null
  checkpoint: Record<string, unknown> | null
  conversation: MemoryEntry[]
  task_context: MemoryEntry[]
  recent_tool_results: MemoryEntry[]
  total_entries: number
  context_window_chars: number
  truncated: boolean
}

export type UserPreferencesResponse = {
  preferences: Record<string, string>
}

export type ApiErrorBody = {
  error?: {
    code?: string
    message?: string
  }
}

export type TaskEventType =
  | 'task_created'
  | 'planning_started'
  | 'plan_generated'
  | 'step_started'
  | 'tool_started'
  | 'tool_completed'
  | 'tool_failed'
  | 'approval_required'
  | 'task_paused'
  | 'task_resumed'
  | 'task_cancelled'
  | 'task_completed'
  | 'task_failed'

export type TaskEventPayload = {
  message?: string | null
  status?: string | null
  step_sequence?: number | null
  tool_name?: string | null
  outcome_status?: string | null
  approval_id?: string | null
}

export type TaskEventWire = {
  id: string
  task_id: string
  user_id: string
  type: TaskEventType
  sequence: number
  occurred_at: string
  agent_execution_id: string | null
  tool_execution_id: string | null
  payload: TaskEventPayload
}