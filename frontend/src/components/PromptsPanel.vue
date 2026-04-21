<template>
  <div class="grid">
    <Card>
      <template #title>
        Saved prompts
      </template>
      <template #subtitle>
        Reusable prompts for recurring engineering workflows (debugging, reviews, postmortems).
      </template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button
              label="Refresh"
              outlined
              icon="pi pi-refresh"
              :loading="loading"
              @click="loadPrompts"
            />
          </div>
          <InputText
            v-model="filterText"
            placeholder="Filter by title/tags"
          />
          <DataTable
            :value="filteredPrompts"
            :loading="loading"
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
              field="updated_at"
              header="Updated"
            />
            <Column header="Actions">
              <template #body="slotProps">
                <div class="actions-inline">
                  <Button
                    icon="pi pi-copy"
                    text
                    @click="copyPrompt(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-sitemap"
                    text
                    severity="secondary"
                    @click="selectForRelated(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-trash"
                    text
                    severity="danger"
                    @click="deletePrompt(slotProps.data)"
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

    <Card>
      <template #title>
        Create prompt
      </template>
      <template #content>
        <div class="stack-md">
          <InputText
            v-model="form.title"
            placeholder="Title"
          />
          <Textarea
            v-model="form.content"
            rows="10"
            placeholder="Prompt content"
          />
          <InputText
            v-model="form.tags"
            placeholder="Tags (comma separated)"
          />
          <div class="row">
            <Button
              label="Save"
              icon="pi pi-save"
              :loading="saving"
              @click="savePrompt"
            />
            <Button
              label="Reset"
              outlined
              severity="secondary"
              :disabled="saving"
              @click="resetForm"
            />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import { del, post } from '../api'
import RelatedItemsPanel from './RelatedItemsPanel.vue'
import { useWorkspaceStore } from '../workspace-store'
import type { MessageResponse, SavedPromptCreateRequest, SavedPromptResponse } from '../types'

const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const prompts = ref<SavedPromptResponse[]>([])
const filterText = ref('')
const selectedRelatedItemId = ref('')
const store = useWorkspaceStore()

const form = ref<SavedPromptCreateRequest>(createBlankForm())

function createBlankForm(): SavedPromptCreateRequest {
  return { title: '', content: '', tags: '' }
}

function resetForm() {
  form.value = createBlankForm()
}

const filteredPrompts = computed(() => {
  const query = String(filterText.value || '').trim().toLowerCase()
  if (!query) {
    return prompts.value
  }
  return prompts.value.filter((item) => {
    const haystack = `${item.title || ''} ${item.tags || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

async function loadPrompts() {
  loading.value = true
  try {
    await store.refreshPrompts({ force: true })
    prompts.value = store.state.lists.prompts || []
  } catch {
    prompts.value = []
  } finally {
    loading.value = false
  }
}

async function savePrompt() {
  const payload: SavedPromptCreateRequest = {
    title: String(form.value.title || '').trim(),
    content: String(form.value.content || '').trim(),
    tags: String(form.value.tags || '').trim(),
  }
  if (!payload.title || !payload.content) {
    toast.add({ severity: 'warn', summary: 'Missing fields', detail: 'Title and content are required.', life: 3500 })
    return
  }

  saving.value = true
  try {
    await post<MessageResponse, SavedPromptCreateRequest>('/api/prompts', payload)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Prompt saved.', life: 3000 })
    resetForm()
    await loadPrompts()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Save failed', detail: apiError?.message || 'Request failed.', life: 4500 })
  } finally {
    saving.value = false
  }
}

async function deletePrompt(item: SavedPromptResponse) {
  if (!item?.id) {
    return
  }
  if (!window.confirm(`Delete "${item.title}"?`)) {
    return
  }
  try {
    await del<MessageResponse>(`/api/prompts/${item.id}`)
    await loadPrompts()
    toast.add({ severity: 'success', summary: 'Deleted', detail: 'Prompt removed.', life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Delete failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  }
}

async function copyPrompt(item: SavedPromptResponse) {
  const text = String(item?.content || '')
  if (!text) {
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: 'Copied', detail: 'Prompt copied to clipboard.', life: 2000 })
  } catch {
    toast.add({ severity: 'warn', summary: 'Copy failed', detail: 'Clipboard permission denied.', life: 2500 })
  }
}

function selectForRelated(item: SavedPromptResponse) {
  if (!item?.id) {
    return
  }
  selectedRelatedItemId.value = `prompt:${item.id}`
}

onMounted(loadPrompts)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1.25fr 0.75fr;
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

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
