import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import DocsPhotosPanel from '../src/components/DocsPhotosPanel.vue'
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

vi.mock('../src/services/downloads', () => ({
  downloadDocumentFile: vi.fn(async () => new Blob()),
  downloadPhotoFile: vi.fn(async () => new Blob()),
  previewDocumentFile: vi.fn(async () => new Blob()),
  previewPhotoFile: vi.fn(async () => new Blob()),
}))

describe('DocsPhotosPanel flows', () => {
  it('updates document metadata via PATCH', async () => {
    mocks.get.mockResolvedValueOnce([]).mockResolvedValueOnce([])
    mocks.patch.mockResolvedValueOnce({ message: 'ok' })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any

    vm.openDocEditor({ id: 'd1', category: 'c', tags: 't', status: 'reviewed' })
    vm.docEditor.category = 'notes'
    vm.docEditor.tags = 'tag1'
    vm.docEditor.status = 'archived'

    await vm.saveDocEditor()

    expect(mocks.patch).toHaveBeenCalledWith('/api/docs/d1', {
      category: 'notes',
      tags: 'tag1',
      status: 'archived',
    })
  })

  it('deletes photo via DELETE', async () => {
    mocks.get.mockResolvedValueOnce([]).mockResolvedValueOnce([])
    mocks.del.mockResolvedValueOnce({ message: 'deleted' })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    await vm.deletePhoto({ id: 'p1', filename: 'x.png' })
    expect(mocks.del).toHaveBeenCalledWith('/api/photos/p1')
  })
})
