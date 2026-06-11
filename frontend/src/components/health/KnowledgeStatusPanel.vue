<template>
  <div class="status-blocks">
    <div class="status-block">
      <h3>{{ t('health.knowledgeByStatus') }}</h3>
      <div class="status-list">
        <div
          v-for="(count, status) in data.knowledge.by_status"
          :key="status"
          class="status-item"
        >
          <span class="status-name">{{ capitalizeStatus(status) }}</span>
          <div class="status-bar">
            <div
              class="status-fill"
              :class="`status-${status}`"
              :style="{ width: calculateStatusWidth(count, data.knowledge.total) }"
            />
          </div>
          <span class="status-count">{{ count }}</span>
        </div>
      </div>
    </div>

    <div class="status-block">
      <h3>{{ t('health.documentIndexStatus') }}</h3>
      <div class="status-list">
        <div
          v-for="row in documentRows"
          :key="row.label"
          class="status-item"
        >
          <span class="status-name">{{ row.label }}</span>
          <div class="status-bar">
            <div
              class="status-fill"
              :class="row.className"
              :style="{ width: calculateStatusWidth(row.count, row.total) }"
            />
          </div>
          <span class="status-count">{{ row.count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { DashboardHealthViewModel } from '../../adapters/dashboard'
import { useI18n } from '../../i18n'
import { calculateStatusWidth, capitalizeStatus } from './useProjectHealth'

const props = defineProps<{
  data: DashboardHealthViewModel
}>()
const { t } = useI18n()

const documentRows = computed(() => [
  {
    className: 'status-indexed',
    count: props.data.documents.indexed,
    label: t('common.indexed'),
    total: props.data.documents.total,
  },
  {
    className: 'status-pending',
    count: props.data.documents.pending,
    label: t('common.pending'),
    total: props.data.documents.total,
  },
  {
    className: 'status-failed',
    count: props.data.documents.failed_documents,
    label: t('common.failed'),
    total: props.data.documents.total,
  },
  {
    className: 'status-archived',
    count: props.data.documents.archived_documents,
    label: t('common.archivedStatus'),
    total: props.data.documents.total + props.data.documents.archived_documents,
  },
])
</script>

<style scoped>
.status-blocks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.status-block {
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.status-block h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: grid;
  grid-template-columns: 80px 1fr 40px;
  align-items: center;
  gap: 12px;
}

.status-name {
  font-size: 12px;
  font-weight: 500;
  color: #51606f;
}

.status-bar {
  height: 8px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  overflow: hidden;
}

.status-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.status-draft {
  background: #ffc107;
}

.status-reviewed {
  background: #17a2b8;
}

.status-verified {
  background: #28a745;
}

.status-archived {
  background: #6c757d;
}

.status-indexed {
  background: #28a745;
}

.status-pending {
  background: #ffc107;
}

.status-failed {
  background: #dc3545;
}

.status-count {
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: #1a1a1a;
  min-width: 40px;
}
</style>
