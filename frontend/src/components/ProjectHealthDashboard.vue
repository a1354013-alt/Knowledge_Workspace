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
            <section class="health-actions surface-card">
              <div class="health-actions-copy">
                <h3>{{ t('health.detailActionsTitle') }}</h3>
                <p>{{ t('health.detailActionsDescription') }}</p>
              </div>
              <div class="health-actions-row">
                <Button
                  :label="t('health.openStatusDialog')"
                  icon="pi pi-book"
                  severity="secondary"
                  outlined
                  @click="openHealthDialog('status')"
                />
                <Button
                  :label="t('health.openRunsDialog')"
                  icon="pi pi-history"
                  severity="secondary"
                  outlined
                  @click="openHealthDialog('runs')"
                />
                <Button
                  :label="t('health.openActivityDialog')"
                  icon="pi pi-calendar"
                  severity="secondary"
                  outlined
                  @click="openHealthDialog('activity')"
                />
              </div>
            </section>
          </div>
        </div>
      </template>
    </Card>
  </div>

  <Dialog
    :visible="activeHealthDialog !== null"
    modal
    closable
    close-on-escape
    dismissable-mask
    class="health-detail-dialog"
    :header="activeDialogTitle"
    :style="{ width: 'min(960px, calc(100vw - 32px))' }"
    @update:visible="onDialogVisibilityChange"
  >
    <div
      v-if="data"
      class="health-dialog-panel"
    >
      <KnowledgeStatusPanel
        v-if="activeHealthDialog === 'status'"
        :data="data"
      />
      <AutoTestRunsPanel
        v-else-if="activeHealthDialog === 'runs'"
        :runs="data.autotest.recent_runs"
      />
      <ActivityLogPanel
        v-else-if="activeHealthDialog === 'activity'"
        :data="data"
        :loading="loading"
        @refresh="loadDashboard"
      />
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import { computed, ref } from 'vue'

import ActivityLogPanel from './health/ActivityLogPanel.vue'
import AutoTestRunsPanel from './health/AutoTestRunsPanel.vue'
import HealthSummaryCards from './health/HealthSummaryCards.vue'
import KnowledgeStatusPanel from './health/KnowledgeStatusPanel.vue'
import LlmStatusCard from './LlmStatusCard.vue'
import RecentWorkspaceItems from './RecentWorkspaceItems.vue'
import { useProjectHealth } from './health/useProjectHealth'
import { t } from '../i18n'

const { data, error, loading, loadDashboard } = useProjectHealth()

type HealthDialogKey = 'status' | 'runs' | 'activity'

const activeHealthDialog = ref<HealthDialogKey | null>(null)
const activeDialogTitle = computed(() => {
  if (activeHealthDialog.value === 'status') {
    return t('health.knowledgeByStatus')
  }
  if (activeHealthDialog.value === 'runs') {
    return t('health.recentRunsTitle')
  }
  if (activeHealthDialog.value === 'activity') {
    return t('health.lastSevenDays')
  }
  return ''
})

function openHealthDialog(dialog: HealthDialogKey) {
  activeHealthDialog.value = dialog
}

function onDialogVisibilityChange(visible: boolean) {
  if (!visible) {
    activeHealthDialog.value = null
  }
}
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

.health-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  padding: 16px;
}

.health-actions-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.health-actions-copy h3 {
  margin: 0;
  color: #1b2d42;
  font-size: 16px;
}

.health-actions-copy p {
  margin: 0;
  color: #51606f;
  line-height: 1.5;
}

.health-actions-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.health-dialog-panel {
  min-height: 0;
}

:deep(.health-detail-dialog) {
  max-height: min(80vh, 720px);
}

:deep(.health-detail-dialog .p-dialog-content) {
  overflow-y: auto;
}

@media (max-width: 768px) {
  .dashboard-content {
    gap: 16px;
  }

  .insights-grid {
    grid-template-columns: 1fr;
  }

  .health-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .health-actions-row {
    justify-content: stretch;
  }

  .health-actions-row :deep(button) {
    width: 100%;
  }
}

@media (max-width: 640px) {
  :deep(.health-detail-dialog) {
    width: calc(100vw - 24px) !important;
  }
}
</style>
