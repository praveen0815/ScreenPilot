import { useCallback, useEffect, useRef, useState } from 'react'

import { getAccessToken } from '../api/client'
import type { TaskEventWire } from '../types/api'

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error'

function wsBaseUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

export function useTaskEventStream(
  taskId: string | undefined,
  onEvent?: (event: TaskEventWire) => void,
) {
  const [events, setEvents] = useState<TaskEventWire[]>([])
  const [connection, setConnection] = useState<ConnectionState>('idle')
  const seenIds = useRef<Set<string>>(new Set())
  const lastSequence = useRef(0)
  const socketRef = useRef<WebSocket | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const ingest = useCallback((incoming: TaskEventWire) => {
    if (seenIds.current.has(incoming.id)) {
      return
    }
    seenIds.current.add(incoming.id)
    lastSequence.current = Math.max(lastSequence.current, incoming.sequence)
    setEvents((prev) => {
      const next = [...prev, incoming]
      next.sort((a, b) => a.sequence - b.sequence)
      return next
    })
    onEventRef.current?.(incoming)
  }, [])

  const cancelledRef = useRef(false)

  const connect = useCallback(() => {
    if (!taskId || cancelledRef.current) {
      return
    }
    const token = getAccessToken()
    if (!token) {
      setConnection('error')
      return
    }
    setConnection('connecting')
    const url = `${wsBaseUrl()}/api/ws/events?token=${encodeURIComponent(token)}&task_id=${encodeURIComponent(taskId)}`
    const socket = new WebSocket(url)
    socketRef.current = socket

    socket.onopen = () => {
      setConnection('connected')
      if (lastSequence.current > 0) {
        socket.send(
          JSON.stringify({
            type: 'resume',
            task_id: taskId,
            last_sequence: lastSequence.current,
          }),
        )
      }
    }
    socket.onmessage = (message) => {
      try {
        const frame = JSON.parse(message.data) as {
          type: string
          event?: TaskEventWire
        }
        if (frame.type === 'event' && frame.event) {
          ingest(frame.event)
        }
      } catch {
        // ignore malformed frames
      }
    }
    socket.onerror = () => setConnection('error')
    socket.onclose = () => {
      socketRef.current = null
      setConnection('idle')
      if (!cancelledRef.current) {
        window.setTimeout(() => connect(), 2500)
      }
    }
  }, [ingest, taskId])

  useEffect(() => {
    cancelledRef.current = false
    seenIds.current.clear()
    lastSequence.current = 0
    setEvents([])
    connect()
    return () => {
      cancelledRef.current = true
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [connect, taskId])

  return { events, connection, lastSequence: lastSequence.current }
}