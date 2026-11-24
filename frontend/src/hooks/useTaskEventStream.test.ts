/** @vitest-environment jsdom */

import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { setTokens } from '../api/client'
import { useTaskEventStream } from './useTaskEventStream'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  sent: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    queueMicrotask(() => this.onopen?.())
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.onclose?.()
  }

  push(frame: unknown) {
    this.onmessage?.({ data: JSON.stringify(frame) })
  }
}

describe('useTaskEventStream', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    setTokens({
      access_token: 'tok',
      refresh_token: 'ref',
      token_type: 'bearer',
      expires_in: 60,
    })
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('deduplicates events by id', async () => {
    const { result } = renderHook(() => useTaskEventStream('task-1'))
    const socket = MockWebSocket.instances[0]
    const payload = {
      id: 'e1',
      task_id: 'task-1',
      user_id: 'u1',
      type: 'tool_started',
      sequence: 1,
      occurred_at: '2026-01-01T00:00:00Z',
      agent_execution_id: null,
      tool_execution_id: null,
      payload: {},
    }
    socket.push({ type: 'event', event: payload })
    socket.push({ type: 'event', event: payload })
    await waitFor(() => {
      expect(result.current.events).toHaveLength(1)
    })
    expect(result.current.connection).toBe('connected')
  })
})