/**
 * Enhanced API client with TypeScript types and unified error handling.
 * Provides interceptors for 401, 500, 503 errors with user-friendly messages.
 */

import axios, { AxiosError, type AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import type { AxiosInstance } from 'axios'
import { clearToken, getToken, notifyUnauthorized } from './auth'
import { API_TIMEOUT_MS, apiPaths } from './api/endpoints'
import type { ApiError } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export type ApiRequestConfig = AxiosRequestConfig & { skipAuth?: boolean }

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
})

function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === 'string') {
    const value = detail.trim()
    return value || undefined
  }
  if (!Array.isArray(detail)) {
    return undefined
  }

  const parts = detail
    .map((item) => {
      if (typeof item === 'string') {
        return item.trim()
      }
      if (!item || typeof item !== 'object') {
        return ''
      }
      const record = item as { loc?: unknown; msg?: unknown }
      const message = typeof record.msg === 'string' ? record.msg.trim() : ''
      const location = Array.isArray(record.loc)
        ? record.loc
            .map((part) => String(part).trim())
            .filter(Boolean)
            .join('.')
        : ''
      if (location && message) {
        return `${location}: ${message}`
      }
      return message
    })
    .filter(Boolean)

  return parts.length ? parts.join('; ') : undefined
}

// Request interceptor: attach auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig & { skipAuth?: boolean }) => {
    const token = getToken()
    if (!config.skipAuth && token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response interceptor: unified error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status ?? 0
    const responseData = error.response?.data
    const code = responseData?.code
    const details = responseData?.details
    const detail =
      formatDetail(responseData?.detail) ||
      formatDetail(details) ||
      (typeof responseData?.message === 'string' ? responseData.message.trim() || undefined : undefined) ||
      error.message ||
      'Request failed.'
    const message =
      (typeof responseData?.message === 'string' ? responseData.message.trim() || undefined : undefined) ||
      formatDetail(responseData?.detail) ||
      error.message ||
      'Request failed.'
    const requestUrl = String(error.config?.url || '')

    if (error.code === 'ECONNABORTED' || String(error.message || '').toLowerCase().includes('timeout')) {
      return Promise.reject({
        status,
        code,
        message: 'Request timed out.',
        details,
        detail,
      } as ApiError)
    }

    // Handle 401 Unauthorized
    if (status === 401 && !requestUrl.includes(apiPaths.auth.login)) {
      clearToken()
      notifyUnauthorized(detail)
      return Promise.reject({
        status: 401,
        code: code || 'unauthorized',
        message: 'Session expired. Please sign in again.',
        details,
        detail,
      })
    }

    // Handle other errors
    return Promise.reject({
      status,
      code,
      message,
      details,
      detail,
    } as ApiError)
  }
)

// Export typed helper functions
export async function get<T>(url: string, config?: ApiRequestConfig): Promise<T> {
  const response = await apiClient.get<T>(url, config)
  return response.data
}

export async function post<T, D = unknown>(url: string, data?: D, config?: ApiRequestConfig): Promise<T> {
  const response = await apiClient.post<T>(url, data, config)
  return response.data
}

export async function patch<T, D = unknown>(url: string, data?: D, config?: ApiRequestConfig): Promise<T> {
  const response = await apiClient.patch<T>(url, data, config)
  return response.data
}

export async function put<T, D = unknown>(url: string, data?: D, config?: ApiRequestConfig): Promise<T> {
  const response = await apiClient.put<T>(url, data, config)
  return response.data
}

export async function del<T>(url: string, config?: ApiRequestConfig): Promise<T> {
  const response = await apiClient.delete<T>(url, config)
  return response.data
}

export async function getBlob(url: string, config?: ApiRequestConfig): Promise<Blob> {
  const response = await apiClient.get(url, { ...config, responseType: 'blob' })
  return response.data as Blob
}
