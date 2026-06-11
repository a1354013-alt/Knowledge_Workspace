<template>
  <div class="page-content autotest-page">
    <header class="page-header">
      <h2>{{ t('autotest.pageTitle') }}</h2>
      <p>{{ t('autotest.pageSubtitle') }}</p>
    </header>

    <div class="grid">
      <Card>
        <template #title>
          {{ t('autotest.runTitle') }}
        </template>
        <template #subtitle>
          {{ t('autotest.runSubtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="warning-banner">
              <strong>{{ t('autotest.runner', { mode: runnerModeLabel }) }}</strong>
              <p>{{ capabilitiesMessage }}</p>
              <p>{{ t('autotest.simulatedIntro') }}</p>
              <p>{{ t('autotest.simulatedRecords') }}</p>
              <p v-if="capabilities?.safety_note">
                {{ capabilities.safety_note }}
              </p>
              <p v-if="capabilities">
                {{ t('autotest.dockerStatus', { status: capabilities.sandbox_backend_ready ? t('autotest.dockerReady') : t('autotest.dockerBlocked') }) }}
              </p>
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
                :label="t('common.chooseZip')"
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
                :label="t('common.run')"
                icon="pi pi-play"
                :loading="running"
                :disabled="capabilities?.runner_mode === 'disabled' && capabilities?.real_mode_requested"
                @click="runAutoTest"
              />
              <Button
                :label="t('common.refresh')"
                outlined
                icon="pi pi-refresh"
                :loading="loadingRuns"
                @click="loadRuns"
              />
            </div>
            <p class="muted">
              {{ t('autotest.tip') }}
            </p>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>
          {{ t('autotest.recentRuns') }}
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
              class="kw-table"
              data-key="id"
              paginator
              :rows="8"
              scrollable
              scroll-height="flex"
              size="small"
              responsive-layout="scroll"
              :table-style="{ minWidth: '640px' }"
              @row-click="onRunSelected"
            >
              <Column
                field="project_name"
                :header="t('common.project')"
              />
              <Column
                field="status"
                :header="t('common.status')"
              />
              <Column
                :header="t('common.created')"
              >
                <template #body="slotProps">
                  <CellText
                    :text="formatDateTime(slotProps.data.created_at)"
                    :title="formatDateTime(slotProps.data.created_at)"
                  />
                </template>
              </Column>
              <template #empty>
                <div class="empty-state">
                  <strong>{{ t('autotest.emptyTitle') }}</strong>
                  <p>{{ t('autotest.emptyBody') }}</p>
                </div>
              </template>
            </DataTable>
          </div>
        </template>
      </Card>

      <Card v-if="selectedRun">
        <template #title>
          {{ t('autotest.detailsTitle') }}
        </template>
        <template #subtitle>
          {{ selectedRun.id }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="result-box">
              <h3>{{ t('autotest.execution') }}</h3>
              <p class="muted">
                {{ t('autotest.mode') }}: {{ selectedRunMode }}
              </p>
              <p
                v-if="selectedRunRunnerMode === 'local_trusted'"
                class="warning-text"
              >
                {{ t('autotest.localTrustedRunWarning') }}
              </p>
              <p
                v-if="selectedRunRunnerMode === 'docker_sandbox'"
                class="muted"
              >
                {{ t('autotest.dockerRunWarning') }}
              </p>
              <p
                v-if="selectedRunIsGitHubIntakeOnly"
                class="muted"
              >
                {{ t('autotest.githubIntakeOnly') }}
              </p>
              <p class="muted">
                {{ t('autotest.failedReason') }}: {{ selectedRun.failed_reason || '-' }}
              </p>
              <p class="muted">
                {{ t('autotest.projectTypeDetected') }}: {{ selectedRun.project_type_detected || selectedRun.project_type || '-' }}
              </p>
              <p class="muted">
                {{ t('autotest.workingDirectory') }}: {{ selectedRun.working_directory || '-' }}
              </p>
            </div>

            <div class="result-box">
              <h3>{{ t('autotest.summary') }}</h3>
              <pre class="mono">{{ selectedRun.summary || '-' }}</pre>
            </div>

            <div class="result-box">
              <h3>{{ t('autotest.reports') }}</h3>
              <div class="row">
                <Button
                  :label="t('autotest.downloadMarkdownReport')"
                  icon="pi pi-download"
                  :disabled="!canExportSelectedRun"
                  :loading="downloadingFormat === 'md'"
                  @click="downloadReport('md')"
                />
                <Button
                  :label="t('autotest.downloadHtmlReport')"
                  icon="pi pi-download"
                  outlined
                  :disabled="!canExportSelectedRun"
                  :loading="downloadingFormat === 'html'"
                  @click="downloadReport('html')"
                />
                <Button
                  :label="t('autotest.copyAiFixPrompt')"
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
              <h3>{{ t('autotest.fixSuggestion') }}</h3>
              <pre class="mono">{{ selectedRun.suggestion }}</pre>
            </div>

            <div
              v-if="selectedRun.problem_entry_id || selectedRun.solution_entry_id"
              class="result-box"
            >
              <h3>{{ t('autotest.knowledgeCapture') }}</h3>
              <p class="muted">
                {{ t('autotest.problemDraft') }}: {{ selectedRun.problem_entry_id || '-' }}
              </p>
              <p class="muted">
                {{ t('autotest.solutionEntry') }}: {{ selectedRun.solution_entry_id || '-' }}
              </p>
              <div
                v-if="selectedRun.problem_entry_id && !selectedRun.solution_entry_id"
                class="row"
              >
                <Button
                  :label="t('autotest.promoteProblemToVerifiedSolution')"
                  icon="pi pi-check"
                  @click="promoteProblem"
                />
              </div>
            </div>

            <div
              v-if="selectedRun.prompt_output"
              class="result-box"
            >
              <h3>{{ t('autotest.promptOutput') }}</h3>
              <pre class="mono">{{ selectedRun.prompt_output }}</pre>
            </div>

            <div
              v-if="selectedRun.steps?.length"
              class="result-box"
            >
              <h3>{{ t('autotest.steps') }}</h3>
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
import { t } from '../i18n'
import { confirmDanger } from '../services/confirm'
import { formatDateTime } from '../utils/date'
import type {
  AutoTestExportFormat,
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
} from '../types'
import { useWorkspaceStore } from '../workspace-store'
import AutoTestStatusBadge from './autotest/AutoTestStatusBadge.vue'
import AutoTestTimeline from './autotest/AutoTestTimeline.vue'
import CellText from './common/CellText.vue'
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
const selectedRunMode = computed(() => selectedRun.value?.execution_mode || 'simulated')
const selectedRunRunnerMode = computed(() => selectedRun.value?.runner_mode || (selectedRunMode.value === 'real' ? 'local_trusted' : 'disabled'))
const runnerModeLabel = computed(() => {
  const mode = capabilities.value?.runner_mode || 'disabled'
  if (mode === 'local_trusted') {
    return t('autotest.localTrusted')
  }
  if (mode === 'docker_sandbox') {
    return t('autotest.dockerSandbox')
  }
  if (mode === 'simulated') {
    return t('autotest.simulated')
  }
  return t('autotest.disabled')
})
const selectedRunIsGitHubIntakeOnly = computed(() => {
  const run = selectedRun.value
  return run?.source_type === 'github_repo' && run?.status === 'registered'
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
    return t('autotest.selectRunReportHint')
  }
  if (!canExportSelectedRun.value) {
    return t('autotest.reportsLocked', { status: selectedRun.value.status })
  }
  if (!canCopyAiPrompt.value) {
    return t('autotest.copyPromptLocked')
  }
  return t('autotest.exportsReady')
})
const runsLoadMessage = computed(() => store.state.error.autotestRuns || '')
const showRunsReloadWarning = computed(() => store.state.status.autotestRuns === 'error' && runs.value.length > 0)
const capabilitiesMessage = computed(() => {
  if (capabilities.value?.runner_mode === 'local_trusted') {
    return t('autotest.localTrustedWarning')
  }
  if (capabilities.value?.runner_mode === 'docker_sandbox') {
    return capabilities.value.message || t('autotest.dockerActive')
  }
  return capabilities.value?.message || t('autotest.simulatedIntro')
})

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
    return t('autotest.timeout')
  }
  const apiError = error as { message?: string }
  return apiError?.message || t('common.requestFailed')
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
  throw new Error(t('autotest.asyncTimeout'))
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
      summary: t('autotest.reloadFailed'),
      detail: apiError?.message || store.state.error.autotestRuns || t('common.requestFailed'),
      life: 4500,
    })
  } finally {
    loadingRuns.value = false
  }
}

async function runAutoTest() {
  if (!selectedZip.value) {
    toast.add({ severity: 'warn', summary: t('autotest.noZipSelected'), detail: t('autotest.chooseZipFirst'), life: 3000 })
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
      summary: t('autotest.runQueued'),
      detail: response.summary || t('autotest.jobStarted', { id: response.id }),
      life: 3000,
    })
    selectedZip.value = null
    if (zipInput.value) {
      zipInput.value.value = ''
    }
    await loadRuns()
    const completed = isTerminalRunStatus(response.status) ? response : await pollAutoTestRun(response.id)
    toast.add({ severity: 'success', summary: t('autotest.runCompleted'), detail: completed.status || t('autotest.done'), life: 3000 })
  } catch (error: unknown) {
    toast.add({ severity: 'error', summary: t('autotest.runFailed'), detail: autoTestRunErrorMessage(error), life: 6000 })
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
      header: t('autotest.promoteProblemHeader'),
      message: t('autotest.promoteProblemMessage'),
      acceptLabel: t('logbook.promote'),
    }))
  ) {
    return
  }
  try {
    const response = await promoteAutoTestProblem(entryId)
    toast.add({ severity: 'success', summary: t('logbook.promoted'), detail: t('logbook.promotedDetail', { id: response.knowledge_entry_id }), life: 4500 })
    if (selectedRun.value?.id) {
      selectedRun.value = await getAutoTestRun(selectedRun.value.id)
    }
    await loadRuns()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.promoteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 5000 })
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
      summary: t('autotest.reportDownloaded'),
      detail: `autotest-report-${selectedRun.value.id}.${format}`,
      life: 3000,
    })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({
      severity: 'error',
      summary: t('autotest.reportDownloadFailed'),
      detail: apiError?.message || t('autotest.reportDownloadUnable'),
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
    toast.add({ severity: 'success', summary: t('autotest.promptCopied'), detail: t('autotest.promptCopiedDetail'), life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({
      severity: 'error',
      summary: t('autotest.copyFailed'),
      detail: apiError?.message || t('autotest.copyPromptUnable'),
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

.page-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.autotest-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
}

.page-header h2,
.page-header p {
  margin: 0;
}

.page-header p {
  margin-top: 6px;
  color: #51606f;
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

.empty-state {
  padding: 18px;
  color: #51606f;
  line-height: 1.6;
}

.empty-state strong {
  display: block;
  color: #1f2f46;
  margin-bottom: 4px;
}

.empty-state p {
  margin: 0;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
