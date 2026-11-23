import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/health')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ status: 'ok', service: 'ScreenPilot', version: '0.1.0' }),
              { status: 200 },
            ),
          )
        }
        if (url.endsWith('/ready')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                status: 'not_ready',
                checks: {
                  database: { status: 'down', detail: 'ConnectionRefusedError' },
                  redis: { status: 'down', detail: 'ConnectionRefusedError' },
                },
              }),
              { status: 503 },
            ),
          )
        }
        if (url.endsWith('/api/capabilities')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                capabilities: [
                  {
                    name: 'agent',
                    state: 'unavailable',
                    detail: 'LangGraph runtime is not enabled in this build.',
                  },
                ],
              }),
              { status: 200 },
            ),
          )
        }
        return Promise.resolve(new Response('not found', { status: 404 }))
      }),
    )
  })

  it('renders foundation status from the API', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'ScreenPilot', level: 1 })).toBeInTheDocument()
    })

    expect(screen.getByText('ok')).toBeInTheDocument()
    expect(screen.getByText('not_ready')).toBeInTheDocument()
    expect(screen.getByText('agent')).toBeInTheDocument()
    expect(
      screen.getByText('LangGraph runtime is not enabled in this build.'),
    ).toBeInTheDocument()
  })
})