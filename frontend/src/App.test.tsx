import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
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
                checks: { database: { status: 'down' }, redis: { status: 'down' } },
              }),
              { status: 503 },
            ),
          )
        }
        if (url.endsWith('/api/capabilities')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                capabilities: [{ name: 'agent', state: 'mock', detail: 'Mock agent.' }],
              }),
              { status: 200 },
            ),
          )
        }
        return Promise.resolve(new Response('not found', { status: 404 }))
      }),
    )
  })

  it('redirects unauthenticated users to login', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    })
  })
})