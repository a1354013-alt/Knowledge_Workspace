# v4.2 版本更新日誌

## 🎯 版本目標
前端 API 統一和 Token 管理改進

## ✅ 完成的工作

### 1. 前端 API 統一 (App.vue + AdminConsole.vue)
- **目標**：移除 fetch 混用，統一使用 axios
- **實現**：
  - 建立 `frontend-vue/src/api.js` 統一 API Service
  - 所有 HTTP 呼叫改用 `apiClient.get/post/patch/delete`
  - 自動注入 Authorization header
  - 統一錯誤處理和回傳格式

### 2. Token 管理改進 (api.js)
- **目標**：Token 不要長期存放於 localStorage
- **實現**：
  - Token 改為 memory + sessionStorage 存儲
  - 應用重新載入時自動恢復 token
  - 登出時清理 sessionStorage
  - 提供 `setToken/clearToken/getToken/restoreToken` 函式

### 3. 401/403 失效處理
- **目標**：自動登出機制
- **實現**：
  - apiClient 響應攔截器自動攔截 401/403
  - 觸發 `auth:unauthorized` 事件
  - App.vue 監聽事件自動調用 `logout()`
  - AdminConsole.vue 監聽事件自動關閉

### 4. 後端環境配置
- **建立檔案**：
  - `backend/requirements.txt` - 依賴清單
  - `backend/.env` - 環境變數配置
- **安裝依賴**：
  - FastAPI + Uvicorn
  - SQLAlchemy + Alembic
  - ChromaDB + LangChain
  - JWT 認證
  - PDF/文檔處理

### 5. 前端項目配置
- **建立檔案**：
  - `frontend-vue/package.json` - 項目配置
  - `frontend-vue/vite.config.js` - Vite 配置
  - `frontend-vue/index.html` - HTML 入口
  - `frontend-vue/.env.local` - 環境變數

## 📝 修改清單

### frontend-vue/src/api.js (新建)
```javascript
- Token 管理（memory + sessionStorage）
- axios instance 創建
- 請求攔截器（自動注入 token）
- 響應攔截器（401/403 自動登出）
- 統一錯誤處理
```

### frontend-vue/src/App.vue
```javascript
// 修改：
- import { apiClient, setToken, clearToken, restoreToken, getToken } from './api'
- 所有 fetch 改用 apiClient
- logout() 使用 clearToken()
- 新增 handleUnauthorized() 函式
- onMounted() 監聽 auth:unauthorized 事件
```

### frontend-vue/src/components/AdminConsole.vue
```javascript
// 修改：
- import { apiClient } from '@/api'
- 移除 axios 和 getAuthHeader()
- 所有 API 呼叫改用 apiClient
- 監聽 auth:unauthorized 事件自動關閉
```

## 🔧 技術細節

### Token 流程
1. 登入成功 → `setToken(token)` → 存入 memory + sessionStorage
2. 頁面重新載入 → `restoreToken()` → 從 sessionStorage 恢復
3. 每個 API 呼叫 → 請求攔截器自動注入 Authorization header
4. Token 過期 → 401 響應 → 觸發 auth:unauthorized 事件 → 自動登出

### API 呼叫模式
```javascript
// 舊方式（已移除）
const response = await fetch(`${API_BASE}/api/docs`, {
  headers: { 'Authorization': `Bearer ${authToken.value}` }
})

// 新方式（統一使用）
const documents = await apiClient.get('/api/docs')
```

### 錯誤處理
```javascript
// apiClient 自動處理
- 401 Unauthorized → 清理 token，觸發登出事件
- 403 Forbidden → 拒絕訪問提示
- 其他錯誤 → 統一格式返回
```

## 🚀 後續階段

### v4.3: 後端 Dependency 遷移 + 輸入驗證補強
- 後端 endpoints 改用 Dependency injection
- 補強輸入驗證（長度限制、格式限制、空值處理）

### v4.4: 文件流程防呆 + RAG 優化
- 文件流程加入狀態檢查
- RAG 查詢加入相似度門檻
- 無 LLM 時實作 retrieval fallback

### v4.5: 元件拆分 + 日誌統一 + 代碼清理
- 拆分過胖的 App.vue
- 統一日誌格式（結構化欄位）
- 清理重複代碼和資源

## 📊 測試清單

- [ ] 登入/登出流程
- [ ] Token 自動恢復（頁面重新載入）
- [ ] Token 過期自動登出（401 處理）
- [ ] 文件上傳/列表/刪除
- [ ] 問答功能
- [ ] 表單生成
- [ ] Admin 後台用戶管理
- [ ] Admin 後台文件審核

## 🔐 安全性改進

- ✅ Token 不再長期存放於 localStorage
- ✅ 自動登出機制（401 攔截）
- ✅ 統一 Authorization header 注入
- ✅ 統一錯誤處理（避免洩露敏感信息）

## 📦 部署檢查清單

- [ ] 後端依賴完全安裝
- [ ] 後端 API 正常運行
- [ ] 前端 API 統一完成
- [ ] 401/403 失效處理正常
- [ ] 集成測試通過
- [ ] 代碼審查完成
- [ ] 文檔更新完成
