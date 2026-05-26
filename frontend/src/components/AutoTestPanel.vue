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
          <p
            v-if="runsLoadMessage"
            class="inline-status"
            :class="{ 'inline-status-warning': showRunsReloadWarning }"
          >
            {{ runsLoadMessage }}
          </p>
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

          <AutoTestTimeline :run="selectedRun" />

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
                <AutoTestStatusBadge :status="step.status" />
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
import { confirmDanger } from '../services/confirm'
import type {
  AutoTestExportFormat,
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
} from '../types'
import { useWorkspaceStore } from '../workspace-store'
import AutoTestStatusBadge from './autotest/AutoTestStatusBadge.vue'
import AutoTestTimeline from './autotest/AutoTestTimeline.vue'
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

const AUTO_TEST_POLL_INTERVAL_MS = 1500
const AUTO_TEST_POLL_TIMEOUT_MS = 5 * 60 * 1000

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
const runsLoadMessage = computed(() => store.state.error.autotestRuns || '')
const showRunsReloadWarning = computed(() => store.state.status.autotestRuns === 'error' && runs.value.length > 0)

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
    return 'AutoTest upload or job creation timed out. Check the ZIP size, network connection, or backend status. If the job was created, refresh and review recent runs.'
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
  } catch (error: unknown) {
    runs.value = store.state.lists.autotestRuns || []
    const apiError = error as { message?: string }
    toast.add({
      severity: runs.value.length ? 'warn' : 'error',
      summary: 'Reload failed',
      detail: apiError?.message || store.state.error.autotestRuns || 'Request failed.',
      life: 4500,
    })
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
    toast.add({
      severity: 'info',
      summary: 'Run queued',
      detail: response.summary || `AutoTest job ${response.id} started.`,
      life: 3000,
    })
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
  if (
    !(await confirmDanger({
      header: 'Promote AutoTest problem',
      message: 'Promote this AutoTest problem draft to a verified knowledge entry?',
      acceptLabel: 'Promote',
    }))
  ) {
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

.inline-status {
  margin: 0;
  color: #b45309;
  font-size: 13px;
}

.inline-status-warning {
  font-weight: 600;
}

.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
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
