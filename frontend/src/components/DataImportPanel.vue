<template>
  <div class="data-page">
    <header class="page-header">
      <div>
        <h2>{{ t('dataImport.title') }}</h2>
        <p>{{ t('dataImport.subtitle') }}</p>
      </div>
      <Tag
        severity="contrast"
        :value="t('dataImport.limitHint', { sizeMb: String(maxSizeMb), rows: String(importLimits.maxRows) })"
      />
    </header>

    <div class="grid">
      <Card>
        <template #title>
          {{ t('dataImport.importCardTitle') }}
        </template>
        <template #subtitle>
          {{ t('dataImport.importCardSubtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="row">
              <Dropdown
                v-model="selectedKind"
                :options="kindOptions"
                option-label="label"
                option-value="value"
                class="field-grow"
              />
              <Button
                :label="t('dataImport.downloadTemplate')"
                icon="pi pi-download"
                outlined
                @click="handleDownloadTemplate"
              />
            </div>

            <div class="row">
              <input
                ref="fileInput"
                type="file"
                accept=".xlsx"
                class="hidden-input"
                @change="onFileSelected"
              >
              <Button
                :label="t('dataImport.chooseExcel')"
                icon="pi pi-file-excel"
                @click="openFilePicker"
              />
              <Button
                :label="t('dataImport.validate')"
                icon="pi pi-check-circle"
                severity="secondary"
                outlined
                :loading="analyzing"
                :disabled="!selectedFile"
                @click="analyzeSelectedFile"
              />
            </div>

            <p class="inline-note">
              {{ selectedFile ? selectedFile.name : t('dataImport.noFileSelected') }}
            </p>

            <div class="steps">
              <span
                v-for="step in steps"
                :key="step"
                class="step-chip"
              >
                {{ step }}
              </span>
            </div>

            <EmptyStateBlock
              v-if="!analysis"
              icon="pi pi-table"
              :title="t('dataImport.emptyTitle')"
              :description="t('dataImport.emptyDescription')"
            />

            <template v-else>
              <div class="summary-grid">
                <div class="summary-item">
                  <strong>{{ analysis.totalRows }}</strong>
                  <span>{{ t('dataImport.totalRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ analysis.validRows.length }}</strong>
                  <span>{{ t('dataImport.validRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ analysis.skippedRows }}</strong>
                  <span>{{ t('dataImport.skippedRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ analysis.errors.length }}</strong>
                  <span>{{ t('dataImport.errorDetails') }}</span>
                </div>
              </div>

              <div class="stack-sm">
                <h3>{{ t('dataImport.preview') }}</h3>
                <DataTable
                  :value="analysis.previewRows"
                  size="small"
                  responsive-layout="scroll"
                >
                  <Column
                    field="rowNumber"
                    :header="t('dataImport.row')"
                  />
                  <Column
                    v-for="header in analysis.headers"
                    :key="header"
                    :header="header"
                  >
                    <template #body="slotProps">
                      {{ slotProps.data.values[header] || '-' }}
                    </template>
                  </Column>
                </DataTable>
              </div>

              <div class="stack-sm">
                <h3>{{ t('dataImport.errorDetails') }}</h3>
                <DataTable
                  :value="analysis.errors"
                  size="small"
                  responsive-layout="scroll"
                >
                  <Column
                    field="row"
                    :header="t('dataImport.row')"
                  />
                  <Column
                    field="field"
                    :header="t('dataImport.field')"
                  />
                  <Column
                    field="reason"
                    :header="t('dataImport.reason')"
                  />
                </DataTable>
              </div>

              <div class="row">
                <Button
                  :label="t('dataImport.confirmImport')"
                  icon="pi pi-upload"
                  :loading="importing"
                  :disabled="analysis.validRows.length === 0"
                  @click="confirmImport"
                />
                <Button
                  :label="t('dataImport.resetImport')"
                  outlined
                  severity="secondary"
                  :disabled="importing"
                  @click="resetImportState"
                />
              </div>
            </template>

            <div
              v-if="result"
              class="result-panel"
            >
              <h3>{{ t('dataImport.importResult') }}</h3>
              <div class="summary-grid">
                <div class="summary-item">
                  <strong>{{ result.totalRows }}</strong>
                  <span>{{ t('dataImport.totalRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ result.successRows }}</strong>
                  <span>{{ t('dataImport.successRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ result.failedRows }}</strong>
                  <span>{{ t('dataImport.failedRows') }}</span>
                </div>
                <div class="summary-item">
                  <strong>{{ result.skippedRows }}</strong>
                  <span>{{ t('dataImport.skippedRows') }}</span>
                </div>
              </div>
              <div class="row">
                <Button
                  :label="t('dataImport.viewImportedData')"
                  severity="secondary"
                  outlined
                  @click="openImportedSection"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>
          {{ t('dataImport.exportCardTitle') }}
        </template>
        <template #subtitle>
          {{ t('dataImport.exportCardSubtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="row export-row">
              <Dropdown
                v-model="selectedKind"
                :options="kindOptions"
                option-label="label"
                option-value="value"
                class="field-grow"
              />
              <Button
                :label="t('dataImport.exportExcel')"
                icon="pi pi-download"
                :loading="exportingExcel"
                @click="handleExport('xlsx')"
              />
              <Button
                :label="t('dataImport.exportJson')"
                icon="pi pi-download"
                outlined
                severity="secondary"
                :loading="exportingJson"
                @click="handleExport('json')"
              />
            </div>

            <EmptyStateBlock
              icon="pi pi-box"
              :title="t('dataImport.exportHintTitle')"
              :description="t('dataImport.exportHintDescription')"
            />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'

import { t } from '../i18n'
import {
  analyzeImportFile,
  downloadImportTemplate,
  exportWorkspaceData,
  getImportLimits,
  submitImport,
  type ExportFormat,
  type ImportAnalysis,
  type ImportResult,
  type WorkspaceDataKind,
} from '../services/workspace-data'
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import { useWorkspaceNavigation } from '../workspace-navigation'
import { useWorkspaceStore } from '../workspace-store'

const toast = useToast()
const store = useWorkspaceStore()
const { navigate } = useWorkspaceNavigation()

const selectedKind = ref<WorkspaceDataKind>('knowledge')
const selectedFile = ref<File | null>(null)
const analysis = ref<ImportAnalysis | null>(null)
const result = ref<ImportResult | null>(null)
const analyzing = ref(false)
const importing = ref(false)
const exportingExcel = ref(false)
const exportingJson = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const importLimits = getImportLimits()
const maxSizeMb = importLimits.maxBytes / 1024 / 1024

const kindOptions = computed(() => [
  { label: t('nav.knowledge'), value: 'knowledge' },
  { label: t('nav.logbook'), value: 'logbook' },
  { label: t('nav.prompts'), value: 'prompt' },
])

const steps = computed(() => [
  t('dataImport.stepChooseType'),
  t('dataImport.stepDownloadTemplate'),
  t('dataImport.stepChooseFile'),
  t('dataImport.stepPreview'),
  t('dataImport.stepValidate'),
  t('dataImport.stepConfirm'),
  t('dataImport.stepResult'),
])

function openFilePicker() {
  fileInput.value?.click()
}

function resetImportState() {
  selectedFile.value = null
  analysis.value = null
  result.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement | null
  selectedFile.value = input?.files?.[0] ?? null
  analysis.value = null
  result.value = null
}

function handleDownloadTemplate() {
  downloadImportTemplate(selectedKind.value)
  toast.add({ severity: 'success', summary: t('common.downloaded'), detail: t('dataImport.templateReady'), life: 2500 })
}

async function analyzeSelectedFile() {
  if (!selectedFile.value) {
    toast.add({ severity: 'warn', summary: t('dataImport.chooseExcel'), detail: t('dataImport.chooseFileFirst'), life: 2500 })
    return
  }

  analyzing.value = true
  result.value = null
  try {
    analysis.value = await analyzeImportFile(selectedKind.value, selectedFile.value)
    toast.add({
      severity: analysis.value.errors.length ? 'warn' : 'success',
      summary: t('dataImport.validate'),
      detail: analysis.value.errors.length ? t('dataImport.validationHasErrors') : t('dataImport.validationPassed'),
      life: 3000,
    })
  } catch (error: unknown) {
    analysis.value = null
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('dataImport.validationFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    analyzing.value = false
  }
}

async function confirmImport() {
  if (!analysis.value) {
    return
  }
  importing.value = true
  try {
    result.value = await submitImport(analysis.value)
    await store.refreshAll({ force: true })
    toast.add({
      severity: result.value.failedRows ? 'warn' : 'success',
      summary: t('dataImport.importCompleted'),
      detail: t('dataImport.importSummary', {
        success: String(result.value.successRows),
        failed: String(result.value.failedRows),
        skipped: String(result.value.skippedRows),
      }),
      life: 4000,
    })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('dataImport.importFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4500 })
  } finally {
    importing.value = false
  }
}

async function handleExport(format: ExportFormat) {
  const loadingRef = format === 'xlsx' ? exportingExcel : exportingJson
  loadingRef.value = true
  try {
    await exportWorkspaceData(selectedKind.value, format)
    toast.add({ severity: 'success', summary: t('dataImport.exportCompleted'), detail: t('dataImport.exportedFileReady'), life: 2500 })
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('dataImport.exportFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    loadingRef.value = false
  }
}

function openImportedSection() {
  if (selectedKind.value === 'knowledge') {
    navigate('knowledge')
    return
  }
  if (selectedKind.value === 'logbook') {
    navigate('logbook')
    return
  }
  navigate('prompts')
}
</script>

<style scoped>
.data-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
}

.page-header h2,
.page-header p {
  margin: 0;
}

.page-header p {
  margin-top: 6px;
  color: #51606f;
}

.grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}

.stack-md,
.stack-sm {
  display: flex;
  flex-direction: column;
}

.stack-md {
  gap: 14px;
}

.stack-sm {
  gap: 10px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.field-grow {
  flex: 1 1 240px;
  min-width: min(100%, 240px);
}

.hidden-input {
  display: none;
}

.inline-note {
  margin: 0;
  color: #51606f;
  font-size: 0.94rem;
}

.steps {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.step-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(32, 98, 177, 0.08);
  color: #254d76;
  font-size: 0.83rem;
  font-weight: 600;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  padding: 14px;
  border-radius: 16px;
  background: #f6faff;
  border: 1px solid rgba(48, 104, 178, 0.08);
}

.summary-item strong,
.summary-item span {
  display: block;
}

.summary-item strong {
  font-size: 1.25rem;
  color: #17324d;
}

.summary-item span {
  margin-top: 4px;
  color: #5a6f84;
  font-size: 0.88rem;
}

.result-panel {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(38, 114, 161, 0.12);
  background: linear-gradient(135deg, rgba(242, 251, 255, 0.9), rgba(247, 255, 250, 0.95));
}

.result-panel h3 {
  margin: 0 0 12px;
}

.export-row {
  align-items: stretch;
}

@media (max-width: 1180px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-header {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
