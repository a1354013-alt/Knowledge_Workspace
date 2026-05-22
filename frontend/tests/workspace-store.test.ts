import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
}))

describe('workspace-store', () => {
  beforeEach(async () => {
    mocks.get.mockReset()
    vi.resetModules()
  })

  it('marks malformed important list payloads as an error instead of swallowing them into empty state', async () => {
    const { useWorkspaceStore } = await import('../src/workspace-store')

    mocks.get.mockResolvedValueOnce({ unexpected: true })
    const store = useWorkspaceStore()

    await store.refreshKnowledgeEntries({ force: true })

    expect(store.state.status.knowledgeEntries).toBe('error')
    expect(store.state.error.knowledgeEntries).toContain('invalid payload')
    expect(store.state.lists.knowledgeEntries).toEqual([])
  })
})
