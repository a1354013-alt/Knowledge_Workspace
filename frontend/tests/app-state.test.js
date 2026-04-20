import { describe, expect, it } from 'vitest'

import { createInitialUiState, createInitialUser } from '../src/app-state.js'

describe('app-state', () => {
  it('initial user state is empty and safe for boot', () => {
    expect(createInitialUser()).toEqual({
      user_id: '',
      role: '',
      display_name: '',
    })
  })

  it('initial UI state does not crash workspace init', () => {
    const state = createInitialUiState()
    expect(state.documents).toEqual([])
    expect(state.photos).toEqual([])
    expect(state.activeSection).toBe('knowledge')
    expect(state.knowledge.sources).toEqual([])
    expect(state.logbook.entries).toEqual([])
  })
})
