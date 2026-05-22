import { get, getBlob, post } from './api'
import { API_UPLOAD_TIMEOUT_MS, apiPaths } from './api/endpoints'
import { downloadBlob } from './utils/blob'
import type {
  AutoTestExportFormat,
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
  PromoteToKnowledgeResponse,
} from './types'

export async function listAutoTestRuns(): Promise<AutoTestRunListItemResponse[]> {
  return get<AutoTestRunListItemResponse[]>(apiPaths.autotest.listRuns)
}

export async function getAutoTestCapabilities(): Promise<AutoTestCapabilitiesResponse> {
  return get<AutoTestCapabilitiesResponse>(apiPaths.autotest.capabilities)
}

export async function getAutoTestRun(runId: string): Promise<AutoTestRunResponse> {
  return get<AutoTestRunResponse>(apiPaths.autotest.detail(runId))
}

export async function startAutoTest(formData: FormData): Promise<AutoTestRunResponse> {
  return post<AutoTestRunResponse, FormData>(apiPaths.autotest.run, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: API_UPLOAD_TIMEOUT_MS,
  })
}

export async function promoteAutoTestProblem(entryId: string): Promise<PromoteToKnowledgeResponse> {
  return post<PromoteToKnowledgeResponse>(apiPaths.logbook.promote(entryId))
}

export async function downloadAutoTestReport(runId: string, format: AutoTestExportFormat): Promise<void> {
  const blob = await getBlob(apiPaths.autotest.exportReport(runId), {
    params: { format },
  })
  downloadBlob(blob, `autotest-report-${runId}.${format}`)
}
