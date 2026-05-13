<template>
  <div class="grid">
    <Card>
      <template #title>
        Run acceptance (install / build / test / lint)
      </template>
      <template #subtitle>
        Guarded runner for supported project zips (smoke/build/test only). Not a fully isolated sandbox; use trusted inputs and a constrained stack.
      </template>
      <template #content>
        <div class="stack-md">
          <div class="warning-banner">
            <strong>AutoTest mode: {{ capabilities?.mode || 'simulated' }}</strong>
            <p>{{ capabilities?.message || 'Safe simulated mode is active until the backend reports otherwise.' }}</p>
          </div>
          <div class="row">
            <input
              ref="zipInput"
              type="file"
              accept=".zip"
              class="hidden-input"
              @change="onZipSelected"
            >
            <Button
              label="Choose Zip"
              icon="pi pi-upload"
              outlined
              @click="openZipPicker"
            />
            <span
              v-if="selectedZip"
              class="muted"
            >{{ selectedZip.name }}</span>
          </div>
          <div class="row">
            <Button
              label="Run"
              icon="pi pi-play"
              :loading="running"
              :disabled="capabilities?.real_mode_requested && !capabilities.real_mode_available"
              @click="runAutoTest"
            />
            <Button
              label="Refresh"
              outlined
              icon="pi pi-refresh"
              :loading="loadingRuns"
              @click="loadRuns"
            />
          </div>
          <p class="muted">
            Tip: keep zips small; steps have timeouts. Results are stored as structured data for later search.
          </p>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        Recent runs
      </template>
      <template #content>
        <div class="stack-md">
          <DataTable
            :value="runs"
            :loading="loadingRuns"
            data-key="id"
            size="small"
            responsive-layout="scroll"
            @row-click="onRunSelected"
          >
            <Column
              field="project_name"
              header="Project"
            />
            <Column
              field="status"
              header="Status"
            />
            <Column
              field="created_at"
              header="Created"
            />
          </DataTable>
        </div>
      </template>
    </Card>

    <Card v-if="selectedRun">
      <template #title>
        Run details
      </template>
      <template #subtitle>
        {{ selectedRun.id }}
      </template>
      <template #content>
        <div class="stack-md">
          <div class="result-box">
            <h3>Execution</h3>
            <p class="muted">
              Mode: {{ selectedRun.execution_mode || '-' }}
            </p>
            <p
              v-if="selectedRun.execution_mode === 'real'"
              class="warning-text"
            >
              Real mode executes commands from uploaded projects. Use only with trusted local projects.
            </p>
            <p class="muted">
              Failed reason: {{ selectedRun.failed_reason || '-' }}
            </p>
            <p class="muted">
              Project type detected: {{ selectedRun.project_type_detected || selectedRun.project_type || '-' }}
            </p>
            <p class="muted">
              Working directory: {{ selectedRun.working_directory || '-' }}
            </p>
          </div>

          <div class="result-box">
            <h3>Summary</h3>
            <pre class="mono">{{ selectedRun.summary || '-' }}</pre>
          </div>

          <div class="result-box">
            <h3>Reports</h3>
            <div class="row">
              <Button
                label="Download Markdown Report"
                icon="pi pi-download"
                :disabled="!canExportSelectedRun"
                :loading="downloadingFormat === 'md'"
                @click="downloadReport('md')"
              />
              <Button
                label="Download HTML Report"
                icon="pi pi-download"
                outlined
                :disabled="!canExportSelectedRun"
                :loading="downloadingFormat === 'html'"
                @click="downloadReport('html')"
              />
              <Button
                label="Copy AI Fix Prompt"
                icon="pi pi-copy"
                outlined
                :disabled="!canCopyAiPrompt"
                @click="copyAiFixPrompt"
              />
            </div>
            <p class="muted">
              {{ reportActionHint }}
            </p>
          </div>

          <div class="result-box">
            <div class="timeline-header">
              <div>
                <h3>Run timeline</h3>
                <p class="muted">
                  Uploaded to report generation, with a safe fallback for older runs that have sparse metadata.
                </p>
              </div>
            </div>

            <div
              v-if="timelineItems.length"
              class="timeline"
            >
              <article
                v-for="item in timelineItems"
                :key="item.key"
                class="timeline-item"
              >
                <div
                  class="timeline-marker"
                  :class="`timeline-${item.status}`"
                >
                  <span />
                </div>
                <div class="timeline-body">
                  <div class="timeline-row">
                    <strong>{{ item.label }}</strong>
                    <span :class="badgeClass(item.status)">{{ item.status }}</span>
                  </div>
                  <p
                    v-if="item.finished_at || item.started_at"
                    class="timeline-time"
                  >
                    {{ formatTimelineTimestamp(item.finished_at || item.started_at || '') }}
                  </p>
                  <p
                    v-if="item.message"
                    class="timeline-message"
                  >
                    {{ item.message }}
                  </p>
                  <p
                    v-if="item.duration_ms !== null"
                    class="timeline-time"
                  >
                    {{ item.duration_ms }} ms
                  </p>
                </div>
              </article>
            </div>

            <div
              v-else
              class="timeline-empty"
            >
              No timeline is available for this run yet.
            </div>
          </div>

          <div
            v-if="selectedRun.suggestion"
            class="result-box"
          >
            <h3>Fix suggestion</h3>
            <pre class="mono">{{ selectedRun.suggestion }}</pre>
          </div>

          <div
            v-if="selectedRun.problem_entry_id || selectedRun.solution_entry_id"
            class="result-box"
          >
            <h3>Knowledge capture</h3>
            <p class="muted">
              Problem draft: {{ selectedRun.problem_entry_id || '-' }}
            </p>
            <p class="muted">
              Solution entry: {{ selectedRun.solution_entry_id || '-' }}
            </p>
            <div
              v-if="selectedRun.problem_entry_id && !selectedRun.solution_entry_id"
              class="row"
            >
              <Button
                label="Promote problem to verified solution"
                icon="pi pi-check"
                @click="promoteProblem"
              />
            </div>
          </div>

          <div
            v-if="selectedRun.prompt_output"
            class="result-box"
          >
            <h3>Prompt output (for Codex/Copilot)</h3>
            <pre class="mono">{{ selectedRun.prompt_output }}</pre>
          </div>

          <div
            v-if="selectedRun.steps?.length"
            class="result-box"
          >
            <h3>Steps</h3>
            <article
              v-for="step in selectedRun.steps"
              :key="step.step_id"
              class="step-card"
            >
              <div class="step-head">
                <strong>{{ step.name }}</strong>
                <span :class="badgeClass(step.status)">{{ step.status }}</span>
              </div>
              <p class="muted">
                {{ step.command }}
              </p>
              <pre class="mono">{{ step.output || step.stderr_summary || step.stdout_summary || '-' }}</pre>
            </article>
          </div>

          <RelatedItemsPanel :item-id="`autotest_run:${selectedRun.id}`" />
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'

import {
  downloadAutoTestReport,
  getAutoTestCapabilities,
  getAutoTestRun,
  promoteAutoTestProblem,
  startAutoTest,
} from '../autotest-api'
import type {
  AutoTestExportFormat,
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
  AutoTestTimelineItemResponse,
} from '../types'
import { useWorkspaceStore } from '../workspace-store'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()

const zipInput = ref<HTMLInputElement | null>(null)
const selectedZip = ref<File | null>(null)

const running = ref(false)
const loadingRuns = ref(false)
const downloadingFormat = ref<AutoTestExportFormat | null>(null)
const runs = ref<AutoTestRunListItemResponse[]>([])
const selectedRun = ref<AutoTestRunResponse | null>(null)
const capabilities = ref<AutoTestCapabilitiesResponse | null>(null)
const store = useWorkspaceStore()

const allowedTimelineStatuses = new Set(['pending', 'running', 'success', 'failed', 'skipped'])
const AUTO_TEST_POLL_INTERVAL_MS = 1500
const AUTO_TEST_POLL_TIMEOUT_MS = 5 * 60 * 1000

const fallbackTimelineKeys = [
  ['uploaded', 'Uploaded'],
  ['extracted', 'Extracted'],
  ['detected_stack', 'Detected stack'],
  ['prepared_environment', 'Installed dependencies / Prepared environment'],
  ['ran_tests', 'Ran tests'],
  ['generated_report', 'Generated report'],
  ['failed_reason', 'Failed reason'],
] as const

const timelineItems = computed<AutoTestTimelineItemResponse[]>(() => buildTimeline(selectedRun.value))
const canExportSelectedRun = computed(() => {
  const status = selectedRun.value?.status
  return status === 'passed' || status === 'failed'
})
const aiFixPromptText = computed(() => {
  const run = selectedRun.value
  if (!run) {
    return ''
  }
  return [run.suggestion, run.prompt_output]
    .map((value) => String(value || '').trim())
    .filter(Boolean)
    .join('\n\n')
})
const canCopyAiPrompt = computed(() => canExportSelectedRun.value && !!aiFixPromptText.value)
const reportActionHint = computed(() => {
  if (!selectedRun.value) {
    return 'Select a run to export reports or copy the generated AI fix prompt.'
  }
  if (!canExportSelectedRun.value) {
    return `Run status is ${selectedRun.value.status}. Reports unlock after the run reaches passed or failed.`
  }
  if (!canCopyAiPrompt.value) {
    return 'Report downloads are ready. AI fix prompt copy unlocks when the backend generated a suggestion or prompt output.'
  }
  return 'Exports use deterministic filenames and include the current run detail report.'
})

function badgeClass(status: string) {
  const value = String(status || '').toLowerCase()
  if (value === 'passed' || value === 'done' || value === 'success') return 'badge badge-ok'
  if (value === 'failed') return 'badge badge-bad'
  if (value === 'skipped') return 'badge badge-skip'
  if (value === 'unavailable') return 'badge badge-unavail'
  if (value === 'running') return 'badge badge-run'
  return 'badge badge-neutral'
}

function formatTimelineTimestamp(value: string) {
  try {
    return new Date(value).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function normalizeTimelineItem(
  raw: Partial<AutoTestTimelineItemResponse> | null | undefined
): AutoTestTimelineItemResponse | null {
  const key = String(raw?.key || '').trim()
  const label = String(raw?.label || '').trim()
  const status = String(raw?.status || '').trim().toLowerCase()
  if (!key || !label || !allowedTimelineStatuses.has(status)) {
    return null
  }
  return {
    key,
    label,
    name: String(raw?.name || label).trim(),
    status: status as AutoTestTimelineItemResponse['status'],
    started_at: raw?.started_at ? String(raw.started_at) : null,
    finished_at: raw?.finished_at ? String(raw.finished_at) : null,
    duration_ms: typeof raw?.duration_ms === 'number' ? raw.duration_ms : null,
    message: raw?.message ? String(raw.message) : null,
  }
}

function buildTimeline(run: AutoTestRunResponse | null): AutoTestTimelineItemResponse[] {
  if (!run) {
    return []
  }

  const normalized = Array.isArray(run.timeline)
    ? run.timeline
        .map((item) => normalizeTimelineItem(item))
        .filter((item): item is AutoTestTimelineItemResponse => item !== null)
    : []
  if (normalized.length) {
    return normalized
  }

  const failedMessage = run.summary || run.suggestion || null
  return fallbackTimelineKeys.map(([key, label]) => ({
    key,
    label,
    name: label,
    status:
      key === 'uploaded'
        ? 'success'
        : key === 'failed_reason' && run.status === 'failed'
          ? 'failed'
          : key === 'generated_report' && (run.summary || run.prompt_output)
            ? 'success'
            : key === 'ran_tests' && run.status === 'running'
              ? 'running'
              : key === 'ran_tests' && (run.status === 'passed' || run.status === 'failed')
                ? run.status === 'failed'
                  ? 'failed'
                  : 'success'
                : 'pending',
    started_at: key === 'uploaded' ? run.created_at || null : null,
    finished_at: key === 'uploaded' ? run.created_at || null : null,
    duration_ms: key === 'uploaded' ? 0 : null,
    message:
      key === 'uploaded'
        ? run.source_ref || null
        : key === 'failed_reason' && run.status === 'failed'
          ? run.failed_reason || failedMessage
          : key === 'generated_report' && run.summary
            ? run.summary
            : null,
  }))
}

function openZipPicker() {
  zipInput.value?.click()
}

function onZipSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedZip.value = target?.files?.[0] || null
}

function isTimeoutError(error: unknown) {
  const apiError = error as { code?: string; message?: string; detail?: string }
  const text = `${apiError?.code || ''} ${apiError?.message || ''} ${apiError?.detail || ''}`.toLowerCase()
  return apiError?.code === 'ECONNABORTED' || text.includes('timeout') || text.includes('timed out')
}

function autoTestRunErrorMessage(error: unknown) {
  if (isTimeoutError(error)) {
    return 'AutoTest execution timed out. Check whether project tests are stuck, adjust AUTOTEST_TIMEOUT_SECONDS, or run a smaller test scope.'
  }
  const apiError = error as { message?: string }
  return apiError?.message || 'Request failed.'
}

function isTerminalRunStatus(status: string | undefined) {
  return status === 'passed' || status === 'failed'
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function pollAutoTestRun(runId: string) {
  const deadline = Date.now() + AUTO_TEST_POLL_TIMEOUT_MS
  while (Date.now() < deadline) {
    const latest = await getAutoTestRun(runId)
    selectedRun.value = latest
    await loadRuns()
    if (isTerminalRunStatus(latest.status)) {
      return latest
    }
    await sleep(AUTO_TEST_POLL_INTERVAL_MS)
  }
  throw new Error('AutoTest execution timed out while waiting for the async job to finish.')
}

async function loadRuns() {
  loadingRuns.value = true
  try {
    capabilities.value = await getAutoTestCapabilities()
    await store.refreshAutotestRuns({ force: true })
    runs.value = store.state.lists.autotestRuns || []
  } catch {
    runs.value = []
  } finally {
    loadingRuns.value = false
  }
}

async function runAutoTest() {
  if (!selectedZip.value) {
    toast.add({ severity: 'warn', summary: 'No zip selected', detail: 'Choose a project zip first.', life: 3000 })
    return
  }

  running.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedZip.value)
    const response = await startAutoTest(formData)
    selectedRun.value = response
    toast.add({ severity: 'info', summary: 'Run queued', detail: `AutoTest job ${response.id} started.`, life: 3000 })
    selectedZip.value = null
    if (zipInput.value) {
      zipInput.value.value = ''
    }
    await loadRuns()
    const completed = isTerminalRunStatus(response.status) ? response : await pollAutoTestRun(response.id)
    toast.add({ severity: 'success', summary: 'Run completed', detail: completed.status || 'Done.', life: 3000 })
  } catch (error: unknown) {
    toast.add({ severity: 'error', summary: 'Run failed', detail: autoTestRunErrorMessage(error), life: 6000 })
  } finally {
    running.value = false
  }
}

async function onRunSelected(event: unknown) {
  const item = (event as { data?: AutoTestRunListItemResponse } | null)?.data
  if (!item?.id) {
    return
  }
  try {
    selectedRun.value = await getAutoTestRun(item.id)
  } catch {
    selectedRun.value = null
  }
}

async function promoteProblem() {
  const entryId = selectedRun.value?.problem_entry_id
  if (!entryId) {
    return
  }
  if (!window.confirm('Promote this AutoTest problem draft to a verified knowledge entry?')) {
    return
  }
  try {
    const response = await promoteAutoTestProblem(entryId)
    toast.add({ severity: 'success', summary: 'Promoted', detail: `Knowledge entry: ${response.knowledge_entry_id}`, life: 4500 })
    if (selectedRun.value?.id) {
      selectedRun.value = await getAutoTestRun(selectedRun.value.id)
    }
    await loadRuns()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Promote failed', detail: apiError?.message || 'Request failed.', life: 5000 })
  }
}

async function downloadReport(format: AutoTestExportFormat) {
  if (!selectedRun.value?.id || !canExportSelectedRun.value) {
    return
  }
  downloadingFormat.value = format
  try {
    await downloadAutoTestReport(selectedRun.value.id, format)
    toast.add({
      severity: 'success',
      summary: 'Report downloaded',
      detail: `autotest-report-${selectedRun.value.id}.${format}`,
      life: 3000,
    })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({
      severity: 'error',
      summary: 'Report download failed',
      detail: apiError?.message || 'Unable to download report.',
      life: 5000,
    })
  } finally {
    downloadingFormat.value = null
  }
}

async function copyAiFixPrompt() {
  if (!canCopyAiPrompt.value || !aiFixPromptText.value) {
    return
  }
  try {
    await navigator.clipboard.writeText(aiFixPromptText.value)
    toast.add({ severity: 'success', summary: 'Prompt copied', detail: 'AI fix prompt copied to clipboard.', life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({
      severity: 'error',
      summary: 'Copy failed',
      detail: apiError?.message || 'Unable to copy AI fix prompt.',
      life: 5000,
    })
  }
}

onMounted(loadRuns)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.warning-banner {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #ffd6a5;
  background: #fff7ed;
  color: #8a4b08;
}

.warning-banner strong,
.warning-banner p,
.warning-text {
  margin: 0;
}

.warning-banner p,
.warning-text {
  font-size: 13px;
  line-height: 1.5;
}

.warning-text {
  color: #8a4b08;
}

.hidden-input {
  display: none;
}

.muted {
  margin: 0;
  color: #51606f;
  font-size: 13px;
}

.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
}

.timeline-header h3 {
  margin: 0 0 4px;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-top: 12px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 14px;
}

.timeline-item:not(:last-child) .timeline-marker::after {
  content: '';
  position: absolute;
  top: 22px;
  bottom: -12px;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  background: #d8e1e8;
}

.timeline-marker {
  position: relative;
  display: flex;
  justify-content: center;
}

.timeline-marker span {
  width: 14px;
  height: 14px;
  margin-top: 4px;
  border-radius: 999px;
  border: 2px solid transparent;
  background: #d8e1e8;
  box-shadow: 0 0 0 6px rgba(255, 255, 255, 0.9);
}

.timeline-done span {
  background: #0f6b3a;
  border-color: #bfead0;
}

.timeline-running span {
  background: #1e4e8c;
  border-color: #cfe6ff;
}

.timeline-failed span {
  background: #a11919;
  border-color: #ffd0d0;
}

.timeline-pending span {
  background: #b0bcc8;
  border-color: #e5edf4;
}

.timeline-body {
  padding: 0 0 18px;
}

.timeline-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.timeline-time,
.timeline-message,
.timeline-empty {
  margin: 6px 0 0;
  color: #51606f;
  font-size: 13px;
}

.timeline-message {
  white-space: pre-wrap;
  line-height: 1.5;
}

.timeline-empty {
  margin-top: 12px;
  padding: 14px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px dashed #d8e1e8;
}

.step-card {
  padding: 10px 12px;
  border-radius: 12px;
  background: white;
  border: 1px solid #d8e1e8;
}

.step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.2px;
  border: 1px solid transparent;
  text-transform: lowercase;
}

.badge-neutral {
  background: #f0f4f8;
  color: #3a4755;
  border-color: #d8e1e8;
}

.badge-run {
  background: #eef6ff;
  color: #1e4e8c;
  border-color: #cfe6ff;
}

.badge-ok {
  background: #e8fbf1;
  color: #0f6b3a;
  border-color: #bfead0;
}

.badge-bad {
  background: #fff0f0;
  color: #a11919;
  border-color: #ffd0d0;
}

.badge-skip {
  background: #fff7e6;
  color: #8a5a00;
  border-color: #ffe0a3;
}

.badge-unavail {
  background: #f6f0ff;
  color: #5a2ea6;
  border-color: #e2d3ff;
}

.mono {
  white-space: pre-wrap;
  margin: 8px 0 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
