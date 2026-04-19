<template>
  <div class="grid">
    <Card>
      <template #title>Template generator</template>
      <template #subtitle>Generate structured engineering docs (bug reports, troubleshooting notes, PR descriptions, postmortems).</template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button label="Refresh templates" outlined icon="pi pi-refresh" :loading="loadingTemplates" @click="loadTemplates" />
            <Dropdown
              v-model="selectedTemplate"
              :options="templates"
              option-label="label"
              option-value="value"
              placeholder="Choose a template..."
              class="picker"
            />
          </div>

          <div v-if="selectedTemplate && fields.length" class="stack-md">
            <div v-for="field in fields" :key="field" class="stack-xs">
              <label class="field-label">{{ field }}</label>
              <Textarea v-model="inputs[field]" rows="2" :placeholder="field" auto-resize />
            </div>
          </div>

          <div class="row">
            <Button label="Generate" icon="pi pi-bolt" :loading="generating" :disabled="!selectedTemplate" @click="generate" />
            <Button label="Clear output" outlined severity="secondary" :disabled="generating" @click="output = ''" />
          </div>

          <div v-if="output" class="result-box">
            <h3>Output</h3>
            <pre class="mono">{{ output }}</pre>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'

import { apiClient } from '../api'

const toast = useToast()

const loadingTemplates = ref(false)
const generating = ref(false)
const templates = ref([])
const selectedTemplate = ref('')
const templateFieldsByType = ref({})

const inputs = ref({})
const output = ref('')

const fields = computed(() => {
  const list = templateFieldsByType.value?.[selectedTemplate.value] || []
  return Array.isArray(list) ? list : []
})

async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const response = await apiClient.get('/api/meta/templates')
    templates.value = response.templates || []
    const next = {}
    for (const item of templates.value) {
      next[item.value] = item.fields || []
    }
    templateFieldsByType.value = next
  } catch (error) {
    templates.value = []
    templateFieldsByType.value = {}
    toast.add({ severity: 'error', summary: 'Load failed', detail: error.message, life: 4000 })
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
    const payload = {
      template_type: selectedTemplate.value,
      inputs: inputs.value || {},
    }
    const response = await apiClient.post('/api/generate', payload)
    output.value = response.content || ''
    if (!output.value) {
      toast.add({ severity: 'warn', summary: 'No output', detail: 'Generator returned empty content.', life: 3000 })
    }
  } catch (error) {
    output.value = ''
    toast.add({ severity: 'error', summary: 'Generate failed', detail: error.message, life: 4500 })
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

.mono {
  white-space: pre-wrap;
  margin: 8px 0 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}
</style>

