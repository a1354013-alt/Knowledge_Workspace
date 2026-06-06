import { computed, ref } from 'vue'

export type WorkspaceSectionKey =
  | 'health'
  | 'activity'
  | 'search'
  | 'knowledge'
  | 'logbook'
  | 'docsPhotos'
  | 'autotest'
  | 'prompts'
  | 'generator'
  | 'settings'

const activeSection = ref<WorkspaceSectionKey>('health')

export function useWorkspaceNavigation() {
  function navigate(section: WorkspaceSectionKey) {
    activeSection.value = section
  }

  return {
    activeSection: computed(() => activeSection.value),
    navigate,
  }
}

