import { computed, ref } from 'vue'

export type WorkspaceSectionKey =
  | 'health'
  | 'activity'
  | 'search'
  | 'knowledge'
  | 'logbook'
  | 'docsPhotos'
  | 'autotest'
  | 'dataImport'
  | 'prompts'
  | 'generator'
  | 'settings'

const activeSection = ref<WorkspaceSectionKey>('health')
const pendingSearchQuery = ref('')

export function useWorkspaceNavigation() {
  function navigate(section: WorkspaceSectionKey) {
    activeSection.value = section
  }

  function openSearch(query = '') {
    pendingSearchQuery.value = String(query || '').trim()
    activeSection.value = 'search'
  }

  function clearSearchDraft() {
    pendingSearchQuery.value = ''
  }

  return {
    activeSection: computed(() => activeSection.value),
    searchDraft: computed(() => pendingSearchQuery.value),
    openSearch,
    clearSearchDraft,
    navigate,
  }
}
