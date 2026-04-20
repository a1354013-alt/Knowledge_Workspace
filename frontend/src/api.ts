/**
 * Enhanced API client with TypeScript types and unified error handling.
 * Provides interceptors for 401, 500, 503 errors with user-friendly messages.
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import type { AxiosInstance } from 'axios'
import { clearToken, getToken, notifyUnauthorized } from './auth.js'
import type { ApiError } from './types'

const API_BASE_URL = import.meta?.env?.VITE_API_BASE || process.env.VITE_API_BASE || 'http://localhost:8000'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// Request interceptor: attach auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
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
  (response) => response.data,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status ?? 0
    const detail = error.response?.data?.detail || error.message || 'Request failed.'
    const requestUrl = String(error.config?.url || '')

    // Handle 401 Unauthorized
    if (status === 401 && !requestUrl.includes('/api/login')) {
      clearToken()
      notifyUnauthorized(detail)
      return Promise.reject({
        status: 401,
        message: 'Session expired. Please sign in again.',
        detail,
      })
    }

    // Handle 500 Internal Server Error
    if (status === 500) {
      return Promise.reject({
        status: 500,
        message: 'Server error occurred. Please try again later.',
        detail,
      })
    }

    // Handle 503 Service Unavailable
    if (status === 503) {
      return Promise.reject({
        status: 503,
        message: 'Service temporarily unavailable. Please try again later.',
        detail,
      })
    }

    // Handle 429 Too Many Requests (Rate Limiting)
    if (status === 429) {
      return Promise.reject({
        status: 429,
        message: 'Too many requests. Please slow down and try again later.',
        detail,
      })
    }

    // Handle other errors
    return Promise.reject({
      status,
      message: detail,
      detail,
    } as ApiError)
  }
)

// Export typed helper functions
export async function get<T>(url: string): Promise<T> {
  return apiClient.get<T>(url)
}

export async function post<T, D = unknown>(url: string, data?: D): Promise<T> {
  return apiClient.post<T>(url, data)
}

export async function patch<T, D = unknown>(url: string, data?: D): Promise<T> {
  return apiClient.patch<T>(url, data)
}

export async function put<T, D = unknown>(url: string, data?: D): Promise<T> {
  return apiClient.put<T>(url, data)
}

export async function del<T>(url: string): Promise<T> {
  return apiClient.delete<T>(url)
}
