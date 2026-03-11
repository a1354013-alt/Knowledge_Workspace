# 企業 AI 助理 - 前端 (Vue 3 + PrimeVue)

Vue 3 + PrimeVue 企業級前端應用，提供直觀的文件管理、問答、表單生成介面。

## ✨ 功能特性

### 文件管理
- 📤 上傳文件 (PDF/TXT/MD)
- 🔐 設定允許查看的角色 (MultiSelect)
- 📋 查看已上傳文件列表
- 🗑️ 刪除文件

### 智能問答
- 💬 提交問題
- 🔍 基於 RAG 的智能回答
- 📚 顯示引用來源
- 👤 支援多角色查詢

### 表單生成
- 📝 4 種預設模板
- 📋 動態表單欄位
- ✅ 必填欄位驗證
- 📋 複製生成內容

### 角色管理
- 👨‍💼 員工 (Employee)
- 👔 主管 (Manager)
- 👨‍💼 人資 (HR)

## 📁 專案結構

```
frontend-vue/
├── src/
│   ├── App.vue              # 主應用元件（完整功能）
│   ├── main.js              # Vue 應用入口
│   ├── components/          # 組件目錄（可擴展）
│   ├── views/               # 頁面目錄（可擴展）
│   └── assets/              # 靜態資源
├── index.html               # HTML 模板
├── vite.config.js           # Vite 配置
├── package.json             # 依賴配置
├── .env.example             # 環境變數範例
├── .env                     # 環境變數配置（本地）
└── README.md                # 本檔案
```

## 🚀 快速啟動

### 1. 安裝依賴
```bash
npm install
```

### 2. 配置環境變數
複製 `.env.example` 為 `.env`：
```bash
cp .env.example .env
```

編輯 `.env` 檔案（可選）：
```env
# API 基礎 URL
VITE_API_BASE=http://localhost:8000
```

### 3. 啟動開發伺服器
```bash
npm run dev
```

✅ 看到 `Local: http://localhost:3000` 表示啟動成功

### 4. 打開瀏覽器
訪問 `http://localhost:3000`

## 🛠️ 開發命令

```bash
# 啟動開發伺服器
npm run dev

# 構建生產版本
npm run build

# 預覽生產構建
npm run preview

# 檢查類型
npm run type-check
```

## 🎨 UI 組件

使用 **PrimeVue 4.0** 企業級 UI 組件庫：

| 組件 | 用途 |
|------|------|
| `Card` | 卡片容器 |
| `Button` | 按鈕（支援 loading 狀態） |
| `Dropdown` | 下拉選擇 |
| `MultiSelect` | 多選（角色選擇） |
| `InputText` | 文本輸入 |
| `Textarea` | 文本區域（自動調整高度） |
| `Toast` | 通知提示 |

## 🔌 API 整合

### 環境變數
```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
```

### API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/docs/upload` | 上傳文件 |
| GET | `/api/docs` | 列出文件 |
| DELETE | `/api/docs/{doc_id}` | 刪除文件 |
| POST | `/api/qa` | 提交問題 |
| POST | `/api/generate` | 生成表單 |

## 📋 表單驗證

### 必填欄位檢查
生成表單前會自動檢查所有欄位是否已填寫：
```javascript
const missingFields = currentTemplateFields.value.filter(
  field => !formInputs.value[field]
)
if (missingFields.length > 0) {
  // 顯示錯誤提示
}
```

### 模板欄位定義
```javascript
const templateFieldsMap = {
  '請假通知': ['請假類型', '請假日期', '請假天數', '原因'],
  '加班申請說明': ['加班日期', '加班時數', '加班原因', '預期完成時間'],
  '變更申請摘要': ['變更項目', '變更內容', '影響範圍', '實施時間'],
  '會議紀錄': ['會議名稱', '出席人員', '主要議題', '決議事項']
}
```

## 🎯 核心功能實現

### 1. 文件上傳
```javascript
const uploadFile = async () => {
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('allowed_roles', uploadRoles.value.join(','))
  
  const response = await axios.post(`${API_BASE}/api/docs/upload`, formData)
}
```

### 2. 問答
```javascript
const askQuestion = async () => {
  const response = await axios.post(`${API_BASE}/api/qa`, {
    question: question.value,
    user_role: userRole.value
  })
  qaResponse.value = response.data
}
```

### 3. 表單生成
```javascript
const generateForm = async () => {
  // 驗證必填欄位
  const missingFields = currentTemplateFields.value.filter(
    field => !formInputs.value[field]
  )
  if (missingFields.length > 0) {
    // 顯示錯誤
    return
  }
  
  const response = await axios.post(`${API_BASE}/api/generate`, {
    template_type: templateType.value,
    inputs: formInputs.value,
    user_role: userRole.value
  })
  generatedContent.value = response.data.content
}
```

## 🔄 狀態管理

### 使用 Vue 3 Composition API
```javascript
const userRole = ref('employee')
const documents = ref([])
const question = ref('')
const qaResponse = ref(null)
const templateType = ref('請假通知')
const formInputs = ref({})
const generatedContent = ref('')
```

### 計算屬性
```javascript
const currentTemplateFields = computed(() => {
  return templateFieldsMap[templateType.value] || []
})
```

## 📱 響應式設計

### 三欄布局
```css
.main-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
}

@media (max-width: 1024px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}
```

## 🔔 通知系統

使用 PrimeVue Toast 提供實時反饋：
```javascript
const toast = useToast()

toast.add({ 
  severity: 'success', 
  summary: '成功', 
  detail: '操作完成', 
  life: 3000 
})
```

## 🎨 樣式主題

使用 **Lara Light Blue** 主題：
```javascript
import 'primevue/resources/themes/lara-light-blue/theme.css'
```

可在 `main.js` 中更換主題。

## 🚨 常見問題

### 1. API 連接失敗
**原因**: 後端未啟動或 `VITE_API_BASE` 配置錯誤  
**解決**: 
- 確認後端運行在 `http://localhost:8000`
- 檢查 `.env` 中的 `VITE_API_BASE` 設定

### 2. 上傳失敗
**原因**: 檔案格式不支援或大小超限  
**解決**: 
- 僅上傳 `.pdf`, `.txt`, `.md` 檔案
- 檔案大小不超過 50MB

### 3. 表單欄位未顯示
**原因**: 模板切換時未重置表單  
**解決**: 
- 檢查 `onTemplateChange` 是否正確重置 `formInputs`

### 4. Toast 通知不顯示
**原因**: `ToastService` 未在 `main.js` 中註冊  
**解決**: 
- 確認 `main.js` 中有 `app.use(ToastService)`

## 📚 技術棧

| 技術 | 版本 | 說明 |
|------|------|------|
| Vue | 3.4.0 | JavaScript 框架 |
| PrimeVue | 4.0.0 | UI 組件庫 |
| Vite | 5.0.0 | 構建工具 |
| Axios | 1.6.0 | HTTP 客戶端 |
| PrimeIcons | 6.0.0 | 圖標庫 |

## 🔐 安全性考慮

- ✅ 使用 HTTPS 在生產環境
- ✅ 驗證所有使用者輸入
- ✅ 不在前端存儲敏感資訊
- ✅ 使用環境變數管理 API 端點

## 📈 性能最佳實踐

- ✅ 使用 `computed` 避免不必要的重新渲染
- ✅ 使用 `ref` 管理局部狀態
- ✅ 非同步操作使用 `async/await`
- ✅ 使用 Vite 進行快速開發和生產構建

## 🚀 部署

### 構建生產版本
```bash
npm run build
```

### 部署靜態檔案
生成的 `dist/` 目錄包含所有靜態檔案，可部署到任何靜態主機。

## 📞 支援

- 📖 查看 PrimeVue 文檔：https://primevue.org/
- 💡 查看 Vue 3 文檔：https://vuejs.org/
- 🐛 發現 Bug？檢查瀏覽器控制台查看錯誤信息

---

**版本**: 1.0.0 MVP  
**最後更新**: 2026-02-05
