import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import { adaptDashboardHealth } from '../src/adapters/dashboard'
import ProjectHealthDashboard from '../src/components/ProjectHealthDashboard.vue'
import { setLocale } from '../src/i18n'
import { PrimeStubs } from './stubs'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
}))

describe('ProjectHealthDashboard', () => {
  beforeEach(() => {
    setLocale('en')
  })

  it('adapts optional generated fields into the dashboard view model', () => {
    const adapted = adaptDashboardHealth({
      knowledge: { total: 1, by_status: { draft: 1, broken: 'bad' } as unknown as Record<string, number> },
      logbook: { total: 0, with_solution: 0, promoted_to_knowledge: 0, resolution_rate: 0 },
      autotest: { total_runs: 0, passed: 0, failed: 0, pass_rate: 0 },
      documents: { total: 0, indexed: 0, pending: 0, failed_documents: 0, archived_documents: 0 },
      recent_activity: {
        days: 7,
        documents_added: 0,
        knowledge_added: 0,
        logbook_added: 0,
        autotest_runs: 0,
        autotest_passed: 0,
        autotest_failed: 0,
      },
    })

    expect(adapted.knowledge.by_status).toEqual({ draft: 1, broken: 0 })
    expect(adapted.autotest.recent_runs).toEqual([])
  })

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
    expect(wrapper.text()).toContain('Knowledge status')
    expect(wrapper.text()).toContain('Recent runs')
    expect(wrapper.text()).toContain('Recent activity')
    expect(wrapper.text()).not.toContain('QA Count')
    expect(wrapper.text()).not.toContain('skipped')
  })

  it('moves detailed sections into dialogs instead of rendering them inline', async () => {
    mocks.get.mockResolvedValueOnce({
      knowledge: { total: 2, by_status: { draft: 1, reviewed: 1, verified: 0, archived: 0 } },
      logbook: { total: 1, with_solution: 1, promoted_to_knowledge: 1, resolution_rate: 100 },
      autotest: {
        total_runs: 3,
        passed: 2,
        failed: 1,
        pass_rate: 67,
        recent_runs: [{ id: 'run-1', project_name: 'Workspace ZIP', created_at: '2026-06-12T08:30:00Z', status: 'passed' }],
      },
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

    expect(wrapper.text()).not.toContain('Workspace ZIP')

    const openStatusButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Knowledge status'))

    expect(openStatusButton).toBeTruthy()

    await openStatusButton!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Knowledge by Status')
  })

  it('shows an error state when the dashboard API returns a malformed payload', async () => {
    mocks.get.mockResolvedValueOnce([] as never)

    const wrapper = mount(ProjectHealthDashboard, { global: { stubs: PrimeStubs } })
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Dashboard API returned an invalid payload.')
    expect(wrapper.text()).toContain('Retry')
  })

  it('renders archived counts inside the knowledge status dialog without implying pending indexing work', async () => {
    mocks.get.mockResolvedValueOnce({
      knowledge: { total: 2, by_status: { draft: 1, reviewed: 1, verified: 0, archived: 0 } },
      logbook: { total: 1, with_solution: 1, promoted_to_knowledge: 1, resolution_rate: 100 },
      autotest: { total_runs: 1, passed: 1, failed: 0, pass_rate: 100, recent_runs: [] },
      documents: { total: 1, indexed: 1, pending: 0, failed_documents: 0, archived_documents: 2 },
      recent_activity: {
        days: 7,
        documents_added: 1,
        knowledge_added: 1,
        logbook_added: 1,
        autotest_runs: 1,
        autotest_passed: 1,
        autotest_failed: 0,
      },
    })

    const wrapper = mount(ProjectHealthDashboard, { global: { stubs: PrimeStubs } })
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Archived')

    const openStatusButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Knowledge status'))

    expect(openStatusButton).toBeTruthy()

    await openStatusButton!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Archived')
    expect(wrapper.text()).toContain('pending')
    expect(wrapper.text()).not.toContain('pending2')
  })
})
