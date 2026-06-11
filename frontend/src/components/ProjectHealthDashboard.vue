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
            <div class="insights-grid">
              <LlmStatusCard />
              <RecentWorkspaceItems />
            </div>
            <section class="health-tabs surface-card">
              <div class="health-tab-list">
                <button
                  v-for="tab in healthTabs"
                  :key="tab.key"
                  type="button"
                  class="health-tab"
                  :class="{ 'health-tab-active': activeHealthTab === tab.key }"
                  @click="activeHealthTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>
              <div class="health-tab-panel">
                <HealthStatusSections
                  v-if="activeHealthTab === 'status'"
                  :data="data"
                />
                <HealthRecentRuns
                  v-else-if="activeHealthTab === 'runs'"
                  :runs="data.autotest.recent_runs"
                />
                <HealthRefreshPanel
                  v-else
                  :data="data"
                  :loading="loading"
                  @refresh="loadDashboard"
                />
              </div>
            </section>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import { computed, ref } from 'vue'

import HealthRecentRuns from './health/HealthRecentRuns.vue'
import HealthRefreshPanel from './health/HealthRefreshPanel.vue'
import HealthStatusSections from './health/HealthStatusSections.vue'
import HealthSummaryCards from './health/HealthSummaryCards.vue'
import LlmStatusCard from './LlmStatusCard.vue'
import RecentWorkspaceItems from './RecentWorkspaceItems.vue'
import { useProjectHealth } from './health/useProjectHealth'
import { t } from '../i18n'

const { data, error, loading, loadDashboard } = useProjectHealth()
const activeHealthTab = ref<'status' | 'runs' | 'activity'>('status')
const healthTabs = computed(() => [
  { key: 'status' as const, label: t('health.knowledgeByStatus') },
  { key: 'runs' as const, label: t('health.recentRunsTitle') },
  { key: 'activity' as const, label: t('health.lastSevenDays') },
])
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.stack-lg {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 0;
  min-width: 0;
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
  gap: 16px;
  min-height: 0;
  min-width: 0;
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-height: 0;
  min-width: 0;
}

.health-tabs {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  padding: 6px;
}

.health-tab-list {
  display: flex;
  gap: 6px;
  flex: 0 0 auto;
  overflow-x: auto;
}

.health-tab {
  border: 0;
  border-radius: 8px;
  padding: 9px 12px;
  background: transparent;
  color: #33536d;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}

.health-tab-active {
  background: #fff;
  color: #1b4d8e;
  box-shadow: 0 6px 12px rgba(31, 76, 132, 0.12);
}

.health-tab-panel {
  min-height: 0;
  max-height: 360px;
  overflow: auto;
  padding: 10px;
}

@media (max-width: 768px) {
  .dashboard-content {
    gap: 16px;
  }

  .insights-grid {
    grid-template-columns: 1fr;
  }
}
</style>
