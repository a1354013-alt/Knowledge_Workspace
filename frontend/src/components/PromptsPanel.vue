<template>
  <div class="page-panel">
    <div class="page-heading">
      <h2>{{ t('prompts.title') }}</h2>
      <p>{{ t('prompts.subtitle') }}</p>
    </div>

    <div class="grid">
      <Card>
        <template #title>
          {{ t('prompts.listTitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <p
              v-if="loadMessage"
              class="inline-status"
              :class="{ 'inline-status-warning': showReloadWarning }"
            >
              {{ loadMessage }}
            </p>
            <div class="row">
              <Button
                :label="t('common.refresh')"
                outlined
                icon="pi pi-refresh"
                :loading="loading"
                @click="loadPrompts"
              />
            </div>
            <InputText
              v-model="filterText"
              :placeholder="t('prompts.filter')"
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
                :header="t('common.title')"
              />
              <Column
                field="tags"
                :header="t('common.tags')"
              />
              <Column
                field="updated_at"
                :header="t('common.updated')"
              />
              <Column :header="t('common.actions')">
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
              <template #empty>
                <EmptyStateBlock
                  icon="pi pi-comment"
                  :title="t('prompts.emptyTitle')"
                  :description="t('prompts.emptyDescription')"
                />
              </template>
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
          {{ t('prompts.createTitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <InputText
              v-model="form.title"
              :placeholder="t('common.title')"
            />
            <Textarea
              v-model="form.content"
              rows="10"
              :placeholder="t('prompts.promptContent')"
            />
            <InputText
              v-model="form.tags"
              :placeholder="t('prompts.tagsComma')"
            />
            <div class="row">
              <Button
                :label="t('common.save')"
                icon="pi pi-save"
                :loading="saving"
                @click="savePrompt"
              />
              <Button
                :label="t('common.reset')"
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
import { apiPaths } from '../api/endpoints'
import { useI18n } from '../i18n'
import { confirmDanger } from '../services/confirm'
import RelatedItemsPanel from './RelatedItemsPanel.vue'
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import { useWorkspaceStore } from '../workspace-store'
import type { MessageResponse, SavedPromptCreateRequest, SavedPromptResponse } from '../types'

const toast = useToast()
const { t } = useI18n()

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
const loadMessage = computed(() => store.state.error.prompts || '')
const showReloadWarning = computed(() => store.state.status.prompts === 'error' && prompts.value.length > 0)

async function loadPrompts() {
  loading.value = true
  try {
    await store.refreshPrompts({ force: true })
    prompts.value = store.state.lists.prompts || []
  } catch (error: unknown) {
    prompts.value = store.state.lists.prompts || []
    const apiError = error as { message?: string }
    toast.add({
      severity: prompts.value.length ? 'warn' : 'error',
      summary: 'Prompts reload failed',
      detail: apiError?.message || store.state.error.prompts || 'Request failed.',
      life: 4000,
    })
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
    const response = await post<SavedPromptResponse, SavedPromptCreateRequest>(apiPaths.prompts.list, payload)
    const indexingUnavailable = response.index_status === 'unavailable'
    const detail = response.index_status === 'failed' || indexingUnavailable
      ? response.index_error || (indexingUnavailable ? 'Prompt saved, but the vector index is unavailable.' : 'Prompt saved, but indexing failed.')
      : 'Prompt saved.'
    toast.add({ severity: response.index_status === 'failed' || indexingUnavailable ? 'warn' : 'success', summary: 'Saved', detail, life: 3500 })
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
  if (!(await confirmDanger({ header: 'Delete prompt', message: `Delete "${item.title}"?`, acceptLabel: 'Delete' }))) {
    return
  }
  try {
    await del<MessageResponse>(apiPaths.prompts.detail(item.id))
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

.inline-status {
  margin: 0;
  color: #b45309;
  font-size: 13px;
}

.inline-status-warning {
  font-weight: 600;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
