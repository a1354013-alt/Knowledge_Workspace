<template>
  <div class="grid">
    <Card>
      <template #title>
        {{ t('settings.localAiProvider') }}
      </template>
      <template #subtitle>
        {{ t('settings.localAiSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            :label="t('common.refresh')"
            outlined
            icon="pi pi-refresh"
            :loading="loading"
            @click="loadStatus"
          />
          <div class="kv">
            <div class="key">
              {{ t('settings.primaryProvider') }}
            </div>
            <div class="value">
              {{ status.primary_provider || '-' }}
            </div>
            <div class="key">
              {{ t('settings.activeProvider') }}
            </div>
            <div class="value">
              {{ status.active_provider || '-' }}
            </div>
            <div class="key">
              {{ t('settings.model') }}
            </div>
            <div class="value">
              {{ status.model || '-' }}
            </div>
            <div class="key">
              {{ t('settings.baseUrl') }}
            </div>
            <div class="value">
              {{ status.base_url || '-' }}
            </div>
            <div class="key">
              {{ t('settings.primaryHealthy') }}
            </div>
            <div class="value">
              {{ status.primary_healthy ? t('common.yes') : t('common.no') }}
            </div>
            <div class="key">
              {{ t('settings.fallback') }}
            </div>
            <div class="value">
              {{ status.fallback_enabled ? t('common.enabled') : t('common.disabled') }}
            </div>
            <div class="key">
              {{ t('settings.ready') }}
            </div>
            <div class="value">
              {{ status.llm_ready_for_generation ? t('common.yes') : t('common.no') }}
            </div>
            <div class="key">
              {{ t('settings.error') }}
            </div>
            <div class="value">
              {{ status.error_message || '-' }}
            </div>
          </div>
          <p class="muted">
            {{ t('settings.ollamaHint') }}
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('settings.promptTemplates') }}
      </template>
      <template #subtitle>
        {{ t('settings.promptTemplatesSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            :label="t('common.refresh')"
            outlined
            icon="pi pi-refresh"
            :loading="loadingTemplates"
            @click="loadTemplates"
          />
          <div
            v-if="templates.length"
            class="kv"
          >
            <div class="key">
              {{ t('settings.availableTemplates') }}
            </div>
            <div class="value">
              {{ templates.map((t) => t.value).join(', ') }}
            </div>
          </div>
          <p class="muted">
            {{ t('settings.generateHint') }}
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('settings.indexHealth') }}
      </template>
      <template #subtitle>
        {{ t('settings.indexHealthSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button
              :label="t('common.refresh')"
              outlined
              icon="pi pi-refresh"
              :loading="loadingIndex"
              @click="loadIndexStatus"
            />
            <Button
              :label="t('settings.rebuildAllIndexes')"
              icon="pi pi-wrench"
              :loading="rebuildingIndex"
              @click="rebuildAllIndexes"
            />
          </div>
          <div class="kv">
            <div class="key">
              {{ t('settings.provider') }}
            </div>
            <div class="value">
              {{ indexStatus.provider.active_provider || '-' }}
            </div>
            <div class="key">
              {{ t('settings.mode') }}
            </div>
            <div class="value">
              {{ indexStatus.provider.demo_mode ? t('settings.demoFallback') : t('settings.semanticReady') }}
            </div>
            <div class="key">
              {{ t('common.status') }}
            </div>
            <div class="value">
              {{ indexStatus.provider.status || '-' }}
            </div>
            <div class="key">
              {{ t('settings.message') }}
            </div>
            <div class="value">
              {{ indexStatus.provider.message || '-' }}
            </div>
            <div class="key">
              {{ t('settings.excluded') }}
            </div>
            <div class="value">
              {{ totalExcludedItems }}
            </div>
          </div>
          <p class="muted">
            {{ t('settings.excludedHint') }}
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('settings.ocr') }}
      </template>
      <template #subtitle>
        {{ t('settings.ocrSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            :label="t('common.refresh')"
            outlined
            icon="pi pi-refresh"
            :loading="loadingOcr"
            @click="loadOcrStatus"
          />
          <div class="kv">
            <div class="key">
              {{ t('common.enabled') }}
            </div>
            <div class="value">
              {{ ocr.enabled ? t('common.yes') : t('common.no') }}
            </div>
            <div class="key">
              {{ t('common.available') }}
            </div>
            <div class="value">
              {{ ocr.available ? t('common.yes') : t('common.no') }}
            </div>
            <div class="key">
              {{ t('settings.tesseract') }}
            </div>
            <div class="value">
              {{ ocr.tesseract_version || '-' }}
            </div>
            <div class="key">
              {{ t('settings.command') }}
            </div>
            <div class="value">
              {{ ocr.tesseract_cmd || '-' }}
            </div>
            <div class="key">
              {{ t('settings.details') }}
            </div>
            <div class="value">
              {{ ocr.details || '-' }}
            </div>
          </div>
          <p class="muted">
            {{ t('settings.ocrHint') }}
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('demoData.title') }}
      </template>
      <template #subtitle>
        {{ t('demoData.subtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button
              :label="t('demoData.create')"
              icon="pi pi-plus-circle"
              :loading="loadingDemo"
              @click="handleCreateDemoData"
            />
            <Button
              :label="t('demoData.clear')"
              icon="pi pi-trash"
              outlined
              severity="secondary"
              :loading="clearingDemo"
              @click="handleClearDemoData"
            />
          </div>
          <p class="muted">
            {{ t('demoData.hint') }}
          </p>
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

import { get } from '../api'
import { post } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import { clearDemoData, createDemoData } from '../services/workspace-data'
import { useWorkspaceStore } from '../workspace-store'
import type {
  IndexRebuildResponse,
  IndexStatusResponse,
  SettingsLLMResponse,
  SettingsOCRResponse,
  TemplateMetaItem,
  TemplatesMetaResponse,
} from '../types'

defineProps({
  currentUser: {
    type: Object,
    default: () => ({}),
  },
})

const loading = ref(false)
const loadingTemplates = ref(false)
const loadingOcr = ref(false)
const loadingIndex = ref(false)
const rebuildingIndex = ref(false)
const loadingDemo = ref(false)
const clearingDemo = ref(false)
const toast = useToast()
const store = useWorkspaceStore()
const status = ref<SettingsLLMResponse>({
  primary_provider: '',
  active_provider: '',
  model: '',
  base_url: '',
  primary_healthy: false,
  fallback_enabled: true,
  llm_ready_for_generation: false,
  error_message: '',
})
const templates = ref<TemplateMetaItem[]>([])
const ocr = ref<SettingsOCRResponse>({ enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' })
const indexStatus = ref<IndexStatusResponse>({
  provider: {
    configured_provider: '',
    active_provider: 'none',
    status: 'disabled',
    index_mode: 'vector_degraded',
    demo_mode: true,
    semantic_search_ready: false,
    message: '',
    details: [],
  },
  summary: {
    document: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
    knowledge: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
    logbook: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
    photo: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
    prompt: { total: 0, pending: 0, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
  },
  failed_items: [],
})

const totalExcludedItems = computed(() =>
  (Object.values(indexStatus.value.summary) as Array<{ excluded?: number }>).reduce(
    (sum, item) => sum + (item.excluded ?? 0),
    0,
  )
)

async function loadStatus() {
  loading.value = true
  try {
    status.value = await get<SettingsLLMResponse>(apiPaths.settings.llm)
  } catch (error: unknown) {
    status.value = {
      primary_provider: 'unknown',
      active_provider: 'unknown',
      model: '',
      base_url: '',
      primary_healthy: false,
      fallback_enabled: true,
      llm_ready_for_generation: false,
      error_message: t('settings.unableToLoadLlm'),
    }
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.llmStatusFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    loading.value = false
  }
}

onMounted(loadStatus)

async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const payload = await get<TemplatesMetaResponse>(apiPaths.settings.templatesMeta)
    templates.value = payload?.templates || []
  } catch (error: unknown) {
    templates.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.templateLoadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    loadingTemplates.value = false
  }
}

onMounted(loadTemplates)

async function loadOcrStatus() {
  loadingOcr.value = true
  try {
    ocr.value = await get<SettingsOCRResponse>(apiPaths.settings.ocr)
  } catch (error: unknown) {
    ocr.value = { enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' }
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.ocrStatusFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    loadingOcr.value = false
  }
}

onMounted(loadOcrStatus)

async function loadIndexStatus() {
  loadingIndex.value = true
  try {
    indexStatus.value = await get<IndexStatusResponse>(apiPaths.index.status)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.indexStatusFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    loadingIndex.value = false
  }
}

async function rebuildAllIndexes() {
  rebuildingIndex.value = true
  try {
    const response = await post<IndexRebuildResponse>(apiPaths.index.rebuildAll)
    const failed = response.failed ?? 0
    const rebuilt = response.rebuilt ?? 0
    const detail = response.message || (failed > 0 ? t('settings.indexRebuildCompletedWithFailures') : t('settings.indexRebuildFinished'))
    toast.add({
      severity: failed > 0 ? 'warn' : 'success',
      summary: failed > 0 ? t('settings.indexRebuildNeedsAttention') : t('settings.indexRebuildFinished'),
      detail: t('settings.indexRebuildDetail', { detail, provider: response.provider.active_provider, rebuilt, failed }),
      life: 4000,
    })
    await loadIndexStatus()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.indexRebuildFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    rebuildingIndex.value = false
  }
}

onMounted(loadIndexStatus)

async function handleCreateDemoData() {
  loadingDemo.value = true
  try {
    const response = await createDemoData()
    await store.refreshAll({ force: true })
    toast.add({
      severity: response.created > 0 ? 'success' : 'info',
      summary: t('demoData.createSuccess'),
      detail: t('demoData.createDetail', { created: response.created, skipped: response.skipped }),
      life: 3500,
    })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('demoData.createFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    loadingDemo.value = false
  }
}

async function handleClearDemoData() {
  clearingDemo.value = true
  try {
    const response = await clearDemoData()
    await store.refreshAll({ force: true })
    toast.add({
      severity: 'success',
      summary: t('demoData.clearSuccess'),
      detail: t('demoData.clearDetail', { cleared: response.cleared }),
      life: 3500,
    })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('demoData.clearFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    clearingDemo.value = false
  }
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  flex-wrap: wrap;
}

.kv {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 10px 12px;
  padding: 12px;
  border-radius: 12px;
  background: #f7fafc;
}

.key {
  font-weight: 600;
  color: #3a4755;
}

.value {
  color: #1f2d3d;
  word-break: break-word;
}

.muted {
  margin: 0;
  color: #51606f;
  font-size: 13px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
