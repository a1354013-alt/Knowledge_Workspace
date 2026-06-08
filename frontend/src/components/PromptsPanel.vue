<template>
  <div class="page-content prompts-page">
    <header class="page-header">
      <h2>{{ t('prompts.pageTitle') }}</h2>
      <p>{{ t('prompts.pageSubtitle') }}</p>
    </header>

    <div class="grid">
      <Card>
        <template #title>
          {{ t('prompts.savedPrompts') }}
        </template>
        <template #subtitle>
          {{ t('prompts.savedSubtitle') }}
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
              :placeholder="t('prompts.filterPlaceholder')"
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
                <div class="empty-state">
                  <strong>{{ t('prompts.emptyTitle') }}</strong>
                  <p>{{ t('prompts.emptyIntro') }}</p>
                  <ul>
                    <li>{{ t('prompts.emptyCodeReview') }}</li>
                    <li>{{ t('prompts.emptyLogAnalysis') }}</li>
                    <li>{{ t('prompts.emptyPrDescription') }}</li>
                    <li>{{ t('prompts.emptyTestDebug') }}</li>
                  </ul>
                </div>
              </template>
            </DataTable>

            <RelatedItemsPanel
              v-if="selectedRelatedItemId"
              :item-id="selectedRelatedItemId"
            />
          </div>
        </template>
      </Card>

      <div class="create-panel surface-card">
        <div>
          <h3>{{ t('prompts.createPrompt') }}</h3>
          <p>{{ t('prompts.savedSubtitle') }}</p>
        </div>
        <Button
          :label="t('prompts.createPrompt')"
          icon="pi pi-plus"
          @click="createVisible = true"
        />
      </div>
    </div>
  </div>

  <Dialog
    v-model:visible="createVisible"
    modal
    :header="t('prompts.createPrompt')"
    class="workspace-dialog"
    :style="{ width: 'min(720px, calc(100vw - 32px))' }"
  >
    <div class="dialog-body stack-md">
      <InputText
        v-model="form.title"
        :placeholder="t('common.title')"
      />
      <Textarea
        v-model="form.content"
        rows="10"
        :placeholder="t('prompts.content')"
      />
      <InputText
        v-model="form.tags"
        :placeholder="t('prompts.tagsPlaceholder')"
      />
    </div>
    <template #footer>
      <div class="dialog-footer">
        <Button
          :label="t('common.reset')"
          outlined
          severity="secondary"
          :disabled="saving"
          @click="resetForm"
        />
        <Button
          :label="t('common.save')"
          icon="pi pi-save"
          :loading="saving"
          @click="saveCreatePrompt"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import { del, post } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import { confirmDanger } from '../services/confirm'
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
const createVisible = ref(false)

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
      summary: t('prompts.reloadFailed'),
      detail: apiError?.message || store.state.error.prompts || t('common.requestFailed'),
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
    toast.add({ severity: 'warn', summary: t('auth.missingFields'), detail: t('prompts.missingDetail'), life: 3500 })
    return false
  }

  saving.value = true
  try {
    const response = await post<SavedPromptResponse, SavedPromptCreateRequest>(apiPaths.prompts.list, payload)
    const indexingUnavailable = response.index_status === 'unavailable'
    const detail = response.index_status === 'failed' || indexingUnavailable
      ? response.index_error || (indexingUnavailable ? t('prompts.savedIndexUnavailable') : t('prompts.savedIndexFailed'))
      : t('prompts.savedDetail')
    toast.add({ severity: response.index_status === 'failed' || indexingUnavailable ? 'warn' : 'success', summary: t('common.saved'), detail, life: 3500 })
    resetForm()
    await loadPrompts()
    return true
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4500 })
    return false
  } finally {
    saving.value = false
  }
}

async function saveCreatePrompt() {
  if (await savePrompt()) {
    createVisible.value = false
  }
}

async function deletePrompt(item: SavedPromptResponse) {
  if (!item?.id) {
    return
  }
  if (!(await confirmDanger({ header: t('prompts.deletePrompt'), message: t('prompts.deleteMessage', { title: item.title }), acceptLabel: t('prompts.deleteAccept') }))) {
    return
  }
  try {
    await del<MessageResponse>(apiPaths.prompts.detail(item.id))
    await loadPrompts()
    toast.add({ severity: 'success', summary: t('prompts.deleted'), detail: t('prompts.deletedDetail'), life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('prompts.deleteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function copyPrompt(item: SavedPromptResponse) {
  const text = String(item?.content || '')
  if (!text) {
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: t('prompts.copied'), detail: t('prompts.copiedDetail'), life: 2000 })
  } catch {
    toast.add({ severity: 'warn', summary: t('prompts.copyFailed'), detail: t('prompts.clipboardDenied'), life: 2500 })
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
.page-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.prompts-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
}

.page-header h2,
.page-header p {
  margin: 0;
}

.page-header p {
  margin-top: 6px;
  color: #51606f;
}

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

.create-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
}

.create-panel h3,
.create-panel p {
  margin: 0;
}

.create-panel h3 {
  font-size: 1rem;
}

.create-panel p {
  margin-top: 4px;
  color: #51606f;
  font-size: 0.9rem;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

.inline-status {
  margin: 0;
  color: #b45309;
  font-size: 13px;
}

.inline-status-warning {
  font-weight: 600;
}

.empty-state {
  padding: 18px;
  color: #51606f;
  line-height: 1.6;
}

.empty-state strong {
  display: block;
  color: #1f2f46;
  margin-bottom: 4px;
}

.empty-state p,
.empty-state ul {
  margin: 0;
}

.empty-state ul {
  padding-left: 20px;
  margin-top: 6px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
