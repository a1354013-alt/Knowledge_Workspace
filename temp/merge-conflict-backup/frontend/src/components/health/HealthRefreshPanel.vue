<template>
  <div class="activity-block">
<<<<<<< HEAD
    <h3>{{ t('dashboard.recentActivity.title') }}</h3>
=======
    <h3>{{ t('health.lastSevenDays') }}</h3>
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
    <div class="activity-grid">
      <div
        v-for="item in activityItems"
        :key="item.label"
        class="activity-item"
      >
        <div class="activity-label">
          {{ item.label }}
        </div>
        <div
          class="activity-value"
          :class="item.className"
        >
          {{ item.value }}
        </div>
      </div>
    </div>
  </div>

  <div class="action-bar">
    <Button
      :label="t('common.refresh')"
      icon="pi pi-refresh"
      :loading="loading"
      @click="$emit('refresh')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'

import type { DashboardHealthViewModel } from '../../adapters/dashboard'
<<<<<<< HEAD
import { useI18n } from '../../i18n'
=======
import { t } from '../../i18n'
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71

const props = defineProps<{
  data: DashboardHealthViewModel
  loading: boolean
}>()

defineEmits<{
  refresh: []
}>()

const { t } = useI18n()

const activityItems = computed(() => [
<<<<<<< HEAD
  { label: t('dashboard.recentActivity.documentsAdded'), value: props.data.recent_activity.documents_added, className: '' },
  { label: t('dashboard.recentActivity.knowledgeAdded'), value: props.data.recent_activity.knowledge_added, className: '' },
  { label: t('dashboard.recentActivity.logbookAdded'), value: props.data.recent_activity.logbook_added, className: '' },
  { label: t('dashboard.recentActivity.autotestRuns'), value: props.data.recent_activity.autotest_runs, className: '' },
  { label: t('dashboard.recentActivity.autotestPassed'), value: props.data.recent_activity.autotest_passed, className: 'success' },
  { label: t('dashboard.recentActivity.autotestFailed'), value: props.data.recent_activity.autotest_failed, className: 'error' },
=======
  { label: t('health.documentsAdded'), value: props.data.recent_activity.documents_added, className: '' },
  { label: t('health.knowledgeAdded'), value: props.data.recent_activity.knowledge_added, className: '' },
  { label: t('health.logbookAdded'), value: props.data.recent_activity.logbook_added, className: '' },
  { label: t('health.autotestRuns'), value: props.data.recent_activity.autotest_runs, className: '' },
  { label: t('health.autotestPassed'), value: props.data.recent_activity.autotest_passed, className: 'success' },
  { label: t('health.autotestFailed'), value: props.data.recent_activity.autotest_failed, className: 'error' },
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
])
</script>

<style scoped>
.activity-block {
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.activity-block h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.activity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.activity-item {
  padding: 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  text-align: center;
}

.activity-label {
  font-size: 11px;
  font-weight: 600;
  color: #51606f;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.activity-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
}

.activity-value.success {
  color: #28a745;
}

.activity-value.error {
  color: #dc3545;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
</style>
