import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import KnowledgeBase from '../src/components/KnowledgeBase.vue'
import { PrimeStubs } from './stubs'

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: vi.fn() }),
}))

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: mocks.get,
  post: mocks.post,
  patch: mocks.patch,
}))

describe('KnowledgeBase flows', () => {
  it('creates knowledge entry with status/source/related_item_ids', async () => {
    mocks.post.mockResolvedValueOnce({ message: 'ok' })
    mocks.get.mockResolvedValue([]).mockResolvedValueOnce([])

    const wrapper = mount(KnowledgeBase, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any

    vm.entry.problem = 'Problem'
    vm.entry.solution = 'Solution'
    vm.entry.status = 'draft'
    vm.entry.source_type = 'manual'
    vm.entry.source_ref = ''
    vm.entry.related_item_ids = ['document:doc123', 'photo:ph1']

    await vm.saveEntry()

    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post.mock.calls[0][0]).toBe('/api/knowledge/entries')
    expect(mocks.post.mock.calls[0][1]).toMatchObject({
      problem: 'Problem',
      solution: 'Solution',
      status: 'draft',
      source_type: 'manual',
      related_item_ids: ['document:doc123', 'photo:ph1'],
    })
  })

  it('edits knowledge entry via patch including related_item_ids', async () => {
    mocks.patch.mockResolvedValueOnce({ message: 'updated' })
    mocks.get.mockResolvedValue([]).mockResolvedValueOnce([])

    const wrapper = mount(KnowledgeBase, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.openEditor({
      id: 'k1',
      title: 'Title',
      problem: 'P',
      root_cause: '',
      solution: 'S',
      tags: '',
      notes: '',
      status: 'reviewed',
      source_type: 'document-derived',
      source_ref: 'document:doc123',
      related_item_ids: ['document:doc123'],
    })

    vm.editor.tags = 'tag1'
    vm.editor.related_item_ids = ['document:doc123', 'prompt:p1']

    await vm.saveEditor()

    expect(mocks.patch).toHaveBeenCalledWith('/api/knowledge/entries/k1', expect.any(Object))
    const payload = mocks.patch.mock.calls[0][1]
    expect(payload).toMatchObject({
      tags: 'tag1',
      source_type: 'document-derived',
      source_ref: 'document:doc123',
      related_item_ids: ['document:doc123', 'prompt:p1'],
    })
  })
})
