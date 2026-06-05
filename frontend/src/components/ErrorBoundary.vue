<template>
  <div
    v-if="hasError"
    class="error-boundary"
  >
    <div class="error-content">
      <i class="pi pi-exclamation-triangle error-icon" />
      <h2 class="error-title">
        {{ t('errorBoundary.title') }}
      </h2>
      <p class="error-message">
        {{ errorMessage }}
      </p>
      <Button
        :label="t('errorBoundary.tryAgain')"
        icon="pi pi-refresh"
        @click="retry"
      />
      <Button
        :label="t('errorBoundary.goHome')"
        icon="pi pi-home"
        severity="secondary"
        @click="goHome"
      />
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'

import { t } from '../i18n'

interface Props {
  retryCount?: number
  maxRetries?: number
}

const props = withDefaults(defineProps<Props>(), {
  retryCount: 0,
  maxRetries: 3,
})

const emit = defineEmits<{
  (e: 'error', error: Error): void
  (e: 'retry'): void
}>()

const hasError = ref(false)
const errorMessage = ref(t('errorBoundary.unexpected'))

// Listen for global error events
function handleError(error: ErrorEvent | PromiseRejectionEvent) {
  hasError.value = true
  
  if ('error' in error && error.error instanceof Error) {
    errorMessage.value = error.error.message
  } else if ('reason' in error) {
    errorMessage.value = String(error.reason)
  } else {
    errorMessage.value = t('errorBoundary.unexpected')
  }
  
  emit('error', new Error(errorMessage.value))
}

function retry() {
  if (props.retryCount < props.maxRetries) {
    hasError.value = false
    emit('retry')
  } else {
    errorMessage.value = t('errorBoundary.maxRetries')
  }
}

function goHome() {
  window.location.href = '/'
}

// Setup global error listeners
watch(
  () => hasError.value,
  (newVal) => {
    if (newVal) {
      window.addEventListener('error', handleError as EventListener)
      window.addEventListener('unhandledrejection', handleError as EventListener)
    } else {
      window.removeEventListener('error', handleError as EventListener)
      window.removeEventListener('unhandledrejection', handleError as EventListener)
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 48px 24px;
  background: linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%);
  border-radius: 16px;
  border: 1px solid #fecaca;
}

.error-content {
  text-align: center;
  max-width: 480px;
}

.error-icon {
  font-size: 64px;
  color: #ef4444;
  margin-bottom: 16px;
}

.error-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 12px 0;
}

.error-message {
  font-size: 16px;
  color: #6b7280;
  margin: 0 0 24px 0;
  line-height: 1.6;
}
</style>
