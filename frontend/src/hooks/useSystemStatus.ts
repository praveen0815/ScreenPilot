import { useCallback, useEffect, useState } from 'react'

import type {
  CapabilitiesResponse,
  HealthResponse,
  ReadyResponse,
} from '../types/api'

type SystemStatusState = {
  health: HealthResponse | null
  ready: ReadyResponse | null
  capabilities: CapabilitiesResponse | null
  loading: boolean
  error: string | null
}

const initialState: SystemStatusState = {
  health: null,
  ready: null,
  capabilities: null,
  loading: true,
  error: null,
}

export function useSystemStatus() {
  const [state, setState] = useState<SystemStatusState>(initialState)

  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }))
    try {
      const [healthResponse, readyResponse, capabilitiesResponse] = await Promise.all([
        fetch('/health'),
        fetch('/ready'),
        fetch('/api/capabilities'),
      ])
      if (!healthResponse.ok) {
        throw new Error(`Health request failed with ${healthResponse.status}.`)
      }
      if (!capabilitiesResponse.ok) {
        throw new Error(
          `Capabilities request failed with ${capabilitiesResponse.status}.`,
        )
      }
      const health = (await healthResponse.json()) as HealthResponse
      let ready: ReadyResponse
      if (readyResponse.ok) {
        ready = (await readyResponse.json()) as ReadyResponse
      } else if (readyResponse.status === 503) {
        ready = (await readyResponse.json()) as ReadyResponse
      } else {
        throw new Error(`Ready request failed with ${readyResponse.status}.`)
      }
      const capabilities = (await capabilitiesResponse.json()) as CapabilitiesResponse
      setState({
        health,
        ready,
        capabilities,
        loading: false,
        error: null,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error.'
      setState({
        health: null,
        ready: null,
        capabilities: null,
        loading: false,
        error: message,
      })
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { ...state, refresh }
}