import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AutoTestStatusBadge from '../src/components/autotest/AutoTestStatusBadge.vue'
import AutoTestTimeline from '../src/components/autotest/AutoTestTimeline.vue'

describe('AutoTest extracted components', () => {
  it('renders status badge classes from backend run statuses', () => {
    const wrapper = mount(AutoTestStatusBadge, {
      props: { status: 'failed' },
    })

    expect(wrapper.text()).toBe('failed')
    expect(wrapper.classes()).toContain('badge-bad')
  })

  it('renders backend timeline events and falls back for sparse runs', () => {
    const wrapper = mount(AutoTestTimeline, {
      props: {
        run: {
          id: 'run-1',
          source_type: 'zip_upload',
          source_ref: 'demo.zip',
          execution_mode: 'simulated',
          project_type_detected: 'node',
          working_directory: '.',
          project_name: 'Demo',
          project_type: 'node',
          status: 'failed',
          summary: 'Acceptance failed',
          suggestion: '',
          prompt_output: '',
          failed_reason: 'timeout after 300s',
          problem_entry_id: '',
          solution_entry_id: '',
          created_at: '2026-05-08T00:00:00Z',
          steps: [],
          timeline: [],
        },
      },
    })

    expect(wrapper.text()).toContain('Run timeline')
    expect(wrapper.text()).toContain('Uploaded')
    expect(wrapper.text()).toContain('Generated report')
    expect(wrapper.text()).toContain('timeout after 300s')
  })
})
