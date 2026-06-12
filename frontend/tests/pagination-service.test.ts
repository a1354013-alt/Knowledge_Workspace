import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
}))

describe('pagination service', () => {
  beforeEach(() => {
    mocks.get.mockReset()
    vi.resetModules()
  })

  it('fetches pages until has_more is false', async () => {
    const { fetchAllPages } = await import('../src/services/pagination')

    mocks.get
      .mockResolvedValueOnce({ items: [{ id: 'a' }, { id: 'b' }], total: 3, limit: 2, offset: 0, has_more: true })
      .mockResolvedValueOnce({ items: [{ id: 'c' }], total: 3, limit: 2, offset: 2, has_more: false })

    const items = await fetchAllPages<{ id: string }>('/api/example', 'Example', 2)

    expect(items.map((item) => item.id)).toEqual(['a', 'b', 'c'])
    expect(mocks.get).toHaveBeenNthCalledWith(1, '/api/example', { params: { limit: 2, offset: 0 } })
    expect(mocks.get).toHaveBeenNthCalledWith(2, '/api/example', { params: { limit: 2, offset: 2 } })
  })

  it('rejects malformed page payloads', async () => {
    const { fetchAllPages } = await import('../src/services/pagination')

    mocks.get.mockResolvedValueOnce({ items: [] })

    await expect(fetchAllPages('/api/example', 'Example', 2)).rejects.toThrow()
  })
})
