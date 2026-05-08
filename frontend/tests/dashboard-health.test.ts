import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import ProjectHealthDashboard from '../src/components/ProjectHealthDashboard.vue'
import { PrimeStubs } from './stubs'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
}))

describe('ProjectHealthDashboard', () => {
  it('renders only backed dashboard metrics', async () => {
    mocks.get.mockResolvedValueOnce({
      knowledge: { total: 2, by_status: { draft: 1, reviewed: 1, verified: 0, archived: 0 } },
      logbook: { total: 1, with_solution: 1, promoted_to_knowledge: 1, resolution_rate: 100 },
      autotest: { total_runs: 3, passed: 2, failed: 1, pass_rate: 67, recent_runs: [] },
      documents: { total: 2, indexed: 1, pending: 1, failed_documents: 0, archived_documents: 0 },
      recent_activity: {
        days: 7,
        documents_added: 1,
        knowledge_added: 1,
        logbook_added: 1,
        autotest_runs: 2,
        autotest_passed: 1,
        autotest_failed: 1,
      },
    })

    const wrapper = mount(ProjectHealthDashboard, { global: { stubs: PrimeStubs } })
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(mocks.get).toHaveBeenCalledWith('/api/dashboard/health')
    expect(wrapper.text()).toContain('AutoTest Runs')
    expect(wrapper.text()).not.toContain('QA Count')
    expect(wrapper.text()).not.toContain('skipped')
  })
})
