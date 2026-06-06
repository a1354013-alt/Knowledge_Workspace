<template>
  <Card>
    <template #title>
      {{ t('knowledge.askTitle') }}
    </template>
    <template #subtitle>
      {{ t('knowledge.askSubtitle') }}
    </template>
    <template #content>
      <div class="stack-md">
        <Textarea
          :model-value="question"
          rows="5"
          :placeholder="t('knowledge.askPlaceholder')"
          @update:model-value="$emit('update:question', $event)"
        />
        <div class="row">
          <Button
            :label="t('common.ask')"
            icon="pi pi-send"
            :loading="asking"
            @click="$emit('submit')"
          />
          <Button
            :label="t('common.clear')"
            outlined
            severity="secondary"
            :disabled="asking"
            @click="$emit('clear')"
          />
        </div>

        <div
          v-if="answer"
          class="result-box"
        >
          <h3>{{ t('knowledge.answer') }}</h3>
          <p class="answer">
            {{ answer }}
          </p>
          <div
            v-if="sources.length"
            class="stack-sm"
          >
            <h4>{{ t('knowledge.sources') }}</h4>
            <article
              v-for="(source, index) in sources"
              :key="index"
              class="source-card"
            >
              <strong>{{ source.title }}</strong>
              <p class="muted">
                {{ formatSourceType(source.source_type) }} · {{ source.location || '-' }}
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
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Textarea from 'primevue/textarea'

import { useI18n } from '../../i18n'
import type { Source } from '../../types'

defineProps<{
  answer: string
  asking: boolean
  question: string
  sources: Source[]
}>()

defineEmits<{
  clear: []
  submit: []
  'update:question': [value: string]
}>()

const { t } = useI18n()

function formatSourceType(value: Source['source_type']): string {
  const labels: Record<Source['source_type'], string> = {
    knowledge: 'Knowledge',
    logbook: 'Logbook',
    prompt: 'Prompt',
    document: 'Document',
    photo: 'Photo',
  }
  return labels[value] || value
}
</script>

<style scoped>
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
</style>
