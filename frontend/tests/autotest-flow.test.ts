import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import AutoTestPanel from '../src/components/AutoTestPanel.vue'
import { PrimeStubs } from './stubs'

const toastAdd = vi.fn()

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAdd }),
}))

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

const autotestMocks = vi.hoisted(() => ({
  startAutoTest: vi.fn(),
  getAutoTestRun: vi.fn(),
  promoteAutoTestProblem: vi.fn(),
  downloadAutoTestReport: vi.fn(),
}))
const clipboardWrite = vi.fn()

vi.mock('../src/api', () => ({
  get: apiMocks.get,
  post: vi.fn(),
}))

vi.mock('../src/autotest-api', () => autotestMocks)

describe('AutoTestPanel flows', () => {
  beforeEach(() => {
    toastAdd.mockReset()
    apiMocks.get.mockReset()
    autotestMocks.startAutoTest.mockReset()
    autotestMocks.getAutoTestRun.mockReset()
    autotestMocks.promoteAutoTestProblem.mockReset()
    autotestMocks.downloadAutoTestReport.mockReset()
    apiMocks.get.mockResolvedValue([])
    clipboardWrite.mockReset()
    clipboardWrite.mockResolvedValue(undefined)
    vi.stubGlobal('navigator', {
      clipboard: {
        writeText: clipboardWrite,
      },
    })
  })

  it('runs autotest upload through the shared API client helper', async () => {
    autotestMocks.startAutoTest.mockResolvedValueOnce({ id: 'r1', status: 'passed', steps: [] })

    const wrapper = mount(AutoTestPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.selectedZip = new File(['zip'], 'proj.zip', { type: 'application/zip' })

    await vm.runAutoTest()

    expect(autotestMocks.startAutoTest).toHaveBeenCalledTimes(1)
    expect(autotestMocks.downloadAutoTestReport).not.toHaveBeenCalled()
  })

  it('shows a specific timeout message when an autotest run exceeds the request timeout', async () => {
    autotestMocks.startAutoTest.mockRejectedValueOnce({
      message: 'Request timed out.',
      detail: 'timeout of 300000ms exceeded',
    })

    const wrapper = mount(AutoTestPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.selectedZip = new File(['zip'], 'proj.zip', { type: 'application/zip' })

    await vm.runAutoTest()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        summary: 'Run failed',
        detail: expect.stringContaining('AutoTest execution timed out'),
      })
    )
    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: expect.stringContaining('AUTOTEST_TIMEOUT_SECONDS'),
      })
    )
  })

  it('shows export actions and disables them for unfinished runs', async () => {
    const wrapper = mount(AutoTestPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.selectedRun = {
      id: 'run-pending',
      source_type: 'upload',
      source_ref: 'demo.zip',
      execution_mode: 'simulated',
      project_type_detected: 'node',
      working_directory: '.',
      project_name: 'Demo',
      project_type: 'node',
      status: 'running',
      summary: 'Running',
      suggestion: '',
      prompt_output: '',
      failed_reason: '',
      problem_entry_id: '',
      solution_entry_id: '',
      created_at: '2026-05-08T00:00:00Z',
      steps: [],
      timeline: [],
    }
    await vm.$nextTick()

    const buttons = wrapper.findAll('button')
    expect(buttons.some((button) => button.text().includes('Download Markdown Report'))).toBe(true)
    expect(buttons.some((button) => button.text().includes('Download HTML Report'))).toBe(true)
    expect(buttons.some((button) => button.text().includes('Copy AI Fix Prompt'))).toBe(true)

    const exportButtons = buttons.filter((button) => button.text().includes('Download'))
    expect(exportButtons.every((button) => (button.element as HTMLButtonElement).disabled)).toBe(true)
    expect(wrapper.text()).toContain('Reports unlock after the run reaches passed or failed.')
  })

  it('downloads reports and copies the AI fix prompt for completed runs', async () => {
    const wrapper = mount(AutoTestPanel, { global: { stubs: PrimeStubs } })
    const vm = wrapper.vm as any
    vm.selectedRun = {
      id: 'run-failed',
      source_type: 'upload',
      source_ref: 'demo.zip',
      execution_mode: 'real',
      project_type_detected: 'python',
      working_directory: '.',
      project_name: 'Demo',
      project_type: 'python',
      status: 'failed',
      summary: 'Failed summary',
      suggestion: 'Fix the failing test',
      prompt_output: 'Re-run pytest after the fix',
      failed_reason: 'Boom',
      problem_entry_id: 'log-1',
      solution_entry_id: '',
      created_at: '2026-05-08T00:00:00Z',
      steps: [],
      timeline: [],
    }
    await vm.$nextTick()

    await vm.downloadReport('md')
    await vm.downloadReport('html')
    await vm.copyAiFixPrompt()

    expect(autotestMocks.downloadAutoTestReport).toHaveBeenNthCalledWith(1, 'run-failed', 'md')
    expect(autotestMocks.downloadAutoTestReport).toHaveBeenNthCalledWith(2, 'run-failed', 'html')
    expect(clipboardWrite).toHaveBeenCalledWith('Fix the failing test\n\nRe-run pytest after the fix')
    expect(wrapper.text()).toContain('Real mode executes commands from uploaded projects. Use only with trusted local projects.')
  })
})
