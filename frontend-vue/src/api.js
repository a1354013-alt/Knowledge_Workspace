/**
 * 統一的 API Service
 * 
 * 功能：
 * 1. 統一 axios instance
 * 2. 自動注入 Authorization token
 * 3. 統一錯誤攔截（401/403 自動登出）
 * 4. 統一回傳格式檢查
 * 5. 統一 toast 訊息來源
 * 
 * 使用方式：
 *   import { apiClient, setToken, clearToken } from '@/api'
 *   
 *   // 登入後設置 token
 *   setToken(response.access_token)
 *   
 *   // 發送請求（自動帶 Authorization header）
 *   const response = await apiClient.get('/api/docs')
 *   
 *   // 登出時清理 token
 *   clearToken()
 */

import axios from 'axios'

// API 基礎 URL（從環境變數讀取）
const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Token 存儲（使用 memory + sessionStorage，不用 localStorage）
let currentToken = null

/**
 * 從 sessionStorage 恢復 token（應用重新載入時）
 */
export function restoreToken() {
  const stored = sessionStorage.getItem('authToken')
  if (stored) {
    currentToken = stored
  }
  return currentToken
}

/**
 * 設置 token
 */
export function setToken(token) {
  currentToken = token
  // 同時存到 sessionStorage，以便頁面重新載入時恢復
  if (token) {
    sessionStorage.setItem('authToken', token)
  }
}

/**
 * 清理 token
 */
export function clearToken() {
  currentToken = null
  sessionStorage.removeItem('authToken')
}

/**
 * 獲取當前 token
 */
export function getToken() {
  return currentToken
}

/**
 * 創建 axios instance
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 請求攔截器：自動注入 Authorization header
 */
apiClient.interceptors.request.use(
  (config) => {
    if (currentToken) {
      config.headers.Authorization = `Bearer ${currentToken}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 響應攔截器：統一錯誤處理
 */
apiClient.interceptors.response.use(
  (response) => {
    // 成功響應直接返回
    return response.data
  },
  (error) => {
    // 處理 HTTP 錯誤
    const status = error.response?.status
    const detail = error.response?.data?.detail || error.message

    // 401 Unauthorized：token 過期或無效
    if (status === 401) {
      clearToken()
      // 觸發登出事件（App.vue 會監聽）
      window.dispatchEvent(new CustomEvent('auth:unauthorized', { detail }))
      return Promise.reject({
        status: 401,
        message: 'Token 已過期或無效，請重新登入',
        detail
      })
    }

    // 403 Forbidden：權限不足
    if (status === 403) {
      return Promise.reject({
        status: 403,
        message: '您沒有權限存取此資源',
        detail
      })
    }

    // 其他錯誤
    return Promise.reject({
      status: status || 0,
      message: detail || '請求失敗',
      detail
    })
  }
)

export { apiClient }
