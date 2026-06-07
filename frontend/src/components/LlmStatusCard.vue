<template>
  <Card>
    <template #title>
      {{ t('llmStatus.title') }}
    </template>
    <template #subtitle>
      {{ t('llmStatus.subtitle') }}
    </template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <Button
            :label="t('common.refresh')"
            icon="pi pi-refresh"
            outlined
            :loading="loading"
            @click="loadStatus"
          />
          <Tag
            :severity="status.llm_ready_for_generation ? 'success' : (status.fallback_enabled ? 'warn' : 'danger')"
            :value="statusLabel"
          />
        </div>

        <div class="kv">
          <div class="key">
            {{ t('llmStatus.provider') }}
          </div>
          <div class="value">
            {{ status.active_provider || status.primary_provider || '-' }}
          </div>
          <div class="key">
            {{ t('llmStatus.model') }}
          </div>
          <div class="value">
            {{ status.model || '-' }}
          </div>
          <div class="key">
            {{ t('llmStatus.fallback') }}
          </div>
          <div class="value">
            {{ status.fallback_enabled ? t('common.enabled') : t('common.disabled') }}
          </div>
        </div>

        <p class="muted">
          {{ status.error_message || t('llmStatus.availableHint') }}
        </p>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

import { get } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import type { SettingsLLMResponse } from '../types'

const emptyStatus: SettingsLLMResponse = {
  primary_provider: '',
  active_provider: '',
  model: '',
  base_url: '',
  primary_healthy: false,
  fallback_enabled: false,
  llm_ready_for_generation: false,
  error_message: '',
}

const loading = ref(false)
const status = ref<SettingsLLMResponse>({ ...emptyStatus })

const statusLabel = computed(() => {
  if (status.value.llm_ready_for_generation) {
    return t('llmStatus.available')
  }
  if (status.value.fallback_enabled) {
    return t('llmStatus.fallbackMode')
  }
  return t('llmStatus.unavailable')
})

async function loadStatus() {
  loading.value = true
  try {
    const payload = await get<SettingsLLMResponse>(apiPaths.settings.llm)
    status.value = { ...emptyStatus, ...(payload || {}) }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    status.value = {
      ...emptyStatus,
      llm_ready_for_generation: false,
      error_message: apiError?.message || t('common.requestFailed'),
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
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

.kv {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 8px 12px;
  padding: 12px;
  border-radius: 14px;
  background: #f7fafc;
}

.key {
  font-weight: 600;
  color: #35536a;
}

.value {
  color: #1f2d3d;
  word-break: break-word;
}

.muted {
  margin: 0;
  color: #51606f;
  line-height: 1.6;
}
</style>
