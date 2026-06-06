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
    expect(store.state.error.knowledgeEntries).toContain('回傳格式無效')
    expect(store.state.lists.knowledgeEntries).toEqual([])
  })

  it('keeps the last successful workspace data when a refresh fails', async () => {
    const { useWorkspaceStore } = await import('../src/workspace-store')

    mocks.get.mockResolvedValueOnce([
      {
        id: 'doc-1',
        filename: 'demo.md',
        category: 'guide',
        tags: 'docs',
        status: 'reviewed',
        uploaded_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
        file_size: 12,
        uploaded_by: 'owner',
        index_status: 'indexed',
        index_error: '',
        indexed_at: '2026-05-01T00:00:00Z',
      },
    ])
    const store = useWorkspaceStore()

    await store.refreshDocuments({ force: true })

    mocks.get.mockRejectedValueOnce(new Error('network offline'))
    await store.refreshDocuments({ force: true })

    expect(store.state.status.documents).toBe('error')
    expect(store.state.error.documents).toContain('正在顯示上次成功載入的資料')
    expect(store.state.lists.documents).toHaveLength(1)
    expect(store.state.lists.documents[0]?.id).toBe('doc-1')
  })

  it('refreshAll loads every workspace list endpoint', async () => {
    const { apiPaths } = await import('../src/api/endpoints')
    const { useWorkspaceStore } = await import('../src/workspace-store')

    mocks.get.mockResolvedValue([])
    const store = useWorkspaceStore()

    await store.refreshAll({ force: true })

    expect(mocks.get).toHaveBeenCalledWith(apiPaths.docs.list)
    expect(mocks.get).toHaveBeenCalledWith(apiPaths.photos.list)
    expect(mocks.get).toHaveBeenCalledWith(apiPaths.knowledge.list)
    expect(mocks.get).toHaveBeenCalledWith(apiPaths.logbook.list)
    expect(mocks.get).toHaveBeenCalledWith(apiPaths.autotest.listRuns)
    expect(mocks.get).toHaveBeenCalledWith(apiPaths.prompts.list)
  })

  it('reset clears loaded data, errors, statuses, and cache timestamps', async () => {
    const { useWorkspaceStore } = await import('../src/workspace-store')

    mocks.get.mockResolvedValueOnce([
      {
        id: 'doc-1',
        filename: 'demo.md',
        category: 'guide',
        tags: 'docs',
        status: 'reviewed',
        uploaded_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
        file_size: 12,
        uploaded_by: 'owner',
        index_status: 'indexed',
        index_error: '',
        indexed_at: '2026-05-01T00:00:00Z',
      },
    ])
    const store = useWorkspaceStore()
    await store.refreshDocuments({ force: true })

    expect(store.state.lists.documents).toHaveLength(1)

    store.reset()

    expect(store.state.lists.documents).toEqual([])
    expect(store.state.error.documents).toBe('')
    expect(store.state.status.documents).toBe('idle')
    expect(store.state.lastLoadedAt.documents).toBe(0)
  })
})
