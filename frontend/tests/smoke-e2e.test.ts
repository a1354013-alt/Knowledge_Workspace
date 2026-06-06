import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import App from '../src/App.vue'
import GlobalSearchPanel from '../src/components/GlobalSearchPanel.vue'
import SettingsPanel from '../src/components/SettingsPanel.vue'
import { apiPaths } from '../src/api/endpoints'
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
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('../src/auth', () => ({
  AUTH_STORAGE_KEY: 'kw-token',
  clearToken: vi.fn(),
  getToken: vi.fn(() => authState.token),
  notifyUnauthorized: vi.fn(),
  onUnauthorized: vi.fn(() => () => undefined),
  restoreToken: vi.fn(() => authState.token),
  setToken: vi.fn((token: string) => {
    authState.token = token
  }),
}))

const authState = vi.hoisted(() => ({
  token: '',
}))

async function flushUi() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('frontend smoke flows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authState.token = ''
  })

  it('renders the login page and signs in through the shared API client', async () => {
    apiMocks.post.mockImplementation(async (path: string) => {
      if (path === apiPaths.auth.login) {
        return { access_token: 'token-1', token_type: 'bearer' }
      }
      throw new Error(`Unexpected POST ${path}`)
    })
    apiMocks.get.mockImplementation(async (path: string) => {
      if (path === apiPaths.auth.me) {
        return { user_id: 'owner', role: 'owner', display_name: 'Owner' }
      }
      throw new Error(`Unexpected GET ${path}`)
    })

    const wrapper = mount(App, { global: { stubs: PrimeStubs } })
    expect(wrapper.text()).toContain('工程師個人 AI 知識工作台')

    const vm = wrapper.vm as unknown as { loginForm: { user_id: string; password: string }; login: () => Promise<void> }
    vm.loginForm.user_id = 'owner'
    vm.loginForm.password = 'OwnerPass123!'
    await vm.login()
    await flushUi()

    expect(apiMocks.post).toHaveBeenCalled()
    expect(apiMocks.get).toHaveBeenCalled()
  })

  it('renders system status/dashboard data', async () => {
    apiMocks.get.mockImplementation(async (path: string) => {
      if (path === apiPaths.dashboard.health) {
        return {
          knowledge: { total: 0, by_status: { draft: 0, reviewed: 0, verified: 0, archived: 0 } },
          logbook: { total: 0, with_solution: 0, promoted_to_knowledge: 0, resolution_rate: 0 },
          autotest: { total_runs: 0, passed: 0, failed: 0, pass_rate: 0, recent_runs: [] },
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
        }
      }
      throw new Error(`Unexpected GET ${path}`)
    })

    const { default: ProjectHealthDashboard } = await import('../src/components/ProjectHealthDashboard.vue')
    const wrapper = mount(ProjectHealthDashboard, { global: { stubs: PrimeStubs } })
    await flushUi()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('AutoTest 次數')
  })

  it('handles an empty search result without crashing', async () => {
    apiMocks.get.mockImplementation(async (path: string) => {
      if (path.startsWith(apiPaths.search.resolve)) {
        return { items: [] }
      }
      throw new Error(`Unexpected GET ${path}`)
    })
    const wrapper = mount(GlobalSearchPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as unknown as { query: string; runSearch: () => Promise<void> }
    vm.query = 'no-match'
    await vm.runSearch()
    expect(apiMocks.get).toHaveBeenCalled()
  })

  it('loads settings including the index provider status', async () => {
    apiMocks.get.mockImplementation(async (path: string) => {
      if (path === apiPaths.settings.llm) {
        return {
          primary_provider: 'ollama',
          active_provider: 'none',
          model: 'llama3.1',
          base_url: 'http://localhost:11434',
          primary_healthy: false,
          fallback_enabled: true,
          llm_ready_for_generation: false,
          error_message: '',
        }
      }
      if (path === apiPaths.settings.templatesMeta) {
        return { templates: [] }
      }
      if (path === apiPaths.settings.ocr) {
        return { enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' }
      }
      if (path === apiPaths.index.status) {
        return {
          provider: {
            configured_provider: 'demo-hash',
            active_provider: 'demo-fallback',
            status: 'degraded',
            demo_mode: true,
            semantic_search_ready: false,
            message: 'Deterministic demo/fallback embeddings are active.',
            details: [],
          },
          summary: {
            document: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 2 },
            knowledge: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            logbook: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            photo: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            prompt: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 1 },
          },
          failed_items: [],
        }
      }
      throw new Error(`Unexpected GET ${path}`)
    })

    const wrapper = mount(SettingsPanel, { global: { stubs: PrimeStubs } })
    await flushUi()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Index health')
    expect(wrapper.text()).toContain('demo / fallback')
    expect(wrapper.text()).toContain('Excluded')
  })
})
