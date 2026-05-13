import { get, getBlob, post } from './api'
import { downloadBlob } from './utils/blob'
import type {
  AutoTestExportFormat,
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
  PromoteToKnowledgeResponse,
} from './types'

export const AUTOTEST_RUN_TIMEOUT_MS = 5 * 60 * 1000

export async function listAutoTestRuns(): Promise<AutoTestRunListItemResponse[]> {
  return get<AutoTestRunListItemResponse[]>('/api/autotest/runs')
}

export async function getAutoTestCapabilities(): Promise<AutoTestCapabilitiesResponse> {
  return get<AutoTestCapabilitiesResponse>('/api/autotest/capabilities')
}

export async function getAutoTestRun(runId: string): Promise<AutoTestRunResponse> {
  return get<AutoTestRunResponse>(`/api/autotest/runs/${runId}`)
}

export async function startAutoTest(formData: FormData): Promise<AutoTestRunResponse> {
  return post<AutoTestRunResponse, FormData>('/api/autotest/run', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: AUTOTEST_RUN_TIMEOUT_MS,
  })
}

export async function promoteAutoTestProblem(entryId: string): Promise<PromoteToKnowledgeResponse> {
  return post<PromoteToKnowledgeResponse>(`/api/logbook/entries/${entryId}/promote-to-knowledge`)
}

export async function downloadAutoTestReport(runId: string, format: AutoTestExportFormat): Promise<void> {
  const blob = await getBlob(`/api/autotest/${runId}/export`, {
    params: { format },
  })
  downloadBlob(blob, `autotest-report-${runId}.${format}`)
}
