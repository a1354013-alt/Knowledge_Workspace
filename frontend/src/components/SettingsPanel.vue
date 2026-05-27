<template>
  <div class="grid">
    <Card>
      <template #title>
        Local AI provider
      </template>
      <template #subtitle>
        Ollama is the default provider. A noop fallback keeps retrieval endpoints alive, but it does not make generation ready.
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            label="Refresh"
            outlined
            icon="pi pi-refresh"
            :loading="loading"
            @click="loadStatus"
          />
          <div class="kv">
            <div class="key">
              Primary provider
            </div>
            <div class="value">
              {{ status.primary_provider || '-' }}
            </div>
            <div class="key">
              Active provider
            </div>
            <div class="value">
              {{ status.active_provider || '-' }}
            </div>
            <div class="key">
              Model
            </div>
            <div class="value">
              {{ status.model || '-' }}
            </div>
            <div class="key">
              Base URL
            </div>
            <div class="value">
              {{ status.base_url || '-' }}
            </div>
            <div class="key">
              Primary healthy
            </div>
            <div class="value">
              {{ status.primary_healthy ? 'yes' : 'no' }}
            </div>
            <div class="key">
              Fallback
            </div>
            <div class="value">
              {{ status.fallback_enabled ? 'enabled' : 'disabled' }}
            </div>
            <div class="key">
              Ready
            </div>
            <div class="value">
              {{ status.llm_ready_for_generation ? 'yes' : 'no' }}
            </div>
            <div class="key">
              Error
            </div>
            <div class="value">
              {{ status.error_message || '-' }}
            </div>
          </div>
          <p class="muted">
            Start Ollama: `ollama serve` and pull a model: `ollama pull llama3.1`. If the active provider is `none`, generation is unavailable until a real provider is healthy.
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        Prompt templates
      </template>
      <template #subtitle>
        Engineering-focused templates for bug reports, troubleshooting notes, PR descriptions, and postmortems.
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            label="Refresh"
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
              Available
            </div>
            <div class="value">
              {{ templates.map((t) => t.value).join(', ') }}
            </div>
          </div>
          <p class="muted">
            Use `Generate` in the Knowledge tab via API: `POST /api/generate` with `template_type` and `inputs`.
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        Index health
      </template>
      <template #subtitle>
        The current provider is exposed here so the demo/fallback hash index is not mistaken for production semantic search.
      </template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button
              label="Refresh"
              outlined
              icon="pi pi-refresh"
              :loading="loadingIndex"
              @click="loadIndexStatus"
            />
            <Button
              label="Rebuild all indexes"
              icon="pi pi-wrench"
              :loading="rebuildingIndex"
              @click="rebuildAllIndexes"
            />
          </div>
          <div class="kv">
            <div class="key">
              Provider
            </div>
            <div class="value">
              {{ indexStatus.provider.active_provider || '-' }}
            </div>
            <div class="key">
              Mode
            </div>
            <div class="value">
              {{ indexStatus.provider.demo_mode ? 'demo / fallback' : 'semantic-ready' }}
            </div>
            <div class="key">
              Status
            </div>
            <div class="value">
              {{ indexStatus.provider.status || '-' }}
            </div>
            <div class="key">
              Message
            </div>
            <div class="value">
              {{ indexStatus.provider.message || '-' }}
            </div>
            <div class="key">
              Excluded
            </div>
            <div class="value">
              {{ totalExcludedItems }}
            </div>
          </div>
          <p class="muted">
            Archived or inactive items are tracked as `excluded`, so they do not count as pending indexing work.
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        OCR
      </template>
      <template #subtitle>
        Extract text from photos for search. Controlled by backend environment variables.
      </template>
      <template #content>
        <div class="stack-md">
          <Button
            label="Refresh"
            outlined
            icon="pi pi-refresh"
            :loading="loadingOcr"
            @click="loadOcrStatus"
          />
          <div class="kv">
            <div class="key">
              Enabled
            </div>
            <div class="value">
              {{ ocr.enabled ? 'yes' : 'no' }}
            </div>
            <div class="key">
              Available
            </div>
            <div class="value">
              {{ ocr.available ? 'yes' : 'no' }}
            </div>
            <div class="key">
              Tesseract
            </div>
            <div class="value">
              {{ ocr.tesseract_version || '-' }}
            </div>
            <div class="key">
              Command
            </div>
            <div class="value">
              {{ ocr.tesseract_cmd || '-' }}
            </div>
            <div class="key">
              Details
            </div>
            <div class="value">
              {{ ocr.details || '-' }}
            </div>
          </div>
          <p class="muted">
            OCR requires both Python deps (pytesseract/Pillow) and a system Tesseract binary. Set `OCR_ENABLED=0` to disable OCR, or set
            `OCR_TESSERACT_CMD=/path/to/tesseract` to point to the binary.
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
import type { IndexStatusResponse, SettingsLLMResponse, SettingsOCRResponse, TemplateMetaItem, TemplatesMetaResponse } from '../types'

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
const toast = useToast()
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
      error_message: 'Unable to load LLM status.',
    }
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'LLM status failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
    toast.add({ severity: 'error', summary: 'Template load failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
    toast.add({ severity: 'error', summary: 'OCR status failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
    toast.add({ severity: 'error', summary: 'Index status failed', detail: apiError?.message || 'Request failed.', life: 3500 })
  } finally {
    loadingIndex.value = false
  }
}

async function rebuildAllIndexes() {
  rebuildingIndex.value = true
  try {
    const response = await post<{ message: string }>(apiPaths.index.rebuildAll)
    toast.add({ severity: 'success', summary: 'Index rebuild started', detail: response.message || 'Index rebuild finished.', life: 3500 })
    await loadIndexStatus()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Index rebuild failed', detail: apiError?.message || 'Request failed.', life: 3500 })
  } finally {
    rebuildingIndex.value = false
  }
}

onMounted(loadIndexStatus)
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
