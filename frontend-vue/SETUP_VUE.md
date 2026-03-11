# 🚀 Vue 3 + PrimeVue 版本啟動指南

## 專案變更

✅ **前端已改寫為 Vue 3 + PrimeVue**
- 原 React 版本保留在 `frontend/` 目錄
- 新 Vue 版本在 `frontend-vue/` 目錄

## 快速開始

### 第一步：啟動後端（終端 1）

```bash
cd enterprise-ai-assistant/backend
pip install -r requirements.txt
python main.py
```

✅ 看到 `Uvicorn running on http://0.0.0.0:8000` 即成功

### 第二步：啟動前端（終端 2）

```bash
cd enterprise-ai-assistant/frontend-vue
npm install
npm run dev
```

✅ 看到 `Local: http://localhost:3000` 即成功

### 第三步：打開瀏覽器

訪問 **http://localhost:3000**

## 📁 目錄結構

```
enterprise-ai-assistant/
├── backend/              # FastAPI 後端（不變）
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── services.py
│   ├── requirements.txt
│   ├── .env
│   └── sample_docs/
│
├── frontend/             # React 版本（保留）
│   └── ...
│
├── frontend-vue/         # ✨ Vue 3 + PrimeVue 新版本
│   ├── src/
│   │   ├── App.vue       # 主應用元件
│   │   ├── main.js       # 應用入口
│   │   └── assets/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── README.md
│
├── README.md             # 完整文檔
├── QUICK_START.md        # 快速開始
└── SETUP_VUE.md         # 本檔案
```

## 🎨 Vue 版本特性

### 三欄布局
- **左欄**：文件管理
  - 上傳文件（PDF/TXT/MD）
  - 設定角色權限
  - 查看已上傳文件
  - 刪除文件

- **中欄**：智能問答
  - 輸入問題
  - 查看 AI 回答
  - 顯示引用來源

- **右欄**：表單生成
  - 選擇模板
  - 填寫表單欄位
  - 生成正式文字
  - 複製到剪貼板

### 核心功能
✅ 文件管理（上傳/列表/刪除）  
✅ RAG 問答（基於文件的回答）  
✅ 表單生成（4 種模板）  
✅ 角色權限（3 層角色控制）  
✅ 實時通知（Toast 提示）  

## 🔌 API 整合

所有 API 調用連接到後端：`http://localhost:8000`

### 主要端點
```
POST   /api/docs/upload      # 上傳文件
GET    /api/docs             # 列出文件
DELETE /api/docs/{doc_id}    # 刪除文件
POST   /api/qa               # 提交問題
POST   /api/generate         # 生成表單
GET    /docs                 # Swagger API 文檔
```

## 🛠️ 技術棧

| 組件 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4.0 | 漸進式 JavaScript 框架 |
| PrimeVue | 4.0.0 | 企業級 UI 組件庫 |
| Vite | 5.0.0 | 現代前端構建工具 |
| Axios | 1.6.0 | HTTP 客戶端 |

## 📝 使用示例

### 1️⃣ 上傳文件
```
1. 點擊「選擇文件」
2. 選擇 backend/sample_docs/leave_policy.txt
3. 選擇「允許查看角色」為「employee」
4. 點擊「上傳文件」
5. 看到成功提示
```

### 2️⃣ 提問
```
1. 在問答區輸入：「請假規定是什麼？」
2. 點擊「提交問題」
3. 查看回答和引用來源
```

### 3️⃣ 生成表單
```
1. 選擇「請假通知」模板
2. 填寫：
   - 請假類型：年假
   - 請假日期：2026-02-10
   - 請假天數：3
   - 原因：個人休息
3. 點擊「生成內容」
4. 複製生成的文本
```

## 🔐 角色管理

### 三種角色
- **employee** - 員工（基本權限）
- **manager** - 主管（擴展權限）
- **hr** - 人資（全部權限）

### 權限過濾
- 上傳文件時設定 `allowed_roles`
- 提問時根據 `user_role` 自動過濾
- 只能查看有權限的文件

## 🎯 PrimeVue 組件

### 使用的組件
- `Card` - 卡片容器
- `Button` - 按鈕（支援 loading 狀態）
- `Dropdown` - 下拉選擇
- `InputText` - 文本輸入
- `Textarea` - 文本區域（自動調整高度）
- `Toast` - 通知提示

### 樣式主題
使用 **Lara Light Blue** 主題，提供現代化的外觀。

## 📚 文件結構

```
frontend-vue/
├── src/
│   ├── App.vue              # 主應用元件（全部功能）
│   ├── main.js              # Vue 應用入口
│   └── assets/              # 靜態資源
├── index.html               # HTML 模板
├── vite.config.js           # Vite 配置
├── package.json             # 依賴配置
└── README.md                # Vue 版本說明
```

## 🐛 故障排除

### 連接後端失敗
```
✗ 問題：無法連接到 http://localhost:8000
✓ 解決：確保後端已啟動，檢查防火牆設定
```

### 樣式不顯示
```
✗ 問題：頁面沒有樣式
✓ 解決：確保 PrimeVue CSS 已加載（main.js 中）
```

### 文件上傳失敗
```
✗ 問題：上傳文件時出錯
✓ 解決：確保文件格式為 PDF/TXT/MD，檢查 backend/uploads 目錄
```

### 問答無結果
```
✗ 問題：提問後沒有回答
✓ 解決：確認已上傳文件，檢查當前角色權限
```

## 🚀 生產部署

### 構建
```bash
cd frontend-vue
npm run build
```

### 部署
```bash
# 將 dist/ 目錄部署到 Web 伺服器
# 例如：Nginx、Apache、或 CDN
```

## 📞 需要幫助？

- 📖 查閱 `README.md` 獲取完整技術文檔
- ⚡ 查閱 `QUICK_START.md` 快速上手
- 🔗 訪問 `http://localhost:8000/docs` 查看 Swagger API 文檔

## ✨ 額外功能

### 已實現
- ✅ 響應式設計（適配各種螢幕）
- ✅ 實時通知反饋
- ✅ 加載狀態指示
- ✅ 錯誤處理
- ✅ 角色切換

### 可擴展
- 添加更多表單模板
- 自訂 PrimeVue 主題
- 添加高級搜索功能
- 集成更多 LLM 服務

---

**版本**: 1.0.0 Vue Edition  
**日期**: 2026-02-05  
**狀態**: ✅ 完成並可立即使用
