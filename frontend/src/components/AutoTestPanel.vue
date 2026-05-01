<template>
  <div class="grid">
    <Card>
      <template #title>
        Run acceptance (install / build / test / lint)
      </template>
      <template #subtitle>
        Guarded runner for supported project zips (smoke/build/test only). Not a fully isolated sandbox — use trusted inputs and a constrained stack.
      </template>
      <template #content>
        <div class="stack-md">
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
                label="Promote problem → verified solution"
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
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'

import { get, post } from '../api'
import { useWorkspaceStore } from '../workspace-store'
import type { AutoTestRunListItemResponse, AutoTestRunResponse, PromoteToKnowledgeResponse } from '../types'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()

const zipInput = ref<HTMLInputElement | null>(null)
const selectedZip = ref<File | null>(null)

const running = ref(false)
const loadingRuns = ref(false)
const runs = ref<AutoTestRunListItemResponse[]>([])
const selectedRun = ref<AutoTestRunResponse | null>(null)
const store = useWorkspaceStore()

function badgeClass(status: string) {
  const value = String(status || '').toLowerCase()
  if (value === 'passed') return 'badge badge-ok'
  if (value === 'failed') return 'badge badge-bad'
  if (value === 'skipped') return 'badge badge-skip'
  if (value === 'unavailable') return 'badge badge-unavail'
  if (value === 'running') return 'badge badge-run'
  return 'badge badge-neutral'
}

function openZipPicker() {
  zipInput.value?.click()
}

function onZipSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedZip.value = target?.files?.[0] || null
}

async function loadRuns() {
  loadingRuns.value = true
  try {
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
    const response = await post<AutoTestRunResponse, FormData>('/api/autotest/run', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    toast.add({ severity: 'success', summary: 'Run completed', detail: response.status || 'Done.', life: 3000 })
    selectedZip.value = null
    if (zipInput.value) {
      zipInput.value.value = ''
    }
    selectedRun.value = response
    await loadRuns()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Run failed', detail: apiError?.message || 'Request failed.', life: 5000 })
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
    selectedRun.value = await get<AutoTestRunResponse>(`/api/autotest/runs/${item.id}`)
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
    const response = await post<PromoteToKnowledgeResponse>(`/api/logbook/entries/${entryId}/promote-to-knowledge`)
    toast.add({ severity: 'success', summary: 'Promoted', detail: `Knowledge entry: ${response.knowledge_entry_id}`, life: 4500 })
    if (selectedRun.value?.id) {
      selectedRun.value = await get<AutoTestRunResponse>(`/api/autotest/runs/${selectedRun.value.id}`)
    }
    await loadRuns()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Promote failed', detail: apiError?.message || 'Request failed.', life: 5000 })
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
