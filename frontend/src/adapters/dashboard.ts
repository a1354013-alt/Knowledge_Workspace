import type { DashboardHealthResponse } from '../generated/api-types'

export type DashboardHealthViewModel = Omit<DashboardHealthResponse, 'knowledge' | 'autotest'> & {
  knowledge: Omit<DashboardHealthResponse['knowledge'], 'by_status'> & {
    by_status: Record<string, number>
  }
  autotest: Omit<DashboardHealthResponse['autotest'], 'recent_runs'> & {
    recent_runs: NonNullable<DashboardHealthResponse['autotest']['recent_runs']>
  }
}

function numberRecord(value: Record<string, unknown> | undefined): Record<string, number> {
  const result: Record<string, number> = {}
  for (const [key, raw] of Object.entries(value ?? {})) {
    result[key] = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0
  }
  return result
}

export function adaptDashboardHealth(response: DashboardHealthResponse): DashboardHealthViewModel {
  return {
    ...response,
    knowledge: {
      ...response.knowledge,
      by_status: numberRecord(response.knowledge.by_status),
    },
    autotest: {
      ...response.autotest,
      recent_runs: response.autotest.recent_runs ?? [],
    },
  }
}
