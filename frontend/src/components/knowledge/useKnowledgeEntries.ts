import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'

import { patch, post } from '../../api'
import { apiPaths } from '../../api/endpoints'
import { t } from '../../i18n'
import { confirmDanger } from '../../services/confirm'
import { useWorkspaceStore } from '../../workspace-store'
import type {
  AutoTestRunListItemResponse,
  DocumentResponse,
  KnowledgeEntryCreateRequest,
  KnowledgeEntryResponse,
  KnowledgeEntryUpdateRequest,
  LogbookEntryResponse,
  MessageResponse,
  PhotoResponse,
  QARequest,
  QAResponse,
  SavedPromptResponse,
  Source,
} from '../../types'

type KnowledgeEditorModel = KnowledgeEntryCreateRequest & { id: string }

export function createBlankEntry(): KnowledgeEntryCreateRequest {
  return {
    title: '',
    problem: '',
    root_cause: '',
    solution: '',
    tags: '',
    notes: '',
    status: 'draft',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  }
}

function createBlankEditor(): KnowledgeEditorModel {
  return { ...createBlankEntry(), id: '' }
}

export function useKnowledgeEntries() {
  const toast = useToast()
  const store = useWorkspaceStore()

  const question = ref('')
  const asking = ref(false)
  const answer = ref('')
  const sources = ref<Source[]>([])

  const saving = ref(false)
  const entry = ref<KnowledgeEntryCreateRequest>(createBlankEntry())

  const loadingRecent = ref(false)
  const recent = ref<KnowledgeEntryResponse[]>([])
  const recentFilterText = ref('')

  const selectedRelatedItemId = ref('')

  const editorVisible = ref(false)
  const editorSaving = ref(false)
  const editor = ref<KnowledgeEditorModel>(createBlankEditor())

  const pickerSelected = ref('')
  const documents = ref<DocumentResponse[]>([])
  const photos = ref<PhotoResponse[]>([])
  const prompts = ref<SavedPromptResponse[]>([])
  const autotestRuns = ref<AutoTestRunListItemResponse[]>([])
  const knowledgeEntries = ref<KnowledgeEntryResponse[]>([])
  const logbookEntries = ref<LogbookEntryResponse[]>([])

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
    const knowledgeOptions = knowledgeEntries.value.map((knowledgeEntry) => ({
      label: `${t('activity.knowledge')}: ${knowledgeEntry.title || knowledgeEntry.id}`,
      value: `knowledge:${knowledgeEntry.id}`,
    }))
    const logbookOptions = logbookEntries.value.map((logbookEntry) => ({
      label: `${t('activity.logbook')}: ${logbookEntry.title || logbookEntry.id}`,
      value: `logbook:${logbookEntry.id}`,
    }))
    return [...docOptions, ...photoOptions, ...runOptions, ...promptOptions, ...knowledgeOptions, ...logbookOptions]
  })

  const filteredRecent = computed(() => {
    const query = String(recentFilterText.value || '').trim().toLowerCase()
    if (!query) {
      return recent.value
    }
    return recent.value.filter((item) => {
      const haystack = `${item.title || ''} ${item.tags || ''} ${item.status || ''}`.toLowerCase()
      return haystack.includes(query)
    })
  })
  const loadRecentMessage = computed(() => store.state.error.knowledgeEntries || '')
  const showLoadRecentWarning = computed(() => store.state.status.knowledgeEntries === 'error' && recent.value.length > 0)

  function clearResult() {
    answer.value = ''
    sources.value = []
  }

  function resetEntry() {
    entry.value = createBlankEntry()
  }

  async function submitQA() {
    if (!question.value.trim()) {
      toast.add({ severity: 'warn', summary: t('knowledge.questionRequired'), detail: t('knowledge.questionRequiredDetail'), life: 3000 })
      return
    }

    asking.value = true
    try {
      const response = await post<QAResponse, QARequest>(apiPaths.qa.ask, { question: question.value.trim() })
      answer.value = response.answer
      sources.value = response.sources || []
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('knowledge.qaFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    } finally {
      asking.value = false
    }
  }

  async function saveEntry() {
    const trimmedProblem = String(entry.value.problem || '').trim()
    if (!trimmedProblem) {
      toast.add({ severity: 'warn', summary: t('common.validationError'), detail: t('knowledge.problemRequired'), life: 3500 })
      return
    }

    const payload = {
      title: String(entry.value.title || '').trim(),
      problem: trimmedProblem,
      root_cause: String(entry.value.root_cause || '').trim(),
      solution: String(entry.value.solution || '').trim(),
      tags: String(entry.value.tags || '').trim(),
      notes: String(entry.value.notes || '').trim(),
      status: entry.value.status || 'draft',
      source_type: entry.value.source_type || 'manual',
      source_ref: String(entry.value.source_ref || '').trim(),
      related_item_ids: Array.isArray(entry.value.related_item_ids) ? entry.value.related_item_ids : [],
    }
    if (!payload.solution) {
      toast.add({ severity: 'warn', summary: t('common.missingFields'), detail: t('knowledge.solutionRequired'), life: 3500 })
      return
    }

    saving.value = true
    try {
      await post<MessageResponse, KnowledgeEntryCreateRequest>(apiPaths.knowledge.list, payload)
      toast.add({ severity: 'success', summary: t('common.saved'), detail: t('knowledge.noteIndexed'), life: 3000 })
      resetEntry()
      await loadRecent()
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    } finally {
      saving.value = false
    }
  }

  async function loadRecent() {
    loadingRecent.value = true
    try {
      await store.refreshKnowledgeEntries({ force: true })
      recent.value = store.state.lists.knowledgeEntries || []
    } catch (error: unknown) {
      recent.value = store.state.lists.knowledgeEntries || []
      const apiError = error as { message?: string }
      toast.add({
        severity: recent.value.length ? 'warn' : 'error',
        summary: t('workspace.knowledgeReloadFailed'),
        detail: apiError?.message || store.state.error.knowledgeEntries || t('common.requestFailed'),
        life: 3500,
      })
    } finally {
      loadingRecent.value = false
    }
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
      // Picker options are a convenience; leave the editor usable without them.
    }
  }

  function selectForRelated(item: KnowledgeEntryResponse) {
    if (!item?.id) {
      return
    }
    selectedRelatedItemId.value = `knowledge:${item.id}`
  }

  function openEditor(item: KnowledgeEntryResponse) {
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
      notes: item.notes || '',
      status: item.status || 'draft',
      source_type: item.source_type || 'manual',
      source_ref: item.source_ref || '',
      related_item_ids: Array.isArray(item.related_item_ids) ? [...item.related_item_ids] : [],
    }
    pickerSelected.value = ''
    editorVisible.value = true
    loadPickers()
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
    const payload: KnowledgeEntryUpdateRequest = {
      title: String(editor.value.title || '').trim(),
      problem: String(editor.value.problem || '').trim(),
      root_cause: String(editor.value.root_cause || '').trim(),
      solution: String(editor.value.solution || '').trim(),
      tags: String(editor.value.tags || '').trim(),
      notes: String(editor.value.notes || '').trim(),
      status: editor.value.status || 'draft',
      source_type: editor.value.source_type || 'manual',
      source_ref: String(editor.value.source_ref || '').trim(),
      related_item_ids: Array.isArray(editor.value.related_item_ids) ? editor.value.related_item_ids : [],
    }
    editorSaving.value = true
    try {
      await patch<MessageResponse, KnowledgeEntryUpdateRequest>(apiPaths.knowledge.detail(editor.value.id), payload)
      toast.add({ severity: 'success', summary: t('common.saved'), detail: t('knowledge.entryUpdated'), life: 2500 })
      editorVisible.value = false
      await loadRecent()
      selectedRelatedItemId.value = `knowledge:${editor.value.id}`
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    } finally {
      editorSaving.value = false
    }
  }

  async function archiveEntry(item: KnowledgeEntryResponse) {
    if (!item?.id) {
      return
    }
    if (
      !(await confirmDanger({
        header: t('knowledge.archiveEntry'),
        message: t('knowledge.archiveEntryMessage', { title: item.title || t('knowledge.thisEntry') }),
        acceptLabel: t('docsPhotos.archive'),
      }))
    ) {
      return
    }
    try {
      await patch<MessageResponse, KnowledgeEntryUpdateRequest>(apiPaths.knowledge.detail(item.id), { status: 'archived' })
      toast.add({ severity: 'success', summary: t('common.archived'), detail: t('knowledge.entryArchived'), life: 2200 })
      await loadRecent()
      if (selectedRelatedItemId.value === `knowledge:${item.id}`) {
        selectedRelatedItemId.value = ''
      }
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      toast.add({ severity: 'error', summary: t('common.archiveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
    }
  }

  onMounted(loadRecent)

  return {
    answer,
    archiveEntry,
    asking,
    clearResult,
    editor,
    editorSaving,
    editorVisible,
    entry,
    filteredRecent,
    loadRecent,
    loadRecentMessage,
    loadingRecent,
    openEditor,
    pickerOptions,
    pickerSelected,
    question,
    recentFilterText,
    resetEntry,
    saveEditor,
    saveEntry,
    saving,
    selectForRelated,
    selectedRelatedItemId,
    showLoadRecentWarning,
    sourceTypes,
    sources,
    statusOptions,
    submitQA,
    addPickedRelated,
  }
}
