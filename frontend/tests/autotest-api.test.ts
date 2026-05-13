import { describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  post: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: vi.fn(),
  getBlob: vi.fn(),
  post: apiMocks.post,
}))

import { AUTOTEST_RUN_TIMEOUT_MS, startAutoTest } from '../src/autotest-api'

describe('autotest API client', () => {
  it('uses a long timeout only for the AutoTest run request', async () => {
    const formData = new FormData()
    apiMocks.post.mockResolvedValueOnce({ id: 'run-1', status: 'passed', steps: [] })

    await startAutoTest(formData)

    expect(AUTOTEST_RUN_TIMEOUT_MS).toBe(5 * 60 * 1000)
    expect(apiMocks.post).toHaveBeenCalledWith('/api/autotest/run', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: AUTOTEST_RUN_TIMEOUT_MS,
    })
  })
})
