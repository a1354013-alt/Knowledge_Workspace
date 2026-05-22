import { onMounted, ref } from 'vue'

import { adaptDashboardHealth, type DashboardHealthViewModel } from '../../adapters/dashboard'
import { get } from '../../api'
import type { DashboardHealthResponse } from '../../types'

export function formatPercentage(value: number | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '0%'
  }
  return `${Math.round(value)}%`
}

export function calculateStatusWidth(count: number, total: number): string {
  if (total === 0) {
    return '0%'
  }
  return `${Math.round((count / total) * 100)}%`
}

export function capitalizeStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatDateTime(dateStr: string): string {
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

export function useProjectHealth() {
  const data = ref<DashboardHealthViewModel | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function loadDashboard() {
    loading.value = true
    error.value = ''
    try {
      const response = await get<DashboardHealthResponse>('/api/dashboard/health')
      if (!response || typeof response !== 'object' || Array.isArray(response)) {
        throw new Error('Dashboard API returned an invalid payload.')
      }
      const requiredSections = ['knowledge', 'logbook', 'autotest', 'documents', 'recent_activity'] as const
      for (const key of requiredSections) {
        if (!(key in response)) {
          throw new Error(`Dashboard API payload is missing '${key}'.`)
        }
      }
      data.value = adaptDashboardHealth(response)
    } catch (err: unknown) {
      const apiError = err as { message?: string; detail?: string }
      error.value = apiError?.message || apiError?.detail || 'Failed to load dashboard metrics'
    } finally {
      loading.value = false
    }
  }

  onMounted(loadDashboard)

  return {
    data,
    error,
    loading,
    loadDashboard,
  }
}
