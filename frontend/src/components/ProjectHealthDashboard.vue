<template>
  <div class="grid">
    <Card>
      <template #title>
        Project Health Dashboard
      </template>
      <template #subtitle>
        System-wide metrics and recent activity overview
      </template>
      <template #content>
        <div class="stack-lg">
          <!-- Loading State -->
          <div v-if="loading" class="loading-state">
            <div class="spinner" />
            <p>Loading dashboard metrics...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="error-state">
            <p class="error-message">{{ error }}</p>
            <Button
              label="Retry"
              icon="pi pi-refresh"
              @click="loadDashboard"
            />
          </div>

          <!-- Empty State -->
          <div v-else-if="!data" class="empty-state">
            <p>No data available yet. Start by uploading documents or creating knowledge entries.</p>
          </div>

          <!-- Dashboard Content -->
          <div v-else class="dashboard-content">
            <!-- Summary Cards Row -->
            <div class="cards-row">
              <div class="summary-card">
                <div class="card-header">
                  <span class="card-label">Knowledge Total</span>
                  <i class="pi pi-book" />
                </div>
                <div class="card-value">{{ data.knowledge.total }}</div>
                <div class="card-detail">
                  <span v-for="(count, status) in data.knowledge.by_status" :key="status" class="status-badge">
                    {{ status }}: {{ count }}
                  </span>
                </div>
              </div>

              <div class="summary-card">
                <div class="card-header">
                  <span class="card-label">Logbook Resolution Rate</span>
                  <i class="pi pi-list" />
                </div>
                <div class="card-value">{{ formatPercentage(data.logbook.resolution_rate) }}</div>
                <div class="card-detail">
                  {{ data.logbook.with_solution }} / {{ data.logbook.total }} with solution
                </div>
              </div>

              <div class="summary-card">
                <div class="card-header">
                  <span class="card-label">AutoTest Pass Rate</span>
                  <i class="pi pi-check-circle" />
                </div>
                <div class="card-value">{{ formatPercentage(data.autotest.pass_rate) }}</div>
                <div class="card-detail">
                  {{ data.autotest.passed }} / {{ data.autotest.total_runs }} passed
                </div>
              </div>

              <div class="summary-card">
                <div class="card-header">
                  <span class="card-label">Document Index Rate</span>
                  <i class="pi pi-file" />
                </div>
                <div class="card-value">{{ formatPercentage(calculateDocumentIndexRate()) }}</div>
                <div class="card-detail">
                  {{ data.documents.indexed }} / {{ data.documents.total }} indexed
                </div>
              </div>
            </div>

            <!-- Status Blocks -->
            <div class="status-blocks">
              <!-- Knowledge Status -->
              <div class="status-block">
                <h3>Knowledge by Status</h3>
                <div class="status-list">
                  <div v-for="(count, status) in data.knowledge.by_status" :key="status" class="status-item">
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

              <!-- Document Index Status -->
              <div class="status-block">
                <h3>Document Index Status</h3>
                <div class="status-list">
                  <div class="status-item">
                    <span class="status-name">Indexed</span>
                    <div class="status-bar">
                      <div
                        class="status-fill status-indexed"
                        :style="{ width: calculateStatusWidth(data.documents.indexed, data.documents.total) }"
                      />
                    </div>
                    <span class="status-count">{{ data.documents.indexed }}</span>
                  </div>
                  <div class="status-item">
                    <span class="status-name">Pending</span>
                    <div class="status-bar">
                      <div
                        class="status-fill status-pending"
                        :style="{ width: calculateStatusWidth(data.documents.pending, data.documents.total) }"
                      />
                    </div>
                    <span class="status-count">{{ data.documents.pending }}</span>
                  </div>
                  <div class="status-item">
                    <span class="status-name">Failed</span>
                    <div class="status-bar">
                      <div
                        class="status-fill status-failed"
                        :style="{ width: calculateStatusWidth(data.documents.failed, data.documents.total) }"
                      />
                    </div>
                    <span class="status-count">{{ data.documents.failed }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- AutoTest Recent Runs -->
            <div class="autotest-block">
              <h3>Recent AutoTest Runs</h3>
              <div v-if="data.autotest.recent_runs.length > 0" class="recent-runs-table">
                <div v-for="run in data.autotest.recent_runs" :key="run.id" class="run-row">
                  <div class="run-info">
                    <div class="run-name">{{ run.project_name }}</div>
                    <div class="run-time">{{ formatDateTime(run.created_at) }}</div>
                  </div>
                  <div class="run-status">
                    <span :class="`badge badge-${run.status}`">
                      {{ capitalizeStatus(run.status) }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-runs">
                <p>No recent AutoTest runs</p>
              </div>
            </div>

            <!-- Recent Activity -->
            <div class="activity-block">
              <h3>Last 7 Days Activity</h3>
              <div class="activity-grid">
                <div class="activity-item">
                  <div class="activity-label">Documents Added</div>
                  <div class="activity-value">{{ data.recent_activity.documents_added }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">Knowledge Added</div>
                  <div class="activity-value">{{ data.recent_activity.knowledge_added }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">Logbook Added</div>
                  <div class="activity-value">{{ data.recent_activity.logbook_added }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">QA Count</div>
                  <div class="activity-value">{{ data.recent_activity.qa_count }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">AutoTest Runs</div>
                  <div class="activity-value">{{ data.recent_activity.autotest_runs }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">AutoTest Passed</div>
                  <div class="activity-value success">{{ data.recent_activity.autotest_passed }}</div>
                </div>
                <div class="activity-item">
                  <div class="activity-label">AutoTest Failed</div>
                  <div class="activity-value error">{{ data.recent_activity.autotest_failed }}</div>
                </div>
              </div>
            </div>

            <!-- Refresh Button -->
            <div class="action-bar">
              <Button
                label="Refresh"
                icon="pi pi-refresh"
                :loading="loading"
                @click="loadDashboard"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import { get } from '../api'
import type { DashboardHealthResponse } from '../types'

const data = ref<DashboardHealthResponse | null>(null)
const loading = ref(false)
const error = ref('')

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const response = await get<DashboardHealthResponse>('/api/dashboard/health')
    data.value = response
  } catch (err: unknown) {
    const apiError = err as { message?: string; detail?: string }
    error.value = apiError?.message || apiError?.detail || 'Failed to load dashboard metrics'
  } finally {
    loading.value = false
  }
}

function formatPercentage(value: number | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '0%'
  }
  return `${Math.round(value)}%`
}

function calculateDocumentIndexRate(): number {
  if (!data.value || data.value.documents.total === 0) {
    return 0
  }
  return (data.value.documents.indexed / data.value.documents.total) * 100
}

function calculateStatusWidth(count: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((count / total) * 100)}%`
}

function capitalizeStatus(status: string): string {
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatDateTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr.replace('T', ' ').replace('Z', '')
  }
}

onMounted(loadDashboard)
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

/* Summary Cards */
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

/* Status Blocks */
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

/* AutoTest Block */
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
}

.run-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.run-time {
  font-size: 11px;
  color: #51606f;
}

.run-status {
  margin-left: 12px;
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-passed {
  background: rgba(40, 167, 69, 0.15);
  color: #28a745;
}

.badge-failed {
  background: rgba(220, 53, 69, 0.15);
  color: #dc3545;
}

.badge-running {
  background: rgba(23, 162, 184, 0.15);
  color: #17a2b8;
}

.badge-queued {
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
}

.empty-runs {
  padding: 16px;
  text-align: center;
  color: #51606f;
  font-size: 13px;
}

/* Activity Block */
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

/* Action Bar */
.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

@media (max-width: 768px) {
  .cards-row {
    grid-template-columns: 1fr;
  }

  .status-blocks {
    grid-template-columns: 1fr;
  }

  .activity-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
