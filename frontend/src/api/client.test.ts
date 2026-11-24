import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiFetch, clearTokens, getAccessToken, setTokens } from './client'

describe('api client auth', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('attaches bearer token when present', async () => {
    setTokens({
      access_token: 'access-abc',
      refresh_token: 'refresh-abc',
      token_type: 'bearer',
      expires_in: 900,
    })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await apiFetch('/api/users/me')
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const hdrs = init.headers as Headers
    expect(hdrs).toBeInstanceOf(Headers)
    expect(getAccessToken()).toBe('access-abc')
    expect(hdrs.get('Authorization')).toBe('Bearer access-abc')
  })

  it('clears tokens on logout helper', () => {
    setTokens({
      access_token: 'x',
      refresh_token: 'y',
      token_type: 'bearer',
      expires_in: 1,
    })
    clearTokens()
    expect(getAccessToken()).toBeNull()
  })
})