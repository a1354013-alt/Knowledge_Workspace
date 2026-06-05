<template>
  <div class="grid">
    <Card>
      <template #title>
        {{ t('health.title') }}
      </template>
      <template #subtitle>
        {{ t('health.subtitle') }}
      </template>
      <template #content>
        <div class="stack-lg">
          <div
            v-if="loading"
            class="loading-state"
          >
            <div class="spinner" />
            <p>{{ t('health.loadingMetrics') }}</p>
          </div>

          <div
            v-else-if="error"
            class="error-state"
          >
            <p class="error-message">
              {{ error }}
            </p>
            <Button
              :label="t('health.retry')"
              icon="pi pi-refresh"
              @click="loadDashboard"
            />
          </div>

          <div
            v-else-if="!data"
            class="empty-state"
          >
            <p>{{ t('health.noData') }}</p>
          </div>

          <div
            v-else
            class="dashboard-content"
          >
            <HealthSummaryCards :data="data" />
            <HealthStatusSections :data="data" />
            <HealthRecentRuns :runs="data.autotest.recent_runs" />
            <HealthRefreshPanel
              :data="data"
              :loading="loading"
              @refresh="loadDashboard"
            />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'

import HealthRecentRuns from './health/HealthRecentRuns.vue'
import HealthRefreshPanel from './health/HealthRefreshPanel.vue'
import HealthStatusSections from './health/HealthStatusSections.vue'
import HealthSummaryCards from './health/HealthSummaryCards.vue'
import { useProjectHealth } from './health/useProjectHealth'
import { t } from '../i18n'

const { data, error, loading, loadDashboard } = useProjectHealth()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.stack-lg {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.loading-state,
.error-state,
.empty-state {
  padding: 32px 16px;
  text-align: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(69, 138, 255, 0.2);
  border-top-color: #458aff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-state {
  background: rgba(255, 76, 76, 0.1);
  border: 1px solid rgba(255, 76, 76, 0.3);
}

.error-message {
  color: #ff4c4c;
  margin: 0 0 12px 0;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 768px) {
  .dashboard-content {
    gap: 16px;
  }
}
</style>
