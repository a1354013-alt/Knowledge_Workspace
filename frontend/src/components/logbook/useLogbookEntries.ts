import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'

import { del, patch, post } from '../../api'
import { apiPaths } from '../../api/endpoints'
import { t } from '../../i18n'
import { confirmDanger } from '../../services/confirm'
import { useWorkspaceStore } from '../../workspace-store'
import type {
  AutoTestRunListItemResponse,
  DocumentResponse,
  KnowledgeEntryResponse,
  LogbookEntryCreateRequest,
  LogbookEntryResponse,
  LogbookEntryUpdateRequest,
  MessageResponse,
  PhotoResponse,
  PromoteToKnowledgeResponse,
  SavedPromptResponse,
} from '../../types'

export type LogbookEditorModel = LogbookEntryCreateRequest & { id: string }

export function createBlankLogbookForm(): LogbookEntryCreateRequest {
  return {
    title: '',
    problem: '',
    root_cause: '',
    solution: '',
    tags: '',
    status: 'draft',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  }
}

function createBlankEditor(): LogbookEditorModel {
  return { ...createBlankLogbookForm(), id: '' }
}

export function useLogbookEntries() {
  const toast = useToast()
  const store = useWorkspaceStore()

  const loading = ref(false)
  const saving = ref(false)
  const entries = ref<LogbookEntryResponse[]>([])
  const selectedRelatedItemId = ref('')

  const editorVisible = ref(false)
  const editorSaving = ref(false)
  const editor = ref<LogbookEditorModel>(createBlankEditor())

  const pickerSelected = ref('')
  const documents = ref<DocumentResponse[]>([])
  const photos = ref<PhotoResponse[]>([])
  const prompts = ref<SavedPromptResponse[]>([])
  const autotestRuns = ref<AutoTestRunListItemResponse[]>([])
  const knowledgeEntries = ref<KnowledgeEntryResponse[]>([])
  const logbookEntries = ref<LogbookEntryResponse[]>([])

  const pickerOptions = computed(() => {
    const docOptions = documents.value.map((doc) => ({
      label: `${t('activity.document')}: ${doc.filename}`,
      value: `document:${doc.id}`,
    }))
    const photoOptions = photos.value.map((photo) => ({
      label: `${t('activity.photo')}: ${photo.filename}`,
      value: `photo:${photo.id}`,
    }))
    const promptOptions = prompts.value.map((prompt) => ({
      label: `${t('activity.prompt')}: ${prompt.title}`,
      value: `prompt:${prompt.id}`,
    }))
    const runOptions = autotestRuns.value.map((run) => ({
      label: `AutoTest: ${run.project_name || run.id}`,
      value: `autotest_run:${run.id}`,
    }))
    const knowledgeOptions = knowledgeEntries.value.map((entry) => ({
      label: `${t('activity.knowledge')}: ${entry.title || entry.id}`,
      value: `knowledge:${entry.id}`,
    }))
    const logbookOptions = logbookEntries.value.map((entry) => ({
      label: `${t('activity.logbook')}: ${entry.title || entry.id}`,
      value: `logbook:${entry.id}`,
    }))
    return [...docOptions, ...photoOptions, ...runOptions, ...promptOptions, ...knowledgeOptions, ...logbookOptions]
  })

  const sourceTypes = computed(() => [
    { label: t('knowledge.sourceManual'), value: 'manual' },
    { label: t('knowledge.sourceDocumentDerived'), value: 'document-derived' },
    { label: t('knowledge.sourceAutotestDerived'), value: 'autotest-derived' },
  ])

  const statusOptions = computed(() => [
    { label: t('common.draft'), value: 'draft' },
    { label: t('common.reviewed'), value: 'reviewed' },
    { label: t('common.verified'), value: 'verified' },
    { label: t('common.archivedStatus'), value: 'archived' },
  ])

  const form = ref<LogbookEntryCreateRequest>(createBlankLogbookForm())
  const loadMessage = computed(() => store.state.error.logbookEntries || '')
  const showReloadWarning = computed(() => store.state.status.logbookEntries === 'error' && entries.value.length > 0)

  function resetForm() {
    form.value = createBlankLogbookForm()
  }

  async function loadEntries() {
    loading.value = true
    try {
      await store.refreshLogbookEntries({ force: true })
      entries.value = store.state.lists.logbookEntries || []
    } catch (error: unknown) {
      entries.value = store.state.lists.logbookEntries || []
      const apiError = error as { message?: string }
      toast.add({
        severity: entries.value.length ? 'warn' : 'error',
        summary: t('workspace.logbookReloadFailed'),
        detail: apiError?.message || store.state.error.logbookEntries || t('common.requestFailed'),
        life: 3500,
      })
    } finally {
      loading.value = false
    }
  }

  async function saveEntry() {
    const payload: LogbookEntryCreateRequest = {
      title: String(form.value.title || '').trim(),
      problem: String(form.value.problem || '').trim(),
      root_cause: String(form.value.root_cause || '').trim(),
      solution: String(form.value.solution || '').trim(),
      tags: String(form.value.tags || '').trim(),
      source_type: form.value.source_type || 'manual',
      status: form.value.status || 'draft',
      source_ref: String(form.value.source_ref || '').trim(),
      related_item_ids: Array.isArray(form.value.related_item_ids) ? form.value.related_item_ids : [],
    }
    if (!payload.title || !payload.problem || !payload.solution) {
      toast.add({ severity: 'warn', summary: t('common.missingFields'), detail: t('logbook.requiredFields'), life: 3500 })
      return
    }

    saving.value = true
    try {
      await post<MessageResponse, LogbookEntryCreateRequest>(apiPaths.logbook.list, payload)
      toast.add({ severity: 'success', summary: t('common.saved'), detail: t('logbook.entryIndexed'), life: 3000 })
      resetForm()
      await loadEntries()
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    } finally {
      saving.value = false
    }
  }

  async function deleteEntry(item: LogbookEntryResponse) {
    if (
      !(await confirmDanger({
        header: t('logbook.deleteEntry'),
        message: t('logbook.deleteEntryMessage', { title: item.title }),
        acceptLabel: t('prompts.deleteAccept'),
      }))
    ) {
      return
    }
    try {
      await del<MessageResponse>(apiPaths.logbook.detail(item.id))
      await loadEntries()
      toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('logbook.entryRemoved'), life: 3000 })
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.deleteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    }
  }

  async function promoteEntry(item: LogbookEntryResponse) {
    if (!item?.id) {
      return
    }
    if (
      !(await confirmDanger({
        header: t('logbook.promoteEntry'),
        message: t('logbook.promoteEntryMessage', { title: item.title }),
        acceptLabel: t('logbook.promote'),
      }))
    ) {
      return
    }
    try {
      const response = await post<PromoteToKnowledgeResponse>(apiPaths.logbook.promote(item.id))
      await loadEntries()
      toast.add({ severity: 'success', summary: t('logbook.promoted'), detail: t('logbook.promotedDetail', { id: response.knowledge_entry_id }), life: 4500 })
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.promoteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    }
  }

  function selectForRelated(item: LogbookEntryResponse) {
    if (!item?.id) {
      return
    }
    selectedRelatedItemId.value = `logbook:${item.id}`
  }

  function openEditor(item: LogbookEntryResponse) {
    if (!item?.id) {
      return
    }
    editor.value = {
      id: item.id,
      title: item.title || '',
      problem: item.problem || '',
      root_cause: item.root_cause || '',
      solution: item.solution || '',
      tags: item.tags || '',
      status: item.status || 'draft',
      source_type: item.source_type || 'manual',
      source_ref: item.source_ref || '',
      related_item_ids: Array.isArray(item.related_item_ids) ? [...item.related_item_ids] : [],
    }
    pickerSelected.value = ''
    editorVisible.value = true
    loadPickers()
  }

  async function loadPickers() {
    try {
      await store.refreshAll()
      documents.value = store.state.lists.documents || []
      photos.value = store.state.lists.photos || []
      autotestRuns.value = store.state.lists.autotestRuns || []
      prompts.value = store.state.lists.prompts || []
      knowledgeEntries.value = store.state.lists.knowledgeEntries || []
      logbookEntries.value = store.state.lists.logbookEntries || []
    } catch {
      // Picker options are a convenience; keep the editor usable if they fail.
    }
  }

  function addPickedRelated() {
    const value = String(pickerSelected.value || '').trim()
    if (!value) {
      return
    }
    const existing = new Set((editor.value.related_item_ids || []).map((item) => String(item)))
    if (!existing.has(value)) {
      editor.value.related_item_ids = [...(editor.value.related_item_ids || []), value]
    }
    pickerSelected.value = ''
  }

  async function saveEditor() {
    if (!editor.value?.id) {
      return
    }
    const payload: LogbookEntryUpdateRequest = {
      title: String(editor.value.title || '').trim(),
      problem: String(editor.value.problem || '').trim(),
      root_cause: String(editor.value.root_cause || '').trim(),
      solution: String(editor.value.solution || '').trim(),
      tags: String(editor.value.tags || '').trim(),
      status: editor.value.status || 'draft',
      source_type: editor.value.source_type || 'manual',
      source_ref: String(editor.value.source_ref || '').trim(),
      related_item_ids: Array.isArray(editor.value.related_item_ids) ? editor.value.related_item_ids : [],
    }
    editorSaving.value = true
    try {
      await patch<MessageResponse, LogbookEntryUpdateRequest>(apiPaths.logbook.detail(editor.value.id), payload)
      toast.add({ severity: 'success', summary: t('common.saved'), detail: t('logbook.entryUpdated'), life: 2500 })
      editorVisible.value = false
      await loadEntries()
      selectedRelatedItemId.value = `logbook:${editor.value.id}`
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    } finally {
      editorSaving.value = false
    }
  }

  onMounted(loadEntries)

  return {
    addPickedRelated,
    deleteEntry,
    editor,
    editorSaving,
    editorVisible,
    entries,
    form,
    loadEntries,
    loadMessage,
    loading,
    openEditor,
    pickerOptions,
    pickerSelected,
    promoteEntry,
    resetForm,
    saveEditor,
    saveEntry,
    saving,
    selectForRelated,
    selectedRelatedItemId,
    showReloadWarning,
    sourceTypes,
    statusOptions,
  }
}
