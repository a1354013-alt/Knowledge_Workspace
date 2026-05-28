import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import SettingsPanel from '../src/components/SettingsPanel.vue'
import { PrimeStubs } from './stubs'

const toastAdd = vi.fn()

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAdd }),
}))

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('../src/api', () => ({
  get: apiMocks.get,
  post: apiMocks.post,
}))

function primeIndexStatus() {
  return {
    provider: {
      configured_provider: 'demo',
      active_provider: 'demo-fallback',
      status: 'degraded',
      demo_mode: true,
      semantic_search_ready: false,
      message: '',
      details: [],
    },
    summary: {
      document: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
      knowledge: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
      logbook: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
      photo: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
      prompt: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
    },
    failed_items: [],
  }
}

describe('SettingsPanel index rebuild toasts', () => {
  it('shows a warning toast when rebuild-all reports failures', async () => {
    toastAdd.mockReset()
    apiMocks.get
      .mockResolvedValueOnce({
        primary_provider: 'ollama',
        active_provider: 'none',
        model: '',
        base_url: '',
        primary_healthy: false,
        fallback_enabled: true,
        llm_ready_for_generation: false,
        error_message: '',
      })
      .mockResolvedValueOnce({ templates: [] })
      .mockResolvedValueOnce({ enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' })
      .mockResolvedValueOnce(primeIndexStatus())
      .mockResolvedValueOnce(primeIndexStatus())
    apiMocks.post.mockResolvedValueOnce({
      message: 'Index rebuild completed with failures: rebuilt 3 item(s); 1 failed.',
      rebuilt: 3,
      failed: 1,
      provider: { active_provider: 'demo-fallback' },
      items: [],
    })

    const wrapper = mount(SettingsPanel, { global: { stubs: PrimeStubs } })
    const rebuildAllIndexes = Reflect.get(wrapper.vm, 'rebuildAllIndexes') as (() => Promise<void>) | undefined
    expect(rebuildAllIndexes).toBeTypeOf('function')
    if (!rebuildAllIndexes) {
      throw new Error('rebuildAllIndexes should be exposed on the component instance')
    }
    await rebuildAllIndexes()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'warn',
        summary: 'Index rebuild needs attention',
      }),
    )
  })

  it('shows a success toast only when rebuild-all has no failures', async () => {
    toastAdd.mockReset()
    apiMocks.get
      .mockResolvedValueOnce({
        primary_provider: 'ollama',
        active_provider: 'none',
        model: '',
        base_url: '',
        primary_healthy: false,
        fallback_enabled: true,
        llm_ready_for_generation: false,
        error_message: '',
      })
      .mockResolvedValueOnce({ templates: [] })
      .mockResolvedValueOnce({ enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' })
      .mockResolvedValueOnce(primeIndexStatus())
      .mockResolvedValueOnce(primeIndexStatus())
    apiMocks.post.mockResolvedValueOnce({
      message: 'Rebuilt 4 item(s); 0 failed.',
      rebuilt: 4,
      failed: 0,
      provider: { active_provider: 'demo-fallback' },
      items: [],
    })

    const wrapper = mount(SettingsPanel, { global: { stubs: PrimeStubs } })
    const rebuildAllIndexes = Reflect.get(wrapper.vm, 'rebuildAllIndexes') as (() => Promise<void>) | undefined
    expect(rebuildAllIndexes).toBeTypeOf('function')
    if (!rebuildAllIndexes) {
      throw new Error('rebuildAllIndexes should be exposed on the component instance')
    }
    await rebuildAllIndexes()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'Index rebuild finished',
      }),
    )
  })
})
