import { describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  post: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: vi.fn(),
  getBlob: vi.fn(),
  post: apiMocks.post,
}))

import { startAutoTest } from '../src/autotest-api'

describe('autotest API client', () => {
  it('starts the async AutoTest job without overriding the shared request timeout', async () => {
    const formData = new FormData()
    apiMocks.post.mockResolvedValueOnce({ id: 'run-1', status: 'passed', steps: [] })

    await startAutoTest(formData)

    expect(apiMocks.post).toHaveBeenCalledWith('/api/autotest/run', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  })
})
