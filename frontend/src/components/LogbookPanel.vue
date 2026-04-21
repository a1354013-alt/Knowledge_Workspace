<template>
  <div class="grid">
    <Card>
      <template #title>Engineering troubleshooting logbook</template>
      <template #subtitle>First-class module for problems you solved. Fully searchable via Knowledge Base.</template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button label="Refresh" outlined icon="pi pi-refresh" :loading="loading" @click="loadEntries" />
          </div>
          <DataTable :value="entries" :loading="loading" data-key="id" size="small" responsive-layout="scroll">
            <Column field="title" header="Title" />
            <Column field="tags" header="Tags" />
            <Column field="source_type" header="Source" />
            <Column field="source_ref" header="Source ref" />
            <Column field="status" header="Status" />
            <Column field="updated_at" header="Updated" />
            <Column header="Actions">
              <template #body="slotProps">
                <div class="actions-inline">
                  <Button icon="pi pi-pencil" text severity="secondary" @click="openEditor(slotProps.data)" />
                  <Button icon="pi pi-sitemap" text severity="secondary" @click="selectForRelated(slotProps.data)" />
                  <Button icon="pi pi-check" text severity="success" @click="promoteEntry(slotProps.data)" />
                  <Button icon="pi pi-trash" text severity="danger" @click="deleteEntry(slotProps.data)" />
                </div>
              </template>
            </Column>
          </DataTable>

          <RelatedItemsPanel v-if="selectedRelatedItemId" :item-id="selectedRelatedItemId" />
        </div>
      </template>
    </Card>

    <Card>
      <template #title>Add entry</template>
      <template #content>
        <div class="stack-md">
          <InputText v-model="form.title" placeholder="Title" />
          <Textarea v-model="form.problem" rows="3" placeholder="Problem" />
          <Textarea v-model="form.root_cause" rows="3" placeholder="Root cause" />
          <Textarea v-model="form.solution" rows="4" placeholder="Solution" />
          <InputText v-model="form.tags" placeholder="Tags (comma separated)" />
          <Dropdown v-model="form.status" :options="statusOptions" option-label="label" option-value="value" placeholder="Status" />
          <Dropdown v-model="form.source_type" :options="sourceTypes" option-label="label" option-value="value" placeholder="Source type" />
          <InputText v-model="form.source_ref" placeholder="Source ref (optional, e.g. doc:..., autotest_run:...)" />
          <Chips v-model="form.related_item_ids" separator="," placeholder="Related item IDs (comma-separated, e.g. document:..., photo:..., prompt:...)" />
          <div class="row">
            <Button label="Save" icon="pi pi-save" :loading="saving" @click="saveEntry" />
            <Button label="Reset" outlined severity="secondary" :disabled="saving" @click="resetForm" />
          </div>
        </div>
      </template>
    </Card>
  </div>

  <Dialog v-model:visible="editorVisible" modal header="Edit logbook entry" :style="{ width: 'min(920px, 95vw)' }">
    <div class="stack-md">
      <InputText v-model="editor.title" placeholder="Title" />
      <Textarea v-model="editor.problem" rows="3" placeholder="Problem" />
      <Textarea v-model="editor.root_cause" rows="3" placeholder="Root cause" />
      <Textarea v-model="editor.solution" rows="4" placeholder="Solution" />
      <InputText v-model="editor.tags" placeholder="Tags" />
      <div class="row">
        <Dropdown v-model="editor.status" :options="statusOptions" option-label="label" option-value="value" placeholder="Status" />
        <Dropdown v-model="editor.source_type" :options="sourceTypes" option-label="label" option-value="value" placeholder="Source type" />
      </div>
      <InputText v-model="editor.source_ref" placeholder="Source ref (optional)" />
      <Chips v-model="editor.related_item_ids" separator="," placeholder="Related item IDs (comma-separated)" />

      <div class="row">
        <Dropdown v-model="pickerSelected" :options="pickerOptions" option-label="label" option-value="value" placeholder="Add related item..." class="picker" />
        <Button label="Add" icon="pi pi-plus" outlined :disabled="!pickerSelected" @click="addPickedRelated" />
      </div>

      <div class="row">
        <Button label="Save changes" icon="pi pi-save" :loading="editorSaving" @click="saveEditor" />
        <Button label="Close" outlined severity="secondary" :disabled="editorSaving" @click="editorVisible = false" />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chips from 'primevue/chips'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import { del, get, patch, post } from '../api'
import { useWorkspaceStore } from '../workspace-store'
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
} from '../types'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const entries = ref<LogbookEntryResponse[]>([])
const store = useWorkspaceStore()

const selectedRelatedItemId = ref('')

const editorVisible = ref(false)
const editorSaving = ref(false)
type LogbookEditorModel = LogbookEntryCreateRequest & { id: string }
const editor = ref<LogbookEditorModel>(createBlankEditor())

const pickerSelected = ref('')
const documents = ref<DocumentResponse[]>([])
const photos = ref<PhotoResponse[]>([])
const prompts = ref<SavedPromptResponse[]>([])
const autotestRuns = ref<AutoTestRunListItemResponse[]>([])
const knowledgeEntries = ref<KnowledgeEntryResponse[]>([])
const logbookEntries = ref<LogbookEntryResponse[]>([])

const pickerOptions = computedPickerOptions()

const sourceTypes = [
  { label: 'Manual', value: 'manual' },
  { label: 'Document-derived', value: 'document-derived' },
  { label: 'AutoTest-derived', value: 'autotest-derived' },
]

const statusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Reviewed', value: 'reviewed' },
  { label: 'Verified', value: 'verified' },
  { label: 'Archived', value: 'archived' },
]

const form = ref<LogbookEntryCreateRequest>(createBlankForm())

function createBlankForm(): LogbookEntryCreateRequest {
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
  return { ...createBlankForm(), id: '' }
}

function resetForm() {
  form.value = createBlankForm()
}

async function loadEntries() {
  loading.value = true
  try {
    await store.refreshLogbookEntries({ force: true })
    entries.value = store.state.lists.logbookEntries || []
  } catch (error: unknown) {
    entries.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Load failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
    toast.add({ severity: 'warn', summary: 'Missing fields', detail: 'Title, problem, and solution are required.', life: 3500 })
    return
  }

  saving.value = true
  try {
    await post<MessageResponse, LogbookEntryCreateRequest>('/api/logbook/entries', payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Logbook entry indexed.', life: 3000 })
    resetForm()
    await loadEntries()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Save failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  } finally {
    saving.value = false
  }
}

async function deleteEntry(item: LogbookEntryResponse) {
  if (!window.confirm(`Delete "${item.title}"?`)) {
    return
  }
  try {
    await del<MessageResponse>(`/api/logbook/entries/${item.id}`)
    await loadEntries()
    toast.add({ severity: 'success', summary: 'Deleted', detail: 'Entry removed.', life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Delete failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  }
}

async function promoteEntry(item: LogbookEntryResponse) {
  if (!item?.id) {
    return
  }
  if (!window.confirm(`Promote "${item.title}" to a verified knowledge entry?`)) {
    return
  }
  try {
    const response = await post<PromoteToKnowledgeResponse>(`/api/logbook/entries/${item.id}/promote-to-knowledge`)
    await loadEntries()
    toast.add({ severity: 'success', summary: 'Promoted', detail: `Knowledge entry: ${response.knowledge_entry_id}`, life: 4500 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Promote failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  }
}

onMounted(loadEntries)

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
    // ignore
  }
}

function computedPickerOptions() {
  return computed(() => {
    const docOptions = documents.value.map((doc) => ({
      label: `Document: ${doc.filename}`,
      value: `document:${doc.id}`,
    }))
    const photoOptions = photos.value.map((photo) => ({
      label: `Photo: ${photo.filename}`,
      value: `photo:${photo.id}`,
    }))
    const promptOptions = prompts.value.map((prompt) => ({
      label: `Prompt: ${prompt.title}`,
      value: `prompt:${prompt.id}`,
    }))
    const runOptions = autotestRuns.value.map((run) => ({
      label: `AutoTest: ${run.project_name || run.id}`,
      value: `autotest_run:${run.id}`,
    }))
    const knowledgeOptions = knowledgeEntries.value.map((entry) => ({
      label: `Knowledge: ${entry.title || entry.id}`,
      value: `knowledge:${entry.id}`,
    }))
    const logbookOptions = logbookEntries.value.map((entry) => ({
      label: `Logbook: ${entry.title || entry.id}`,
      value: `logbook:${entry.id}`,
    }))
    return [...docOptions, ...photoOptions, ...runOptions, ...promptOptions, ...knowledgeOptions, ...logbookOptions]
  })
}

function addPickedRelated() {
  const value = String(pickerSelected.value || '').trim()
  if (!value) {
    return
  }
  const existing = new Set((editor.value.related_item_ids || []).map((v) => String(v)))
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
    await patch<MessageResponse, LogbookEntryUpdateRequest>(`/api/logbook/entries/${editor.value.id}`, payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Logbook entry updated.', life: 2500 })
    editorVisible.value = false
    await loadEntries()
    selectedRelatedItemId.value = `logbook:${editor.value.id}`
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Save failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  } finally {
    editorSaving.value = false
  }
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1.35fr 0.65fr;
  gap: 16px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.picker {
  min-width: min(520px, 100%);
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
