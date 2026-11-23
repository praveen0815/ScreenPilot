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
  checks: {
    database: CheckResult
    redis: CheckResult
  }
}

export type CapabilityStatus = {
  name: string
  state: 'unavailable'
  detail: string
}

export type CapabilitiesResponse = {
  capabilities: CapabilityStatus[]
}