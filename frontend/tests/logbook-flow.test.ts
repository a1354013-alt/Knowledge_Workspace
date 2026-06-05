import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import LogbookPanel from '../src/components/LogbookPanel.vue'
import { setLocale } from '../src/i18n'
import { PrimeStubs } from './stubs'

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: vi.fn() }),
}))

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
  post: mocks.post,
  patch: mocks.patch,
  del: mocks.del,
}))

describe('LogbookPanel flows', () => {
  it('creates logbook entry with status/source/related_item_ids', async () => {
    mocks.post.mockResolvedValueOnce({ message: 'ok' })
    mocks.get.mockResolvedValueOnce([])

    const wrapper = mount(LogbookPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any

    vm.form.title = 'T'
    vm.form.problem = 'P'
    vm.form.solution = 'S'
    vm.form.status = 'draft'
    vm.form.source_type = 'autotest-derived'
    vm.form.source_ref = 'autotest_run:r1'
    vm.form.related_item_ids = ['autotest_run:r1']

    await vm.saveEntry()

    expect(mocks.post).toHaveBeenCalledWith('/api/logbook/entries', expect.any(Object))
    const payload = mocks.post.mock.calls[0][1]
    expect(payload).toMatchObject({
      title: 'T',
      problem: 'P',
      solution: 'S',
      status: 'draft',
      source_type: 'autotest-derived',
      source_ref: 'autotest_run:r1',
      related_item_ids: ['autotest_run:r1'],
    })
  })

  it('promotes entry to knowledge', async () => {
    mocks.post.mockResolvedValueOnce({ knowledge_entry_id: 'k1' })
    mocks.get.mockResolvedValueOnce([])

    const wrapper = mount(LogbookPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    await vm.promoteEntry({ id: 'l1', title: 'T' })

    expect(mocks.post).toHaveBeenCalledWith('/api/logbook/entries/l1/promote-to-knowledge')
  })

  it('updates option labels when locale changes', async () => {
    setLocale('en')
    const wrapper = mount(LogbookPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any

    expect(vm.statusOptions[0].label).toBe('Draft')

    setLocale('zh-TW')
    await wrapper.vm.$nextTick()

    expect(vm.statusOptions[0].label).not.toBe('Draft')
    expect(vm.statusOptions[0].label).not.toBe('common.draft')
    setLocale('en')
  })
})
