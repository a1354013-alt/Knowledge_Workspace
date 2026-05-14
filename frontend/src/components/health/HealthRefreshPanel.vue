<template>
  <div class="activity-block">
    <h3>Last 7 Days Activity</h3>
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
      label="Refresh"
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

const props = defineProps<{
  data: DashboardHealthViewModel
  loading: boolean
}>()

defineEmits<{
  refresh: []
}>()

const activityItems = computed(() => [
  { label: 'Documents Added', value: props.data.recent_activity.documents_added, className: '' },
  { label: 'Knowledge Added', value: props.data.recent_activity.knowledge_added, className: '' },
  { label: 'Logbook Added', value: props.data.recent_activity.logbook_added, className: '' },
  { label: 'AutoTest Runs', value: props.data.recent_activity.autotest_runs, className: '' },
  { label: 'AutoTest Passed', value: props.data.recent_activity.autotest_passed, className: 'success' },
  { label: 'AutoTest Failed', value: props.data.recent_activity.autotest_failed, className: 'error' },
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
