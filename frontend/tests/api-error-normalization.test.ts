import { describe, expect, it, vi } from 'vitest'

async function getRejectedHandler() {
  vi.resetModules()
  vi.doMock('../src/auth', () => ({
    clearToken: vi.fn(),
    getToken: () => null,
    notifyUnauthorized: vi.fn(),
  }))

  const { apiClient } = await import('../src/api')
  const handlers = (apiClient.interceptors.response as unknown as { handlers: Array<{ rejected?: unknown }> }).handlers
  return handlers.find((item) => typeof item?.rejected === 'function')?.rejected as
    | ((error: unknown) => Promise<unknown>)
    | undefined
}

describe('api error normalization', () => {
  it('prefers response.data.message over other sources', async () => {
    const handler = await getRejectedHandler()
    await expect(
      handler!({
        response: { status: 400, data: { message: 'Specific backend message', detail: 'secondary detail' } },
        config: { url: '/api/docs' },
        message: 'Axios fallback',
      })
    ).rejects.toMatchObject({
      message: 'Specific backend message',
      detail: 'secondary detail',
    })
  })

  it('uses response.data.detail when message is missing', async () => {
    const handler = await getRejectedHandler()
    await expect(
      handler!({
        response: { status: 400, data: { detail: 'Readable backend detail' } },
        config: { url: '/api/docs' },
        message: 'Axios fallback',
      })
    ).rejects.toMatchObject({
      message: 'Readable backend detail',
      detail: 'Readable backend detail',
    })
  })

  it('formats response.data.detail arrays into readable text', async () => {
    const handler = await getRejectedHandler()
    await expect(
      handler!({
        response: {
          status: 422,
          data: {
            detail: [
              { loc: ['query', 'limit'], msg: 'Input should be greater than or equal to 1' },
              { loc: ['query', 'q'], msg: 'Field required' },
            ],
          },
        },
        config: { url: '/api/search' },
        message: 'Axios fallback',
      })
    ).rejects.toMatchObject({
      message: 'query.limit: Input should be greater than or equal to 1; query.q: Field required',
      detail: 'query.limit: Input should be greater than or equal to 1; query.q: Field required',
    })
  })

  it('falls back to error.message when no response payload is available', async () => {
    const handler = await getRejectedHandler()
    await expect(
      handler!({
        config: { url: '/api/docs' },
        message: 'Network blew up',
      })
    ).rejects.toMatchObject({
      message: 'Network blew up',
      detail: 'Network blew up',
    })
  })

  it('falls back to Request failed when nothing else is available', async () => {
    const handler = await getRejectedHandler()
    await expect(
      handler!({
        config: { url: '/api/docs' },
      })
    ).rejects.toMatchObject({
      message: 'Request failed.',
      detail: 'Request failed.',
    })
  })
})
