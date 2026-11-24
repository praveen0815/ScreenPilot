import { apiFetch, clearTokens, setTokens } from './client'
import type {
  AgentTask,
  AgentTaskDetail,
  CapabilitiesResponse,
  HealthResponse,
  PendingApprovalsResponse,
  ReadyResponse,
  RunTaskResponse,
  TaskMemoryResponse,
  TokenResponse,
  ToolCatalogResponse,
  UserPreferencesResponse,
  UserProfile,
  TaskEventWire,
} from '../types/api'

export async function registerUser(body: {
  email: string
  password: string
  display_name: string
}): Promise<TokenResponse> {
  const tokens = await apiFetch<TokenResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  setTokens(tokens)
  return tokens
}

export async function loginUser(body: { email: string; password: string }): Promise<TokenResponse> {
  const tokens = await apiFetch<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  setTokens(tokens)
  return tokens
}

export async function logoutUser(): Promise<void> {
  const refresh_token = localStorage.getItem('screenpilot_refresh_token')
  if (refresh_token) {
    try {
      await apiFetch<void>('/api/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token }),
      })
    } catch {
      // still clear locally
    }
  }
  clearTokens()
}

export async function fetchProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>('/api/users/me')
}

export async function updateProfile(display_name: string): Promise<UserProfile> {
  return apiFetch<UserProfile>('/api/users/me', {
    method: 'PATCH',
    body: JSON.stringify({ display_name }),
  })
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}

export async function fetchReady(): Promise<ReadyResponse> {
  const response = await fetch('/ready')
  const body = (await response.json()) as ReadyResponse
  if (!response.ok && response.status !== 503) {
    throw new Error(`Ready check failed (${response.status}).`)
  }
  return body
}

export async function fetchCapabilities(): Promise<CapabilitiesResponse> {
  return apiFetch<CapabilitiesResponse>('/api/capabilities')
}

export async function listTasks(): Promise<AgentTask[]> {
  return apiFetch<AgentTask[]>('/api/tasks')
}

export async function createTask(instruction: string): Promise<AgentTask> {
  return apiFetch<AgentTask>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  })
}

export async function getTask(taskId: string): Promise<AgentTaskDetail> {
  return apiFetch<AgentTaskDetail>(`/api/tasks/${taskId}`)
}

export async function fetchTaskEvents(
  taskId: string,
  afterSequence = 0,
): Promise<TaskEventWire[]> {
  return apiFetch<TaskEventWire[]>(
    `/api/tasks/${taskId}/events?after_sequence=${afterSequence}`,
  )
}

export async function runAgent(instruction: string): Promise<RunTaskResponse> {
  return apiFetch<RunTaskResponse>('/api/agent/runs', {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  })
}

export async function runTask(taskId: string): Promise<RunTaskResponse> {
  return apiFetch<RunTaskResponse>(`/api/tasks/${taskId}/run`, { method: 'POST' })
}

export async function resumeTask(taskId: string): Promise<RunTaskResponse> {
  return apiFetch<RunTaskResponse>(`/api/tasks/${taskId}/resume`, { method: 'POST' })
}

export async function cancelTask(taskId: string): Promise<AgentTask> {
  return apiFetch<AgentTask>(`/api/tasks/${taskId}/cancel`, { method: 'POST' })
}

export async function approveTask(taskId: string): Promise<AgentTask> {
  return apiFetch<AgentTask>(`/api/tasks/${taskId}/approve`, { method: 'POST' })
}

export async function listTaskApprovals(taskId: string): Promise<PendingApprovalsResponse> {
  return apiFetch<PendingApprovalsResponse>(`/api/tasks/${taskId}/approvals`)
}

export async function approveRequest(taskId: string, approvalId: string): Promise<void> {
  await apiFetch(`/api/tasks/${taskId}/approvals/${approvalId}/approve`, { method: 'POST' })
}

export async function rejectApproval(
  taskId: string,
  approvalId: string,
  reason?: string,
): Promise<AgentTask> {
  return apiFetch<AgentTask>(`/api/tasks/${taskId}/approvals/${approvalId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  })
}

export async function fetchTools(): Promise<ToolCatalogResponse> {
  return apiFetch<ToolCatalogResponse>('/api/tools')
}

export async function fetchTaskMemory(taskId: string): Promise<TaskMemoryResponse> {
  return apiFetch<TaskMemoryResponse>(`/api/tasks/${taskId}/memory`)
}

export async function fetchUserPreferences(): Promise<UserPreferencesResponse> {
  return apiFetch<UserPreferencesResponse>('/api/users/me/preferences')
}

export async function updateUserPreferences(
  preferences: Record<string, string>,
): Promise<UserPreferencesResponse> {
  return apiFetch<UserPreferencesResponse>('/api/users/me/preferences', {
    method: 'PATCH',
    body: JSON.stringify({ preferences }),
  })
}