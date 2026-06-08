import ExcelJS from 'exceljs'

import { del, get, patch, post } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import { downloadBlob } from '../utils/blob'
import type {
  KnowledgeEntryCreateRequest,
  KnowledgeEntryResponse,
  LogbookEntryCreateRequest,
  LogbookEntryResponse,
  MessageResponse,
  SavedPromptCreateRequest,
  SavedPromptResponse,
} from '../types'

export type WorkspaceDataKind = 'knowledge' | 'logbook' | 'prompt'
export type ExportFormat = 'xlsx' | 'json'

export type ImportErrorDetail = {
  row: number
  field: string
  reason: string
}

export type ImportPreviewRow = {
  rowNumber: number
  values: Record<string, string>
}

export type ImportAnalysis = {
  kind: WorkspaceDataKind
  headers: string[]
  previewRows: ImportPreviewRow[]
  validRows: ImportPreviewRow[]
  skippedRows: number
  totalRows: number
  errors: ImportErrorDetail[]
}

export type ImportResult = {
  totalRows: number
  successRows: number
  failedRows: number
  skippedRows: number
  errors: ImportErrorDetail[]
}

type ImportSchema = {
  columns: string[]
  required: string[]
  sample: Record<string, string>
  filename: string
}

const MAX_IMPORT_BYTES = 5 * 1024 * 1024
const MAX_IMPORT_ROWS = 500
const PREVIEW_ROW_LIMIT = 12
const DEMO_TITLE_PREFIX = '[DEMO]'

const importSchemas: Record<WorkspaceDataKind, ImportSchema> = {
  knowledge: {
    columns: ['title', 'problem', 'root_cause', 'solution', 'tags', 'notes', 'status', 'source_ref'],
    required: ['title', 'problem', 'solution'],
    filename: 'knowledge-base-template.xlsx',
    sample: {
      title: 'Ollama fallback mode note',
      problem: 'When Ollama is offline, generation features should degrade gracefully.',
      root_cause: 'The local provider was unavailable during startup.',
      solution: 'Show an unavailable/fallback status while keeping search and knowledge flows usable.',
      tags: 'ollama,llm,fallback',
      notes: 'Used for local showcase and troubleshooting.',
      status: 'reviewed',
      source_ref: '',
    },
  },
  logbook: {
    columns: ['title', 'problem', 'root_cause', 'solution', 'tags', 'status', 'source_ref'],
    required: ['title', 'problem', 'solution', 'status'],
    filename: 'problem-logbook-template.xlsx',
    sample: {
      title: 'Invalid credentials during sign-in',
      problem: 'A user could not sign in to the workspace.',
      root_cause: 'The local .env password no longer matched the seeded owner account.',
      solution: 'Reset the owner password and restart the backend.',
      tags: 'auth,login,bootstrap',
      status: 'draft',
      source_ref: '',
    },
  },
  prompt: {
    columns: ['title', 'content', 'tags'],
    required: ['title', 'content'],
    filename: 'prompts-template.xlsx',
    sample: {
      title: 'Code review prompt',
      content: 'Review this diff with a focus on regressions, tests, and operational risk.',
      tags: 'review,quality',
    },
  },
}

const allowedStatuses = new Set(['draft', 'reviewed', 'verified', 'archived'])

function getSchema(kind: WorkspaceDataKind): ImportSchema {
  return importSchemas[kind]
}

function normalizeCellValue(value: unknown): string {
  return String(value ?? '').trim()
}

function dateStamp(now = new Date()): string {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

function exportBaseFilename(kind: WorkspaceDataKind): string {
  if (kind === 'knowledge') {
    return 'knowledge-base'
  }
  if (kind === 'logbook') {
    return 'problem-logbook'
  }
  return 'prompts'
}

function buildWorkbook(headers: string[], row: Record<string, string>, sheetName: string) {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet(sheetName)
  worksheet.addRow(headers)
  worksheet.addRow(headers.map((header) => row[header] ?? ''))
  return workbook
}

function isFormulaCell(cell: ExcelJS.Cell): boolean {
  return cell.type === ExcelJS.ValueType.Formula || Boolean(cell.formula)
}

function getCellText(cell: ExcelJS.Cell): string {
  if (isFormulaCell(cell)) {
    return normalizeCellValue(cell.result ?? '')
  }
  return normalizeCellValue(cell.text || cell.value)
}

function getRowValues(row: ExcelJS.Row, columnCount: number): string[] {
  return Array.from({ length: columnCount }, (_, index) => getCellText(row.getCell(index + 1)))
}

async function downloadWorkbook(workbook: ExcelJS.Workbook, filename: string) {
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer as BlobPart], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  downloadBlob(blob, filename)
}

function listFormulaErrors(worksheet: ExcelJS.Worksheet, headers: string[]): ImportErrorDetail[] {
  const errors: ImportErrorDetail[] = []
  for (let rowNumber = 2; rowNumber <= worksheet.rowCount; rowNumber += 1) {
    const row = worksheet.getRow(rowNumber)
    for (let columnIndex = 1; columnIndex <= headers.length; columnIndex += 1) {
      if (!isFormulaCell(row.getCell(columnIndex))) {
        continue
      }
      errors.push({
        row: rowNumber,
        field: headers[columnIndex - 1] ?? t('common.field'),
        reason: t('dataImport.formulaNotSupported'),
      })
    }
  }
  return errors
}

export function getImportLimits() {
  return {
    maxBytes: MAX_IMPORT_BYTES,
    maxRows: MAX_IMPORT_ROWS,
  }
}

export async function downloadImportTemplate(kind: WorkspaceDataKind) {
  const schema = getSchema(kind)
  const workbook = buildWorkbook(schema.columns, schema.sample, kind)
  await downloadWorkbook(workbook, schema.filename)
}

export async function analyzeImportFile(kind: WorkspaceDataKind, file: File): Promise<ImportAnalysis> {
  const schema = getSchema(kind)
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    throw new Error(t('dataImport.unsupportedFileType'))
  }
  if (file.size > MAX_IMPORT_BYTES) {
    throw new Error(t('dataImport.fileTooLarge', { sizeMb: String(MAX_IMPORT_BYTES / 1024 / 1024) }))
  }

  const buffer = await file.arrayBuffer()
  const workbook = new ExcelJS.Workbook()
  await workbook.xlsx.load(buffer)
  const worksheet = workbook.worksheets[0]

  if (!worksheet) {
    throw new Error(t('dataImport.emptyFile'))
  }

  const headerColumnCount = Math.max(worksheet.getRow(1).cellCount, worksheet.columnCount)
  const headers = getRowValues(worksheet.getRow(1), headerColumnCount).map((value) => value.toLowerCase())
  if (!headers.length || headers.every((value) => !value)) {
    throw new Error(t('dataImport.emptyHeader'))
  }

  const missingHeaders = schema.required.filter((field) => !headers.includes(field))
  const errors: ImportErrorDetail[] = listFormulaErrors(worksheet, headers)
  if (missingHeaders.length) {
    errors.push(
      ...missingHeaders.map((field) => ({
        row: 1,
        field,
        reason: t('dataImport.missingRequiredField'),
      }))
    )
  }

  const rawDataRows = Array.from({ length: Math.max(worksheet.rowCount - 1, 0) }, (_, index) => {
    const rowNumber = index + 2
    return {
      rowNumber,
      values: getRowValues(worksheet.getRow(rowNumber), headers.length),
    }
  })
  if (!rawDataRows.length) {
    throw new Error(t('dataImport.emptyFile'))
  }
  if (rawDataRows.length > MAX_IMPORT_ROWS) {
    throw new Error(t('dataImport.tooManyRows', { count: String(MAX_IMPORT_ROWS) }))
  }

  const previewRows: ImportPreviewRow[] = []
  const validRows: ImportPreviewRow[] = []
  let skippedRows = 0

  rawDataRows.forEach((row) => {
    const values = Object.fromEntries(headers.map((header, headerIndex) => [header, normalizeCellValue(row.values[headerIndex])]))
    const populatedFields = Object.values(values).filter(Boolean)
    if (!populatedFields.length) {
      skippedRows += 1
      errors.push({ row: row.rowNumber, field: '-', reason: t('dataImport.emptyRow') })
      return
    }

    const rowErrors: ImportErrorDetail[] = []
    for (const field of schema.required) {
      if (!values[field]) {
        rowErrors.push({ row: row.rowNumber, field, reason: t('dataImport.missingRequiredField') })
      }
    }

    if ('status' in values && values.status && !allowedStatuses.has(values.status)) {
      rowErrors.push({ row: row.rowNumber, field: 'status', reason: t('dataImport.invalidStatus') })
    }

    if (previewRows.length < PREVIEW_ROW_LIMIT) {
      previewRows.push({ rowNumber: row.rowNumber, values })
    }
    if (!rowErrors.length) {
      validRows.push({ rowNumber: row.rowNumber, values })
    }
    errors.push(...rowErrors)
  })

  if (validRows.length === 0) {
    throw new Error(t('dataImport.noValidRows'))
  }

  return {
    kind,
    headers,
    previewRows,
    validRows,
    skippedRows,
    totalRows: rawDataRows.length,
    errors,
  }
}

async function createKnowledgeFromRow(row: Record<string, string>) {
  const payload: KnowledgeEntryCreateRequest = {
    title: row.title,
    problem: row.problem,
    root_cause: row.root_cause ?? '',
    solution: row.solution,
    tags: row.tags ?? '',
    notes: row.notes ?? '',
    status: (row.status as KnowledgeEntryCreateRequest['status']) || 'draft',
    source_type: 'manual',
    source_ref: row.source_ref ?? '',
    related_item_ids: [],
  }
  await post<MessageResponse, KnowledgeEntryCreateRequest>(apiPaths.knowledge.list, payload)
}

async function createLogbookFromRow(row: Record<string, string>) {
  const payload: LogbookEntryCreateRequest = {
    title: row.title,
    problem: row.problem,
    root_cause: row.root_cause ?? '',
    solution: row.solution,
    tags: row.tags ?? '',
    status: (row.status as LogbookEntryCreateRequest['status']) || 'draft',
    source_type: 'manual',
    source_ref: row.source_ref ?? '',
    related_item_ids: [],
  }
  await post<MessageResponse, LogbookEntryCreateRequest>(apiPaths.logbook.list, payload)
}

async function createPromptFromRow(row: Record<string, string>) {
  const payload: SavedPromptCreateRequest = {
    title: row.title,
    content: row.content,
    tags: row.tags ?? '',
  }
  await post<SavedPromptResponse, SavedPromptCreateRequest>(apiPaths.prompts.list, payload)
}

export async function submitImport(analysis: ImportAnalysis): Promise<ImportResult> {
  const errors: ImportErrorDetail[] = []
  let successRows = 0

  for (const row of analysis.validRows) {
    try {
      if (analysis.kind === 'knowledge') {
        await createKnowledgeFromRow(row.values)
      } else if (analysis.kind === 'logbook') {
        await createLogbookFromRow(row.values)
      } else {
        await createPromptFromRow(row.values)
      }
      successRows += 1
    } catch (error: unknown) {
      const apiError = error as { message?: string }
      errors.push({
        row: row.rowNumber,
        field: '-',
        reason: apiError?.message || t('common.requestFailed'),
      })
    }
  }

  const invalidRows = analysis.totalRows - analysis.validRows.length - analysis.skippedRows
  return {
    totalRows: analysis.totalRows,
    successRows,
    failedRows: invalidRows + errors.length,
    skippedRows: analysis.skippedRows,
    errors: [...analysis.errors, ...errors],
  }
}

type ExportRow = Record<string, string>

async function fetchKnowledgeRows(): Promise<ExportRow[]> {
  const items = await get<KnowledgeEntryResponse[]>(apiPaths.knowledge.list)
  return items.map((item) => ({
    title: item.title || '',
    problem: item.problem || '',
    root_cause: item.root_cause || '',
    solution: item.solution || '',
    tags: item.tags || '',
    notes: item.notes || '',
    status: item.status || 'draft',
    source_ref: item.source_ref || '',
  }))
}

async function fetchLogbookRows(): Promise<ExportRow[]> {
  const items = await get<LogbookEntryResponse[]>(apiPaths.logbook.list)
  return items.map((item) => ({
    title: item.title || '',
    problem: item.problem || '',
    root_cause: item.root_cause || '',
    solution: item.solution || '',
    tags: item.tags || '',
    status: item.status || 'draft',
    source_ref: item.source_ref || '',
  }))
}

async function fetchPromptRows(): Promise<ExportRow[]> {
  const items = await get<SavedPromptResponse[]>(apiPaths.prompts.list)
  return items.map((item) => ({
    title: item.title || '',
    content: item.content || '',
    tags: item.tags || '',
  }))
}

async function fetchExportRows(kind: WorkspaceDataKind): Promise<ExportRow[]> {
  if (kind === 'knowledge') {
    return fetchKnowledgeRows()
  }
  if (kind === 'logbook') {
    return fetchLogbookRows()
  }
  return fetchPromptRows()
}

export async function exportWorkspaceData(kind: WorkspaceDataKind, format: ExportFormat) {
  const schema = getSchema(kind)
  const rows = await fetchExportRows(kind)
  if (!rows.length) {
    throw new Error(t('dataImport.noDataToExport'))
  }

  const filename = `${exportBaseFilename(kind)}-${dateStamp()}`
  if (format === 'json') {
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json;charset=utf-8' })
    downloadBlob(blob, `${filename}.json`)
    return
  }

  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet(exportBaseFilename(kind))
  worksheet.addRow(schema.columns)
  rows.forEach((row) => {
    worksheet.addRow(schema.columns.map((column) => row[column] ?? ''))
  })
  await downloadWorkbook(workbook, `${filename}.xlsx`)
}

type DemoResult = {
  created: number
  skipped: number
}

const demoKnowledgeEntries: KnowledgeEntryCreateRequest[] = [
  {
    title: `${DEMO_TITLE_PREFIX} Vue DataTable edit event note`,
    problem: 'PrimeVue DataTable row edit handlers felt inconsistent during inline editing.',
    root_cause: 'The edit lifecycle was split across row state, emit timing, and optimistic UI updates.',
    solution: 'Centralize row editing state, save explicitly, and keep toast feedback close to the mutation path.',
    tags: 'primevue,datatable,ui',
    notes: 'Portfolio-friendly demo entry.',
    status: 'reviewed',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
  {
    title: `${DEMO_TITLE_PREFIX} FastAPI /docs vs root route`,
    problem: 'Developers assumed `/docs` readiness meant the root route behaved the same way.',
    root_cause: 'Health, root, and OpenAPI routes serve different purposes and had different expectations.',
    solution: 'Keep `/api/health` explicit for probes and document the distinction in onboarding notes.',
    tags: 'fastapi,docs,health',
    notes: 'Useful for local walkthroughs.',
    status: 'verified',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
  {
    title: `${DEMO_TITLE_PREFIX} Ollama fallback explanation`,
    problem: 'AI generation errors looked like total workspace failure when the local model was unavailable.',
    root_cause: 'LLM readiness and retrieval readiness were not clearly separated in the UI.',
    solution: 'Expose provider, model, fallback, and availability while keeping core features usable.',
    tags: 'ollama,llm,fallback',
    notes: 'Supports the dashboard demo story.',
    status: 'reviewed',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
]

const demoLogbookEntries: LogbookEntryCreateRequest[] = [
  {
    title: `${DEMO_TITLE_PREFIX} Invalid credentials during login`,
    problem: 'The owner account failed to sign in after environment changes.',
    root_cause: 'Seeded credentials and `.env` drifted out of sync.',
    solution: 'Reseed the owner account or align the backend env before retrying.',
    tags: 'auth,login',
    status: 'draft',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
  {
    title: `${DEMO_TITLE_PREFIX} bootstrap-dev failed after npm install`,
    problem: 'Frontend startup stopped after dependency installation warnings.',
    root_cause: 'A clean install was required because lockfile and local modules diverged.',
    solution: 'Delete local modules, run `npm ci`, then rerun the bootstrap command.',
    tags: 'node,npm,bootstrap',
    status: 'reviewed',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
  {
    title: `${DEMO_TITLE_PREFIX} AutoTest runner disabled mode`,
    problem: 'Users expected uploaded ZIP files to execute immediately during demos.',
    root_cause: 'Safe simulation mode was active by default, but the UI explanation was too subtle.',
    solution: 'Explain the runner mode in the panel and keep execution off by default.',
    tags: 'autotest,safety',
    status: 'reviewed',
    source_type: 'manual',
    source_ref: '',
    related_item_ids: [],
  },
]

const demoPrompts: SavedPromptCreateRequest[] = [
  {
    title: `${DEMO_TITLE_PREFIX} Code review prompt`,
    content: 'Review this change for regressions, missing tests, and operational risks. Prioritize actionable findings.',
    tags: 'review,quality',
  },
  {
    title: `${DEMO_TITLE_PREFIX} Error log analysis prompt`,
    content: 'Summarize the failure, identify the most likely root cause, and suggest the next debugging steps.',
    tags: 'logs,debugging',
  },
]

async function createMissingKnowledge(existingTitles: Set<string>): Promise<DemoResult> {
  let created = 0
  let skipped = 0
  for (const payload of demoKnowledgeEntries) {
    if (existingTitles.has(payload.title || '')) {
      skipped += 1
      continue
    }
    await post<MessageResponse, KnowledgeEntryCreateRequest>(apiPaths.knowledge.list, payload)
    created += 1
  }
  return { created, skipped }
}

async function createMissingLogbook(existingTitles: Set<string>): Promise<DemoResult> {
  let created = 0
  let skipped = 0
  for (const payload of demoLogbookEntries) {
    if (existingTitles.has(payload.title || '')) {
      skipped += 1
      continue
    }
    await post<MessageResponse, LogbookEntryCreateRequest>(apiPaths.logbook.list, payload)
    created += 1
  }
  return { created, skipped }
}

async function createMissingPrompts(existingTitles: Set<string>): Promise<DemoResult> {
  let created = 0
  let skipped = 0
  for (const payload of demoPrompts) {
    if (existingTitles.has(payload.title || '')) {
      skipped += 1
      continue
    }
    await post<SavedPromptResponse, SavedPromptCreateRequest>(apiPaths.prompts.list, payload)
    created += 1
  }
  return { created, skipped }
}

export async function createDemoData() {
  const [knowledge, logbook, prompts] = await Promise.all([
    get<KnowledgeEntryResponse[]>(apiPaths.knowledge.list),
    get<LogbookEntryResponse[]>(apiPaths.logbook.list),
    get<SavedPromptResponse[]>(apiPaths.prompts.list),
  ])

  const [knowledgeResult, logbookResult, promptResult] = await Promise.all([
    createMissingKnowledge(new Set(knowledge.map((item) => item.title))),
    createMissingLogbook(new Set(logbook.map((item) => item.title))),
    createMissingPrompts(new Set(prompts.map((item) => item.title))),
  ])

  return {
    created: knowledgeResult.created + logbookResult.created + promptResult.created,
    skipped: knowledgeResult.skipped + logbookResult.skipped + promptResult.skipped,
  }
}

export async function clearDemoData() {
  const [knowledge, logbook, prompts] = await Promise.all([
    get<KnowledgeEntryResponse[]>(apiPaths.knowledge.list),
    get<LogbookEntryResponse[]>(apiPaths.logbook.list),
    get<SavedPromptResponse[]>(apiPaths.prompts.list),
  ])

  let cleared = 0

  for (const item of knowledge.filter((entry) => entry.title.startsWith(DEMO_TITLE_PREFIX))) {
    await patch<MessageResponse>(apiPaths.knowledge.detail(item.id), { status: 'archived' })
    cleared += 1
  }

  for (const item of logbook.filter((entry) => entry.title.startsWith(DEMO_TITLE_PREFIX))) {
    await patch<MessageResponse>(apiPaths.logbook.detail(item.id), { status: 'archived' })
    cleared += 1
  }

  for (const item of prompts.filter((entry) => entry.title.startsWith(DEMO_TITLE_PREFIX))) {
    await del<MessageResponse>(apiPaths.prompts.detail(item.id))
    cleared += 1
  }

  return { cleared }
}
