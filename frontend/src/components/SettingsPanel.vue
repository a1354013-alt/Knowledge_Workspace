<template>
  <div class="grid">
    <Card>
      <template #title>
        Local AI provider
      </template>
      <template #subtitle>
        Ollama is the default provider. If it is down, the workspace keeps working in fallback mode.
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
              Provider
            </div>
            <div class="value">
              {{ status.provider || '-' }}
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
              Healthy
            </div>
            <div class="value">
              {{ status.healthy ? 'yes' : 'no' }}
            </div>
            <div class="key">
              Fallback
            </div>
            <div class="value">
              {{ status.fallback_mode ? 'enabled' : 'disabled' }}
            </div>
          </div>
          <p class="muted">
            Start Ollama: `ollama serve` and pull a model: `ollama pull llama3.1`.
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
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'

import { get } from '../api'
import type { SettingsLLMResponse, SettingsOCRResponse, TemplateMetaItem, TemplatesMetaResponse } from '../types'

defineProps({
  currentUser: {
    type: Object,
    default: () => ({}),
  },
})

const loading = ref(false)
const loadingTemplates = ref(false)
const loadingOcr = ref(false)
const toast = useToast()
const status = ref<SettingsLLMResponse>({
  provider: '',
  model: '',
  base_url: '',
  healthy: false,
  fallback_mode: true,
})
const templates = ref<TemplateMetaItem[]>([])
const ocr = ref<SettingsOCRResponse>({ enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' })

async function loadStatus() {
  loading.value = true
  try {
    status.value = await get<SettingsLLMResponse>('/api/settings/llm')
  } catch (error: unknown) {
    status.value = { provider: 'unknown', model: '', base_url: '', healthy: false, fallback_mode: true }
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
    const payload = await get<TemplatesMetaResponse>('/api/meta/templates')
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
    ocr.value = await get<SettingsOCRResponse>('/api/settings/ocr')
  } catch (error: unknown) {
    ocr.value = { enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' }
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'OCR status failed', detail: apiError?.message || 'Request failed.', life: 3500 })
  } finally {
    loadingOcr.value = false
  }
}

onMounted(loadOcrStatus)
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
