<template>
  <div class="autotest-block">
    <h3>{{ t('health.recentRunsTitle') }}</h3>
    <div
      v-if="runs.length > 0"
      class="recent-runs-table kw-scroll-panel"
    >
      <div
        v-for="run in runs"
        :key="run.id"
        class="run-row"
      >
        <div class="run-info">
          <div class="run-name">
            {{ run.project_name }}
          </div>
          <div class="run-time">
            {{ formatDateTime(run.created_at) }}
          </div>
        </div>
        <div class="run-status">
          <HealthStatusBadge :status="run.status" />
        </div>
      </div>
    </div>
    <div
      v-else
      class="empty-runs"
    >
      <EmptyStateBlock
        icon="pi pi-check-square"
        :title="t('health.emptyRecentRunsTitle')"
        :description="t('health.emptyRecentRunsDescription')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DashboardHealthViewModel } from '../../adapters/dashboard'
import { useI18n } from '../../i18n'
import EmptyStateBlock from '../common/EmptyStateBlock.vue'
import HealthStatusBadge from './HealthStatusBadge.vue'
import { formatDateTime } from './useProjectHealth'

defineProps<{
  runs: DashboardHealthViewModel['autotest']['recent_runs']
}>()

const { t } = useI18n()
</script>

<style scoped>
.autotest-block {
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.autotest-block h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.recent-runs-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
}

.run-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.run-info {
  flex: 1;
  min-width: 0;
}

.run-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-time {
  font-size: 11px;
  color: #51606f;
}

.run-status {
  margin-left: 12px;
}

.empty-runs {
  padding-top: 8px;
}
</style>
