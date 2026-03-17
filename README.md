# 企業 AI 助理 - 完整版本

完整的企業內部 AI 助理系統，包含文件管理、RAG 問答、表單生成、用戶認證、Admin 後台等功能。

**版本**: 3.9.0 Final  
**更新**: 2026-03-13

## 🎯 核心功能

### 🔐 用戶認證與授權
- ✅ **密碼驗證** - 使用 bcrypt 加密，防止密碼洩露
- ✅ **JWT Token** - 後端簽署，前端無法偽造角色
- ✅ **角色管理** - employee / manager / hr / admin 四層角色
- ✅ **Admin 後台** - 僅 admin 可進入，管理使用者和文件

### 📄 文件管理與審核
- ✅ **上傳流程** - 上傳時預設 approved=0（未審核）
- ✅ **文件審核** - Admin 可批准/下架文件
- ✅ **權限控制** - 只有 approved=1 & is_active=1 的文件才能被 QA 檢索
- ✅ **刪除權限** - 上傳者或 admin 才能刪除

### 🐋 RAG 問答系統
- ✅ **向量搜尋** - 基於 ChromaDB 的語義搜尋
- ✅ **權限過濾** - 查詢時在 database 層進行權限檢查
  - **權限詳述**: 非 admin 角色只能查詢文件的 allowed_roles 包含了他們的文件（例如 HR 只能查詢 allowed_roles 包含「hr」的文件）。admin 可以查詢所有已批準的文件。
- ✅ **引用來源** - 每個回答都顯示出處
- ✅ **Demo Mode** - 無需 OpenAI Key 也能運行

### 📋 表單生成
- ✅ **多種模板** - 請假通知、加班申請、變更申請、會議紀錄
- ✅ **動態欄位** - 根據模板自動生成欄位
- ✅ **內容複製** - 一鍵複製生成的內容

## 🛠️ 技術棧

### 後端
| 組件 | 版本 | 說明 |
|------|------|------|
| FastAPI | 0.104+ | REST API 框架 |
| ChromaDB | 0.4+ | 向量資料庫 |
| LangChain | 0.1+ | 文本分割 & LLM |
| SQLite | 3.x | 關聯式資料庫 |
| PyJWT | 2.8+ | JWT 簽署 |
| bcrypt | 4.0+ | 密碼加密 |

### 前端
| 組件 | 版本 | 說明 |
|------|------|------|
| Vue | 3.4.0 | JavaScript 框架 |
| PrimeVue | 4.0.0 | UI 組件庫 |
| Vite | 5.0.0 | 構建工具 |
| Axios | 1.6.0 | HTTP 客戶端 |

## 🚀 快速開始

### 1️⃣ 解壓縮
```bash
tar -xzf enterprise-ai-assistant-v3.9-final.tar.gz
cd enterprise-ai-assistant
```

### 2️⃣ 啟動後端（終端 1）

【推薦】使用啟動腳本（含依賴快取）：
```bash
./start_backend.sh
```

✅ 看到以下輸出表示成功：
```
✅ 企業 AI 助理 API 啟動
📝 允許的來源: ['http://localhost:3000']
🔐 Allow Credentials: True
🔑 OpenAI API Key: 未配置（使用 sentence-transformers）
Uvicorn running on http://0.0.0.0:8000
```

【下一步】如果需要手動啟動：
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3️⃣ 啟動前端（終端 2）

【推薦】使用啟動腳本（含依賴快取）：
```bash
./start_frontend.sh
```

✅ 看到以下輸出表示成功：
```
Local:   http://localhost:3000/
Network: http://169.254.0.21:3000/
```

【下一步】如果需要手動啟動：
```bash
cd frontend-vue
npm install
npm run dev
```

### 4️⃣ 打開瀏覽器
訪問 **http://localhost:3000**

### 5️⃣ 登入

- **帳號**: `admin`
- **密碼**: 開發環境若未設定 `DEFAULT_ADMIN_PASSWORD`，系統會使用 fallback 密碼

⚠️ **重要**：正式環境必須自行設定強密碼！在 `.env` 中設定 `DEFAULT_ADMIN_PASSWORD`

## 📖 使用指南

### 普通使用者流程
1. 登入（輸入 user_id + password）
2. 上傳文件（預設待審核）
3. 等待 admin 批准
4. 提問（只能查詢已批准的文件）
5. 生成表單

### Admin 流程
1. 登入（admin 帳號）
2. 進入 Admin 後台
3. 在 Users Tab 管理使用者
4. 在 Documents Tab 審核文件
5. 批准後，一般使用者才能查詢

## 🔧 環境變數配置

### 後端 (.env)
```env
# OpenAI API Key（可選）
OPENAI_API_KEY=sk-...

# JWT 密鑰（必填，生成強密鑰）
JWT_SECRET=your-secret-key-here

# CORS 允許的來源
ALLOWED_ORIGINS=http://localhost:3000

# 資料庫路徑
DATABASE_PATH=documents.db

# 上傳目錄
UPLOAD_DIR=./uploads

# ChromaDB 路徑（持久化向量庫）
CHROMA_DB_PATH=./chroma_db

# Admin 預設密碼（可選）
# 開發環境若未設定，系統會使用 fallback 密碼
# 正式環境必須設定強密碼
DEFAULT_ADMIN_PASSWORD=your-strong-password-here
```

### 前端 (.env)
```env
# API 基礎 URL
VITE_API_BASE=http://localhost:8000
```

## 📁 專案結構

```
enterprise-ai-assistant/
├── backend/
│   ├── main.py                 # FastAPI 主應用
│   ├── database.py             # SQLite + ChromaDB 管理
│   ├── services.py             # 業務邏輯（文件處理、RAG、表單生成）
│   ├── models.py               # Pydantic 模型
│   ├── requirements.txt         # Python 依賴
│   └── .env.example            # 環境變數範例
│
├── frontend-vue/
│   ├── src/
│   │   ├── App.vue             # 主應用元件
│   │   ├── main.js             # Vue 入口
│   │   ├── components/         # UI 元件
│   │   │   └── AdminConsole.vue
│   │   └── index.css           # 全局樣式
│   ├── index.html              # HTML 模板
│   ├── vite.config.js          # Vite 配置
│   ├── package.json            # 依賴配置
│   └── .env.example            # 環境變數範例
│
├── start_backend.sh            # 後端啟動腳本（推薦）
├── start_frontend.sh           # 前端啟動腳本（推薦）
├── README.md                    # 本檔案
└── QUICK_START.md              # 快速開始指南
```

## 📊 API 文檔

啟動後端後，訪問 **http://localhost:8000/docs** 查看完整 API 文檔（Swagger UI）

### 主要端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | /api/login | 登入 |
| GET | /api/docs | 列出文件（權限過濾） |
| POST | /api/docs/upload | 上傳文件 |
| POST | /api/qa | 提問 |
| POST | /api/generate | 生成表單 |
| GET | /api/admin/users | 列出使用者（僅 admin） |
| GET | /api/admin/docs | 列出所有文件（僅 admin） |
| PATCH | /api/admin/docs/{doc_id} | 更新文件（僅 admin） |

## 🔐 安全特性

- ✅ **密碼加密** - bcrypt 加鹽雜湊
- ✅ **JWT 簽署** - 後端簽署，無法偽造
- ✅ **角色驗證** - 每個 API 都檢查使用者角色
- ✅ **權限過濾** - 文件查詢時過濾不可見文件
- ✅ **CORS 保護** - 限制跨域請求來源

## 🐛 故障排除

### 後端無法啟動
```
ModuleNotFoundError: No module named 'fastapi'
```
→ 執行 `pip install -r requirements.txt`

### 前端無法啟動
```
npm ERR! code ERESOLVE
```
→ 執行 `npm install --legacy-peer-deps`

### 登入失敗
→ 確認帳號密碼正確（admin / 由 DEFAULT_ADMIN_PASSWORD 決定）

### 提問返回「找不到依據」
→ 確認文件已被 admin 批准

### 無法進入 Admin 後台
→ 只有 admin 角色才能進入

## 📚 下一步

1. 📖 查閱 **QUICK_START.md** 了解詳細步驟
2. 🔧 配置 **OpenAI API Key** 以使用 GPT-4
3. 🔐 修改預設密碼和 JWT_SECRET
4. 📤 上傳您自己的企業文件
5. 🚀 部署到生產環境

## 📝 更多資訊

- 🔗 API 文檔：http://localhost:8000/docs (Swagger UI)
- 🚀 快速開始：`QUICK_START.md`

## 📄 授權

MIT License

---

**版本**: 3.9.0 Final  
**最後更新**: 2026-03-13  
**狀態**: ✅ 企業級生產環境就緒
