<template>
  <div class="grid">
    <Card>
      <template #title>
        Ask your knowledge
      </template>
      <template #subtitle>
        Search across your documents, knowledge notes, logbook entries, and image metadata.
      </template>
      <template #content>
        <div class="stack-md">
          <Textarea
            v-model="question"
            rows="5"
            placeholder="e.g. Delphi CRLF 問題怎麼處理？Vue build fail 之前怎麼修？"
          />
          <div class="row">
            <Button
              label="Ask"
              icon="pi pi-send"
              :loading="asking"
              @click="submitQA"
            />
            <Button
              label="Clear"
              outlined
              severity="secondary"
              :disabled="asking"
              @click="clearResult"
            />
          </div>

          <div
            v-if="answer"
            class="result-box"
          >
            <h3>Answer</h3>
            <p class="answer">
              {{ answer }}
            </p>
            <div
              v-if="sources.length"
              class="stack-sm"
            >
              <h4>Sources</h4>
              <article
                v-for="(source, index) in sources"
                :key="index"
                class="source-card"
              >
                <strong>{{ source.title }}</strong>
                <p class="muted">
                  {{ source.source_type }} · {{ source.location || '-' }}
                </p>
                <p class="snippet">
                  {{ source.snippet }}
                </p>
              </article>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        Quick add (Knowledge note)
      </template>
      <template #subtitle>
        Manually capture a problem / root cause / solution so it becomes searchable.
      </template>
      <template #content>
        <div class="stack-md">
          <InputText
            v-model="entry.title"
            placeholder="Title (short)"
          />
          <Textarea
            v-model="entry.problem"
            rows="3"
            placeholder="Problem"
          />
          <Textarea
            v-model="entry.root_cause"
            rows="3"
            placeholder="Root cause"
          />
          <Textarea
            v-model="entry.solution"
            rows="4"
            placeholder="Solution (steps, commands, links)"
          />
          <InputText
            v-model="entry.tags"
            placeholder="Tags (comma separated)"
          />
          <Textarea
            v-model="entry.notes"
            rows="2"
            placeholder="Notes (optional)"
          />
          <div class="row">
            <Dropdown
              v-model="entry.status"
              :options="statusOptions"
              option-label="label"
              option-value="value"
              placeholder="Status"
            />
            <Dropdown
              v-model="entry.source_type"
              :options="sourceTypes"
              option-label="label"
              option-value="value"
              placeholder="Source type"
            />
          </div>
          <InputText
            v-model="entry.source_ref"
            placeholder="Source ref (optional, e.g. document:..., autotest_run:...)"
          />
          <Chips
            v-model="entry.related_item_ids"
            separator=","
            placeholder="Related item IDs (comma-separated, e.g. document:..., photo:..., prompt:...)"
          />
          <div class="row">
            <Button
              label="Save"
              icon="pi pi-save"
              :loading="saving"
              @click="saveEntry"
            />
            <Button
              label="Reset"
              outlined
              severity="secondary"
              :disabled="saving"
              @click="resetEntry"
            />
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        Recent notes
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            label="Refresh"
            outlined
            icon="pi pi-refresh"
            :loading="loadingRecent"
            @click="loadRecent"
          />
          <InputText
            v-model="recentFilterText"
            placeholder="Filter recent (title/tags/status)"
          />
          <DataTable
            :value="filteredRecent"
            :loading="loadingRecent"
            data-key="id"
            size="small"
            responsive-layout="scroll"
          >
            <Column
              field="title"
              header="Title"
            />
            <Column
              field="tags"
              header="Tags"
            />
            <Column
              field="source_type"
              header="Source"
            />
            <Column
              field="source_ref"
              header="Source ref"
            />
            <Column
              field="status"
              header="Status"
            />
            <Column
              field="updated_at"
              header="Updated"
            />
            <Column header="Actions">
              <template #body="slotProps">
                <div class="actions-inline">
                  <Button
                    icon="pi pi-pencil"
                    text
                    severity="secondary"
                    @click="openEditor(slotProps.data)"
                    v-tooltip.top="'Edit'"
                  />
                  <Button
                    icon="pi pi-history"
                    text
                    severity="secondary"
                    @click="openRevisionHistory(slotProps.data)"
                    v-tooltip.top="'Revision History'"
                  />
                  <Button
                    icon="pi pi-sitemap"
                    text
                    severity="secondary"
                    @click="selectForRelated(slotProps.data)"
                    v-tooltip.top="'Related Items'"
                  />
                  <Button
                    icon="pi pi-archive"
                    text
                    severity="secondary"
                    @click="archiveEntry(slotProps.data)"
                    v-tooltip.top="'Archive'"
                  />
                </div>
              </template>
            </Column>
          </DataTable>

          <RelatedItemsPanel
            v-if="selectedRelatedItemId"
            :item-id="selectedRelatedItemId"
          />
        </div>
      </template>
    </Card>
  </div>

  <!-- Edit Dialog -->
  <Dialog
    v-model:visible="editorVisible"
    modal
    header="Edit knowledge entry"
    :style="{ width: 'min(920px, 95vw)' }"
  >
    <div class="stack-md">
      <InputText
        v-model="editor.title"
        placeholder="Title"
      />
      <Textarea
        v-model="editor.problem"
        rows="3"
        placeholder="Problem"
      />
      <Textarea
        v-model="editor.root_cause"
        rows="3"
        placeholder="Root cause"
      />
      <Textarea
        v-model="editor.solution"
        rows="4"
        placeholder="Solution"
      />
      <InputText
        v-model="editor.tags"
        placeholder="Tags"
      />
      <Textarea
        v-model="editor.notes"
        rows="2"
        placeholder="Notes"
      />
      <div class="row">
        <Dropdown
          v-model="editor.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Status"
        />
        <Dropdown
          v-model="editor.source_type"
          :options="sourceTypes"
          option-label="label"
          option-value="value"
          placeholder="Source type"
        />
      </div>
      <InputText
        v-model="editor.source_ref"
        placeholder="Source ref (optional, e.g. document:..., autotest_run:...)"
      />
      <Chips
        v-model="editor.related_item_ids"
        separator=","
        placeholder="Related item IDs (comma-separated)"
      />

      <div class="row">
        <Dropdown
          v-model="pickerSelected"
          :options="pickerOptions"
          option-label="label"
          option-value="value"
          placeholder="Add related item..."
          class="picker"
        />
        <Button
          label="Add"
          icon="pi pi-plus"
          outlined
          :disabled="!pickerSelected"
          @click="addPickedRelated"
        />
      </div>

      <InputText
        v-model="editor.change_note"
        placeholder="Change note (optional)"
      />

      <div class="row">
        <Button
          label="Save changes"
          icon="pi pi-save"
          :loading="editorSaving"
          @click="saveEditor"
        />
        <Button
          label="Close"
          outlined
          severity="secondary"
          :disabled="editorSaving"
          @click="editorVisible = false"
        />
      </div>
    </div>
  </Dialog>

  <!-- Revision History Dialog -->
  <Dialog
    v-model:visible="revisionVisible"
    modal
    header="Revision History"
    :style="{ width: 'min(1000px, 95vw)' }"
  >
    <div class="stack-md">
      <DataTable
        :value="revisions"
        :loading="loadingRevisions"
        data-key="revision_id"
        size="small"
        responsive-layout="scroll"
      >
        <Column
          field="version_number"
          header="v#"
          style="width: 60px"
        />
        <Column
          field="created_at"
          header="Time"
        />
        <Column
          field="changed_by"
          header="By"
        />
        <Column
          field="change_note"
          header="Note"
        />
        <Column header="Actions">
          <template #body="slotProps">
            <div class="actions-inline">
              <Button
                icon="pi pi-eye"
                text
                severity="secondary"
                @click="viewRevision(slotProps.data)"
                v-tooltip.top="'View Content'"
              />
              <Button
                icon="pi pi-compare"
                text
                severity="secondary"
                @click="viewDiff(slotProps.data)"
                v-tooltip.top="'Compare with current'"
              />
              <Button
                icon="pi pi-undo"
                text
                severity="warning"
                @click="restoreRevision(slotProps.data)"
                v-tooltip.top="'Restore this version'"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <div v-if="loadingRevisions" class="text-center p-4">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem"></i>
      </div>

      <div v-if="!loadingRevisions && !revisions.length" class="empty-state">
        No revisions found for this entry.
      </div>

      <!-- Revision Detail/Diff View -->
      <div v-if="selectedRevision" class="revision-detail stack-md mt-4">
        <div class="row justify-content-between">
          <h3>{{ diffMode ? 'Difference' : 'Revision Content' }} (v{{ selectedRevision.version_number }})</h3>
          <Button icon="pi pi-times" text severity="secondary" @click="selectedRevision = null; diffMode = false" />
        </div>

        <div v-if="diffMode && diffResult" class="stack-sm">
          <div v-if="!diffResult.changed.length" class="p-2">No differences detected.</div>
          <div v-for="item in diffResult.changed" :key="item.field" class="diff-item">
            <div class="diff-field"><strong>{{ item.field }}</strong></div>
            <div class="diff-values">
              <div class="diff-old"> - {{ item.old_value }}</div>
              <div class="diff-new"> + {{ item.new_value }}</div>
            </div>
          </div>
        </div>

        <div v-else class="stack-sm revision-content-box">
          <div class="content-field"><strong>Title:</strong> {{ selectedRevision.title }}</div>
          <div class="content-field"><strong>Status:</strong> {{ selectedRevision.status }}</div>
          <div class="content-field"><strong>Problem:</strong> <pre>{{ selectedRevision.problem }}</pre></div>
          <div class="content-field"><strong>Root Cause:</strong> <pre>{{ selectedRevision.root_cause }}</pre></div>
          <div class="content-field"><strong>Solution:</strong> <pre>{{ selectedRevision.solution }}</pre></div>
          <div class="content-field"><strong>Tags:</strong> {{ selectedRevision.tags }}</div>
        </div>
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

import { get, patch, post } from '../api'
import { useWorkspaceStore } from '../workspace-store'
import type {
  AutoTestRunListItemResponse,
  DocumentResponse,
  KnowledgeEntryCreateRequest,
  KnowledgeEntryResponse,
  KnowledgeEntryUpdateRequest,
  KnowledgeRevisionResponse,
  KnowledgeDiffResponse,
  LogbookEntryResponse,
  MessageResponse,
  PhotoResponse,
  QARequest,
  QAResponse,
  SavedPromptResponse,
  Source,
} from '../types'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()
const store = useWorkspaceStore()

const question = ref('')
const asking = ref(false)
const answer = ref('')
const sources = ref<Source[]>([])

const saving = ref(false)
const entry = ref<KnowledgeEntryCreateRequest>({
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
})

const loadingRecent = ref(false)
const recent = ref<KnowledgeEntryResponse[]>([])
const recentFilterText = ref('')

const editorVisible = ref(false)
const editorSaving = ref(false)
const editor = ref<KnowledgeEntryUpdateRequest & { id: string }>({
  id: '',
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
  change_note: '',
})

const selectedRelatedItemId = ref('')

const documents = ref<DocumentResponse[]>([])
const photos = ref<PhotoResponse[]>([])
const autotestRuns = ref<AutoTestRunListItemResponse[]>([])
const prompts = ref<SavedPromptResponse[]>([])
const knowledgeEntries = ref<KnowledgeEntryResponse[]>([])
const logbookEntries = ref<LogbookEntryResponse[]>([])

const pickerSelected = ref('')

// Revision state
const revisionVisible = ref(false)
const loadingRevisions = ref(false)
const revisions = ref<KnowledgeRevisionResponse[]>([])
const selectedRevision = ref<KnowledgeRevisionResponse | null>(null)
const diffMode = ref(false)
const diffResult = ref<KnowledgeDiffResponse | null>(null)
const currentKnowledgeId = ref('')

const statusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Reviewed', value: 'reviewed' },
  { label: 'Verified', value: 'verified' },
  { label: 'Archived', value: 'archived' },
]

const sourceTypes = [
  { label: 'Manual', value: 'manual' },
  { label: 'Document-derived', value: 'document-derived' },
  { label: 'AutoTest-derived', value: 'autotest-derived' },
]

const filteredRecent = computed(() => {
  const query = recentFilterText.value.toLowerCase().trim()
  if (!query) return recent.value
  return recent.value.filter((item) => {
    return (
      (item.title || '').toLowerCase().includes(query) ||
      (item.tags || '').toLowerCase().includes(query) ||
      (item.status || '').toLowerCase().includes(query)
    )
  })
})

const pickerOptions = computed(() => {
  const options: { label: string; value: string }[] = []
  documents.value.forEach((d) => options.push({ label: `[Doc] ${d.filename}`, value: `document:${d.id}` }))
  photos.value.forEach((p) => options.push({ label: `[Photo] ${p.filename}`, value: `photo:${p.id}` }))
  autotestRuns.value.forEach((r) => options.push({ label: `[AutoTest] ${r.project_name || r.id}`, value: `autotest_run:${r.id}` }))
  prompts.value.forEach((p) => options.push({ label: `[Prompt] ${p.title}`, value: `prompt:${p.id}` }))
  knowledgeEntries.value.forEach((k) => {
    if (k.id !== editor.value.id) {
      options.push({ label: `[Knowledge] ${k.title}`, value: `knowledge:${k.id}` })
    }
  })
  logbookEntries.value.forEach((l) => options.push({ label: `[Logbook] ${l.title}`, value: `logbook:${l.id}` }))
  return options.sort((a, b) => a.label.localeCompare(b.label))
})

function clearResult() {
  question.value = ''
  answer.value = ''
  sources.value = []
}

async function submitQA() {
  const q = question.value.trim()
  if (!q) return
  asking.value = true
  try {
    const res = await post<QAResponse, QARequest>('/api/qa', { question: q })
    answer.value = res.answer
    sources.value = res.sources
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'QA failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  } finally {
    asking.value = false
  }
}

function resetEntry() {
  entry.value = {
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

async function saveEntry() {
  const payload: KnowledgeEntryCreateRequest = {
    title: String(entry.value.title || '').trim(),
    problem: String(entry.value.problem || '').trim(),
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
    await post<MessageResponse, KnowledgeEntryCreateRequest>('/api/knowledge/entries', payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Knowledge note indexed.', life: 3000 })
    resetEntry()
    await loadRecent()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Save failed', detail: apiError?.message || 'Request failed.', life: 4000 })
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
    recent.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Load failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
    // ignore (pickers are optional)
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
    change_note: '',
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
    change_note: String(editor.value.change_note || '').trim(),
  }
  editorSaving.value = true
  try {
    await patch<MessageResponse, KnowledgeEntryUpdateRequest>(`/api/knowledge/entries/${editor.value.id}`, payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Knowledge entry updated.', life: 2500 })
    editorVisible.value = false
    await loadRecent()
    selectedRelatedItemId.value = `knowledge:${editor.value.id}`
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Save failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  } finally {
    editorSaving.value = false
  }
}

async function archiveEntry(item: KnowledgeEntryResponse) {
  if (!item?.id) {
    return
  }
  if (!window.confirm(`Archive "${item.title || 'this entry'}"?`)) {
    return
  }
  try {
    await patch<MessageResponse, KnowledgeEntryUpdateRequest>(`/api/knowledge/entries/${item.id}`, { status: 'archived' })
    toast.add({ severity: 'success', summary: 'Archived', detail: 'Entry archived.', life: 2200 })
    await loadRecent()
    if (selectedRelatedItemId.value === `knowledge:${item.id}`) {
      selectedRelatedItemId.value = ''
    }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Archive failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  }
}

// Revision methods
async function openRevisionHistory(item: KnowledgeEntryResponse) {
  currentKnowledgeId.value = item.id
  revisions.value = []
  selectedRevision.value = null
  diffMode.value = false
  revisionVisible.value = true
  loadingRevisions.value = true
  try {
    revisions.value = await get<KnowledgeRevisionResponse[]>(`/api/knowledge/${item.id}/revisions`)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Load failed', detail: apiError?.message || 'Failed to load revisions.', life: 3500 })
  } finally {
    loadingRevisions.value = false
  }
}

function viewRevision(rev: KnowledgeRevisionResponse) {
  selectedRevision.value = rev
  diffMode.value = false
}

async function viewDiff(rev: KnowledgeRevisionResponse) {
  selectedRevision.value = rev
  diffMode.value = true
  diffResult.value = null
  try {
    diffResult.value = await get<KnowledgeDiffResponse>(`/api/knowledge/${currentKnowledgeId.value}/revisions/${rev.revision_id}/diff`)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Diff failed', detail: apiError?.message || 'Failed to get diff.', life: 3500 })
  }
}

async function restoreRevision(rev: KnowledgeRevisionResponse) {
  if (!window.confirm(`Restore to version ${rev.version_number}? This will create a snapshot of current state.`)) {
    return
  }
  try {
    const res = await post<MessageResponse, any>(`/api/knowledge/${currentKnowledgeId.value}/revisions/${rev.revision_id}/restore`, {})
    toast.add({ severity: 'success', summary: 'Restored', detail: res.message, life: 3000 })
    revisionVisible.value = false
    await loadRecent()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Restore failed', detail: apiError?.message || 'Failed to restore.', life: 4000 })
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

.justify-content-between {
  justify-content: space-between;
}

.mt-4 {
  margin-top: 1.5rem;
}

.text-center {
  text-align: center;
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

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 8px;
}

.revision-detail {
  border-top: 1px solid #dee2e6;
  padding-top: 1rem;
}

.revision-content-box {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.content-field {
  margin-bottom: 0.5rem;
}

.content-field pre {
  background: #fff;
  padding: 0.5rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-item {
  border: 1px solid #dee2e6;
  border-radius: 4px;
  overflow: hidden;
}

.diff-field {
  background: #e9ecef;
  padding: 4px 8px;
  border-bottom: 1px solid #dee2e6;
}

.diff-values {
  padding: 8px;
}

.diff-old {
  color: #dc3545;
  background-color: #f8d7da;
  padding: 2px 4px;
  margin-bottom: 2px;
  white-space: pre-wrap;
}

.diff-new {
  color: #198754;
  background-color: #d1e7dd;
  padding: 2px 4px;
  white-space: pre-wrap;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
