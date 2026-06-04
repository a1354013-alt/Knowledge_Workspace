import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import DocsPhotosPanel from '../src/components/DocsPhotosPanel.vue'
import { setLocale } from '../src/i18n'
import { PrimeStubs } from './stubs'

const toastAdd = vi.fn()

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAdd }),
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
    setLocale('en')
    toastAdd.mockReset()
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
    setLocale('en')
    toastAdd.mockReset()
    mocks.get.mockResolvedValueOnce([]).mockResolvedValueOnce([])
    mocks.del.mockResolvedValueOnce({ message: 'deleted' })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    await vm.deletePhoto({ id: 'p1', filename: 'x.png' })
    expect(mocks.del).toHaveBeenCalledWith('/api/photos/p1')
  })

  it('shows a warning toast when document index rebuild reports failures', async () => {
    setLocale('en')
    toastAdd.mockReset()
    mocks.get.mockResolvedValue([])
    mocks.post.mockResolvedValueOnce({
      message: 'Failed to rebuild document:d1.',
      rebuilt: 0,
      failed: 1,
      provider: { active_provider: 'demo-fallback' },
      items: [{ item_id: 'd1', item_type: 'document', title: 'doc.txt', status: 'failed', error: 'vector offline' }],
    })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const rebuildDocumentIndex = Reflect.get(wrapper.vm, 'rebuildDocumentIndex') as
      | ((doc: { id: string }) => Promise<void>)
      | undefined
    expect(rebuildDocumentIndex).toBeTypeOf('function')
    if (!rebuildDocumentIndex) {
      throw new Error('rebuildDocumentIndex should be exposed on the component instance')
    }
    await rebuildDocumentIndex({ id: 'd1' })

    expect(mocks.post).toHaveBeenCalledWith('/api/index/rebuild/document/d1')
    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'warn',
        summary: 'Index rebuild needs attention',
      }),
    )
  })

  it('shows a success toast when document index rebuild fully succeeds', async () => {
    setLocale('en')
    toastAdd.mockReset()
    mocks.get.mockResolvedValue([])
    mocks.post.mockResolvedValueOnce({
      message: 'Rebuilt document:d1.',
      rebuilt: 1,
      failed: 0,
      provider: { active_provider: 'demo-fallback' },
      items: [{ item_id: 'd1', item_type: 'document', title: 'doc.txt', status: 'indexed', error: '' }],
    })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const rebuildDocumentIndex = Reflect.get(wrapper.vm, 'rebuildDocumentIndex') as
      | ((doc: { id: string }) => Promise<void>)
      | undefined
    expect(rebuildDocumentIndex).toBeTypeOf('function')
    if (!rebuildDocumentIndex) {
      throw new Error('rebuildDocumentIndex should be exposed on the component instance')
    }
    await rebuildDocumentIndex({ id: 'd1' })

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'Index rebuilt',
      }),
    )
  })

  it('shows degraded upload as a warning instead of an error', async () => {
    setLocale('en')
    toastAdd.mockReset()
    mocks.get.mockResolvedValue([])
    mocks.post.mockResolvedValueOnce({
      id: 'd1',
      filename: 'note.txt',
      category: '',
      tags: '',
      status: 'reviewed',
      uploaded_at: 'now',
      updated_at: 'now',
      file_size: 10,
      index_status: 'unavailable',
      index_error: 'Vector index unavailable',
      message: 'Document uploaded. Semantic indexing is unavailable right now, so full-text search is available.',
      user_message: 'Document uploaded. Semantic indexing is unavailable right now, so full-text search is available.',
      upload_status: 'success',
      full_text_index_status: 'indexed',
      vector_index_status: 'degraded',
      degraded_reason: 'Vector index unavailable',
    })

    const wrapper = mount(DocsPhotosPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.selectedDoc = new File(['hello'], 'note.txt', { type: 'text/plain' })
    await vm.uploadDoc()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'warn',
        summary: 'Uploaded with full-text fallback',
      }),
    )
  })
})
