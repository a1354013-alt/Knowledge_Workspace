import { describe, expect, it, vi } from 'vitest'

describe('apiClient 401 handling', () => {
  it('clears token and notifies on any non-login 401', async () => {
    vi.resetModules()
    const clearToken = vi.fn()
    const notifyUnauthorized = vi.fn()

    vi.doMock('../src/auth.js', () => ({
      clearToken,
      getToken: () => 't',
      notifyUnauthorized,
    }))

    const { apiClient } = await import('../src/api')
    const handler = apiClient.interceptors.response.handlers.find((item) => typeof item?.rejected === 'function')?.rejected
    expect(typeof handler).toBe('function')

    await handler({
      response: { status: 401, data: { detail: 'unauthorized' } },
      config: { url: '/api/docs' },
      message: 'unauthorized',
    }).catch(() => {})

    expect(clearToken).toHaveBeenCalledTimes(1)
    expect(notifyUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('does not clear token for /api/login 401', async () => {
    vi.resetModules()
    const clearToken = vi.fn()
    const notifyUnauthorized = vi.fn()

    vi.doMock('../src/auth.js', () => ({
      clearToken,
      getToken: () => null,
      notifyUnauthorized,
    }))

    const { apiClient } = await import('../src/api')
    const handler = apiClient.interceptors.response.handlers.find((item) => typeof item?.rejected === 'function')?.rejected

    await handler({
      response: { status: 401, data: { detail: 'bad creds' } },
      config: { url: '/api/login' },
      message: 'unauthorized',
    }).catch(() => {})

    expect(clearToken).toHaveBeenCalledTimes(0)
    expect(notifyUnauthorized).toHaveBeenCalledTimes(0)
  })
})
