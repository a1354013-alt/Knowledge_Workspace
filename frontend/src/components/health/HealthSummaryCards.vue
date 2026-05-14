<template>
  <div class="cards-row">
    <div class="summary-card">
      <div class="card-header">
        <span class="card-label">Knowledge Total</span>
        <i class="pi pi-book" />
      </div>
      <div class="card-value">
        {{ data.knowledge.total }}
      </div>
      <div class="card-detail">
        <span
          v-for="(count, status) in data.knowledge.by_status"
          :key="status"
          class="status-badge"
        >
          {{ status }}: {{ count }}
        </span>
      </div>
    </div>

    <div class="summary-card">
      <div class="card-header">
        <span class="card-label">Logbook Resolution Rate</span>
        <i class="pi pi-list" />
      </div>
      <div class="card-value">
        {{ formatPercentage(data.logbook.resolution_rate) }}
      </div>
      <div class="card-detail">
        {{ data.logbook.with_solution }} / {{ data.logbook.total }} with solution
      </div>
    </div>

    <div class="summary-card">
      <div class="card-header">
        <span class="card-label">AutoTest Pass Rate</span>
        <i class="pi pi-check-circle" />
      </div>
      <div class="card-value">
        {{ formatPercentage(data.autotest.pass_rate) }}
      </div>
      <div class="card-detail">
        {{ data.autotest.passed }} / {{ data.autotest.total_runs }} passed
      </div>
    </div>

    <div class="summary-card">
      <div class="card-header">
        <span class="card-label">Document Index Rate</span>
        <i class="pi pi-file" />
      </div>
      <div class="card-value">
        {{ formatPercentage(documentIndexRate) }}
      </div>
      <div class="card-detail">
        {{ data.documents.indexed }} / {{ data.documents.total }} indexed
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { DashboardHealthViewModel } from '../../adapters/dashboard'
import { formatPercentage } from './useProjectHealth'

const props = defineProps<{
  data: DashboardHealthViewModel
}>()

const documentIndexRate = computed(() => {
  if (props.data.documents.total === 0) {
    return 0
  }
  return (props.data.documents.indexed / props.data.documents.total) * 100
})
</script>

<style scoped>
.cards-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(69, 138, 255, 0.08) 0%, rgba(0, 184, 148, 0.08) 100%);
  border: 1px solid rgba(69, 138, 255, 0.15);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  color: #51606f;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-header i {
  color: #458aff;
  font-size: 18px;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
}

.card-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #51606f;
}

.status-badge {
  padding: 4px 8px;
  background: rgba(69, 138, 255, 0.1);
  border-radius: 4px;
  font-weight: 500;
}
</style>
