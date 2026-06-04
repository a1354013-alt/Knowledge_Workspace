<template>
  <div class="page-content generator-page">
    <header class="page-header">
      <h2>{{ t('generator.pageTitle') }}</h2>
      <p>{{ t('generator.pageSubtitle') }}</p>
    </header>

    <div class="grid">
      <Card>
        <template #title>
          {{ t('generator.cardTitle') }}
        </template>
        <template #subtitle>
          {{ t('generator.cardSubtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="row">
              <Button
                :label="t('generator.refreshTemplates')"
                outlined
                icon="pi pi-refresh"
                :loading="loadingTemplates"
                @click="loadTemplates"
              />
              <Dropdown
                v-model="selectedTemplate"
                :options="templates"
                option-label="label"
                option-value="value"
                :placeholder="t('generator.chooseTemplate')"
                class="picker"
              />
            </div>

            <div
              v-if="showNoTemplates"
              class="empty-state"
            >
              <strong>{{ t('generator.noTemplatesTitle') }}</strong>
              <p>{{ t('generator.noTemplatesDetail') }}</p>
            </div>

            <div
              v-else-if="!selectedTemplate"
              class="empty-state"
            >
              <strong>{{ t('generator.selectPrompt') }}</strong>
              <p>{{ t('generator.selectPromptDetail') }}</p>
            </div>

            <div
              v-if="selectedTemplate && fields.length"
              class="stack-md"
            >
              <div
                v-for="field in fields"
                :key="field"
                class="stack-xs"
              >
                <label class="field-label">{{ field }}</label>
                <Textarea
                  v-model="inputs[field]"
                  rows="2"
                  :placeholder="field"
                  auto-resize
                />
              </div>
            </div>

            <div class="row">
              <Button
                :label="t('common.generate')"
                icon="pi pi-bolt"
                :loading="generating"
                :disabled="!selectedTemplate"
                @click="generate"
              />
              <Button
                :label="t('common.clearOutput')"
                outlined
                severity="secondary"
                :disabled="generating"
                @click="output = ''"
              />
            </div>

            <div
              v-if="output"
              class="result-box"
            >
              <h3>{{ t('generator.output') }}</h3>
              <pre class="mono">{{ output }}</pre>
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
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'

import { get, post } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import type { GenerateRequest, GenerateResponse, TemplateMetaItem, TemplatesMetaResponse } from '../types'

const toast = useToast()

const loadingTemplates = ref(false)
const generating = ref(false)
const templates = ref<TemplateMetaItem[]>([])
const selectedTemplate = ref('')
const templateFieldsByType = ref<Record<string, string[]>>({})

const inputs = ref<Record<string, string>>({})
const output = ref('')

const fields = computed(() => {
  const list = templateFieldsByType.value?.[selectedTemplate.value] || []
  return Array.isArray(list) ? list : []
})
const showNoTemplates = computed(() => !loadingTemplates.value && templates.value.length === 0)

async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const response = await get<TemplatesMetaResponse>(apiPaths.settings.templatesMeta)
    templates.value = response.templates || []
    const next: Record<string, string[]> = {}
    for (const item of templates.value) {
      next[item.value] = item.fields || []
    }
    templateFieldsByType.value = next
  } catch (error: unknown) {
    templates.value = []
    templateFieldsByType.value = {}
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('generator.loadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    loadingTemplates.value = false
  }
}

async function generate() {
  if (!selectedTemplate.value) {
    return
  }
  generating.value = true
  try {
    const payload: GenerateRequest = {
      template_type: selectedTemplate.value,
      inputs: inputs.value || {},
    }
    const response = await post<GenerateResponse, GenerateRequest>(apiPaths.generator.generate, payload)
    output.value = response.content || ''
    if (!output.value) {
      toast.add({ severity: 'warn', summary: t('generator.noOutput'), detail: t('generator.emptyOutput'), life: 3000 })
    }
  } catch (error: unknown) {
    output.value = ''
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('generator.generateFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4500 })
  } finally {
    generating.value = false
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.page-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.generator-page {
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

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stack-xs {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.picker {
  min-width: min(520px, 100%);
}

.field-label {
  font-weight: 600;
}

.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
}

.empty-state {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
  color: #51606f;
  line-height: 1.6;
}

.empty-state strong {
  display: block;
  color: #1f2f46;
  margin-bottom: 4px;
}

.empty-state p {
  margin: 0;
}

.mono {
  white-space: pre-wrap;
  margin: 8px 0 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}
</style>
