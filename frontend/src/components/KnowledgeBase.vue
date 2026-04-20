<template>
  <div class="grid">
    <Card>
      <template #title>Ask your knowledge</template>
      <template #subtitle>Search across your documents, knowledge notes, logbook entries, and image metadata.</template>
      <template #content>
        <div class="stack-md">
          <Textarea v-model="question" rows="5" placeholder="e.g. Delphi CRLF 問題怎麼處理？Vue build fail 之前怎麼修？" />
          <div class="row">
            <Button label="Ask" icon="pi pi-send" :loading="asking" @click="submitQA" />
            <Button label="Clear" outlined severity="secondary" :disabled="asking" @click="clearResult" />
          </div>

          <div v-if="answer" class="result-box">
            <h3>Answer</h3>
            <p class="answer">{{ answer }}</p>
            <div v-if="sources.length" class="stack-sm">
              <h4>Sources</h4>
              <article v-for="(source, index) in sources" :key="index" class="source-card">
                <strong>{{ source.title }}</strong>
                <p class="muted">{{ source.source_type }} · {{ source.location || '-' }}</p>
                <p class="snippet">{{ source.snippet }}</p>
              </article>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>Quick add (Knowledge note)</template>
      <template #subtitle>Manually capture a problem / root cause / solution so it becomes searchable.</template>
      <template #content>
        <div class="stack-md">
          <InputText v-model="entry.title" placeholder="Title (short)" />
          <Textarea v-model="entry.problem" rows="3" placeholder="Problem" />
          <Textarea v-model="entry.root_cause" rows="3" placeholder="Root cause" />
          <Textarea v-model="entry.solution" rows="4" placeholder="Solution (steps, commands, links)" />
          <InputText v-model="entry.tags" placeholder="Tags (comma separated)" />
          <Textarea v-model="entry.notes" rows="2" placeholder="Notes (optional)" />
          <div class="row">
            <Dropdown v-model="entry.status" :options="statusOptions" option-label="label" option-value="value" placeholder="Status" />
            <Dropdown v-model="entry.source_type" :options="sourceTypes" option-label="label" option-value="value" placeholder="Source type" />
          </div>
          <InputText v-model="entry.source_ref" placeholder="Source ref (optional, e.g. document:..., autotest_run:...)" />
          <Chips v-model="entry.related_item_ids" separator="," placeholder="Related item IDs (comma-separated, e.g. document:..., photo:..., prompt:...)" />
          <div class="row">
            <Button label="Save" icon="pi pi-save" :loading="saving" @click="saveEntry" />
            <Button label="Reset" outlined severity="secondary" :disabled="saving" @click="resetEntry" />
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>Recent notes</template>
      <template #content>
        <div class="stack-md">
          <Button label="Refresh" outlined icon="pi pi-refresh" :loading="loadingRecent" @click="loadRecent" />
          <InputText v-model="recentFilterText" placeholder="Filter recent (title/tags/status)" />
          <DataTable :value="filteredRecent" :loading="loadingRecent" data-key="id" size="small" responsive-layout="scroll">
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
                  <Button icon="pi pi-archive" text severity="secondary" @click="archiveEntry(slotProps.data)" />
                </div>
              </template>
            </Column>
          </DataTable>

          <RelatedItemsPanel v-if="selectedRelatedItemId" :item-id="selectedRelatedItemId" />
        </div>
      </template>
    </Card>
  </div>

  <Dialog v-model:visible="editorVisible" modal header="Edit knowledge entry" :style="{ width: 'min(920px, 95vw)' }">
    <div class="stack-md">
      <InputText v-model="editor.title" placeholder="Title" />
      <Textarea v-model="editor.problem" rows="3" placeholder="Problem" />
      <Textarea v-model="editor.root_cause" rows="3" placeholder="Root cause" />
      <Textarea v-model="editor.solution" rows="4" placeholder="Solution" />
      <InputText v-model="editor.tags" placeholder="Tags" />
      <Textarea v-model="editor.notes" rows="2" placeholder="Notes" />
      <div class="row">
        <Dropdown v-model="editor.status" :options="statusOptions" option-label="label" option-value="value" placeholder="Status" />
        <Dropdown v-model="editor.source_type" :options="sourceTypes" option-label="label" option-value="value" placeholder="Source type" />
      </div>
      <InputText v-model="editor.source_ref" placeholder="Source ref (optional, e.g. document:..., autotest_run:...)" />
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

<script setup>
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

import { apiClient } from '../api'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()

const question = ref('')
const asking = ref(false)
const answer = ref('')
const sources = ref([])

const saving = ref(false)
const entry = ref(createBlankEntry())

const loadingRecent = ref(false)
const recent = ref([])
const recentFilterText = ref('')

const selectedRelatedItemId = ref('')

const editorVisible = ref(false)
const editorSaving = ref(false)
const editor = ref(createBlankEntry())

const pickerSelected = ref('')
const documents = ref([])
const photos = ref([])
const prompts = ref([])
const autotestRuns = ref([])
const knowledgeEntries = ref([])
const logbookEntries = ref([])

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

const pickerOptions = computed(() => {
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

function createBlankEntry() {
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

function clearResult() {
  answer.value = ''
  sources.value = []
}

function resetEntry() {
  entry.value = createBlankEntry()
}

async function submitQA() {
  if (!question.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Question required', detail: 'Enter a question first.', life: 3000 })
    return
  }

  asking.value = true
  try {
    const response = await apiClient.post('/api/qa', { question: question.value.trim() })
    answer.value = response.answer
    sources.value = response.sources || []
  } catch (error) {
    toast.add({ severity: 'error', summary: 'QA failed', detail: error.message, life: 4000 })
  } finally {
    asking.value = false
  }
}

async function saveEntry() {
  // Validate problem field: must not be empty after trimming (matches backend min_length=1)
  const trimmedProblem = String(entry.value.problem || '').trim()
  if (!trimmedProblem) {
    toast.add({ severity: 'warn', summary: 'Validation Error', detail: 'Problem field cannot be empty.', life: 3500 })
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
    toast.add({ severity: 'warn', summary: 'Missing fields', detail: 'Solution field is required.', life: 3500 })
    return
  }

  saving.value = true
  try {
    await apiClient.post('/api/knowledge/entries', payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Knowledge note indexed.', life: 3000 })
    resetEntry()
    await loadRecent()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Save failed', detail: error.message, life: 4000 })
  } finally {
    saving.value = false
  }
}

async function loadRecent() {
  loadingRecent.value = true
  try {
    recent.value = await apiClient.get('/api/knowledge/entries')
  } catch (error) {
    recent.value = []
    toast.add({ severity: 'error', summary: 'Load failed', detail: error.message, life: 3500 })
  } finally {
    loadingRecent.value = false
  }
}

async function loadPickers() {
  try {
    const [docs, imgs, runs, promptList, kbEntries, lbEntries] = await Promise.all([
      apiClient.get('/api/docs'),
      apiClient.get('/api/photos'),
      apiClient.get('/api/autotest/runs'),
      apiClient.get('/api/prompts'),
      apiClient.get('/api/knowledge/entries'),
      apiClient.get('/api/logbook/entries'),
    ])
    documents.value = docs || []
    photos.value = imgs || []
    autotestRuns.value = runs || []
    prompts.value = promptList || []
    knowledgeEntries.value = kbEntries || []
    logbookEntries.value = lbEntries || []
  } catch {
    // ignore (pickers are optional)
  }
}

function selectForRelated(item) {
  if (!item?.id) {
    return
  }
  selectedRelatedItemId.value = `knowledge:${item.id}`
}

function openEditor(item) {
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
  const payload = {
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
    await apiClient.patch(`/api/knowledge/entries/${editor.value.id}`, payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Knowledge entry updated.', life: 2500 })
    editorVisible.value = false
    await loadRecent()
    selectedRelatedItemId.value = `knowledge:${editor.value.id}`
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Save failed', detail: error.message, life: 4000 })
  } finally {
    editorSaving.value = false
  }
}

async function archiveEntry(item) {
  if (!item?.id) {
    return
  }
  if (!window.confirm(`Archive "${item.title || 'this entry'}"?`)) {
    return
  }
  try {
    await apiClient.patch(`/api/knowledge/entries/${item.id}`, { status: 'archived' })
    toast.add({ severity: 'success', summary: 'Archived', detail: 'Entry archived.', life: 2200 })
    await loadRecent()
    if (selectedRelatedItemId.value === `knowledge:${item.id}`) {
      selectedRelatedItemId.value = ''
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Archive failed', detail: error.message, life: 4000 })
  }
}

onMounted(loadRecent)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stack-sm {
  display: flex;
  flex-direction: column;
  gap: 8px;
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

.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
}

.answer {
  white-space: pre-wrap;
  margin: 0;
}

.source-card {
  padding: 10px 12px;
  border-radius: 12px;
  background: white;
  border: 1px solid #d8e1e8;
}

.muted {
  margin: 4px 0 0;
  font-size: 12px;
  color: #51606f;
}

.snippet {
  margin: 8px 0 0;
  white-space: pre-wrap;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
