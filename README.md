# 企業 AI 助理 - 完整版本

完整的企業內部 AI 助理系統，包含文件管理、RAG 問答、表單生成、用戶認證、Admin 後台等功能。

**版本**: 3.0.0 Admin Console  
**更新**: 2026-02-08

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

### 🤖 RAG 問答系統
- ✅ **向量檢索** - 基於 ChromaDB 的語義搜尋
- ✅ **權限過濾** - 查詢時在 database 層進行權限檢查
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

## 📦 專案結構

```
enterprise-ai-assistant/
├── backend/                     # FastAPI 後端
│   ├── main.py                 # 應用主程式（含 Admin API）
│   ├── models.py               # Pydantic 模型
│   ├── database.py             # SQLite + ChromaDB 操作層
│   ├── services.py             # 業務邏輯（RAG、表單生成）
│   ├── auth.py                 # JWT 驗證模組
│   ├── utils.py                # 工具函數
│   ├── requirements.txt         # Python 依賴
│   ├── .env.example            # 環境變數範例
│   ├── documents.db            # SQLite 資料庫（自動生成）
│   ├── chroma_db/              # ChromaDB 向量庫（自動生成）
│   ├── uploads/                # 上傳檔案存儲目錄
│   ├── sample_docs/            # 範例文件
│   └── README.md               # 後端文檔
│
├── frontend-vue/                # Vue 3 + PrimeVue 前端
│   ├── src/
│   │   ├── App.vue             # 主應用元件（含登入、Admin 入口）
│   │   ├── main.js             # Vue 入口
│   │   ├── components/
│   │   │   └── AdminConsole.vue # Admin 後台元件
│   │   ├── views/              # 頁面目錄
│   │   └── assets/             # 靜態資源
│   ├── index.html              # HTML 模板
│   ├── vite.config.js          # Vite 配置
│   ├── package.json            # 依賴配置
│   ├── .env.example            # 環境變數範例
│   └── README.md               # 前端文檔
│
├── README.md                    # 本檔案
├── QUICK_START.md              # 快速開始指南
└── PROJECT_STRUCTURE.md        # 專案架構說明
```

## 🚀 快速開始

### 1️⃣ 解壓縮
```bash
tar -xzf enterprise-ai-assistant-admin-fixed.tar.gz
cd enterprise-ai-assistant
```

### 2️⃣ 啟動後端（終端 1）
```bash
cd backend
pip install -r requirements.txt
python main.py
```

✅ 看到以下輸出表示成功：
```
✅ 企業 AI 助理 API 啟動
📝 允許的來源: ['http://localhost:3000']
🔐 Allow Credentials: True
🔑 OpenAI API Key: 未配置（使用 sentence-transformers）
Uvicorn running on http://0.0.0.0:8000
```

### 3️⃣ 啟動前端（終端 2）
```bash
cd frontend-vue
npm install
npm run dev
```

✅ 看到以下輸出表示成功：
```
Local:   http://localhost:3000/
Network: http://169.254.0.21:3000/
```

### 4️⃣ 打開瀏覽器
訪問 **http://localhost:3000**

### 5️⃣ 登入
```
帳號：admin
密碼：admin12345
```

⚠️ **重要**：生產環境必須修改預設密碼！

## 📖 使用指南

### 普通使用者流程
1. 登入（輸入 user_id + password）
2. 上傳文件（預設待審核）
3. 等待 admin 批准
4. 提問（只能查詢已批准的文件）
5. 生成表單

### Admin 流程
1. 登入（admin 帳號）
2. 點擊「Admin 後台」進入管理界面
3. **Users Tab**：
   - 新增使用者
   - 編輯使用者角色
   - 停用/啟用使用者
4. **Documents Tab**：
   - 查看所有上傳的文件
   - 批准/撤審文件
   - 上架/下架文件
   - 刪除文件

## 🔐 安全特性

### 認證與授權
- ✅ 密碼使用 bcrypt 加密
- ✅ JWT Token 簽署，無法偽造
- ✅ 每個 API 都驗證 Authorization header
- ✅ 角色白名單驗證

### 文件安全
- ✅ 檔名使用 UUID，防止路徑穿越
- ✅ 副檔名白名單（.pdf .txt .md）
- ✅ 檔案大小限制（50MB）
- ✅ 刪除時同時清理向量庫、資料庫、檔案

### 數據安全
- ✅ SQLite 持久化存儲
- ✅ ChromaDB 向量庫快取
- ✅ CORS 環境變數控制
- ✅ 權限過濾在查詢階段進行

## 🔧 環境變數配置

### 後端 (.env)
```env
# OpenAI API Key（可選）
OPENAI_API_KEY=sk-...

# JWT 密鑰（必填）
JWT_SECRET=your-secret-key-here

# CORS 允許的來源
ALLOWED_ORIGINS=http://localhost:3000

# 資料庫路徑
DATABASE_PATH=documents.db

# 上傳目錄
UPLOAD_DIR=./uploads
```

### 前端 (.env)
```env
# API 基礎 URL
VITE_API_BASE=http://localhost:8000
```

## 📊 API 文檔

### 認證端點
- `POST /api/login` - 登入
- `GET /api/me` - 取得當前使用者資訊

### 文件管理
- `POST /api/docs/upload` - 上傳文件
- `GET /api/docs` - 列出文件
- `DELETE /api/docs/{doc_id}` - 刪除文件

### 問答
- `POST /api/qa` - 提交問題

### 表單生成
- `POST /api/generate` - 生成表單

### Admin API
- `GET /api/admin/users` - 列出使用者
- `POST /api/admin/users` - 新增使用者
- `PATCH /api/admin/users/{user_id}` - 編輯使用者
- `GET /api/admin/docs` - 列出所有文件
- `PATCH /api/admin/docs/{doc_id}` - 編輯文件
- `DELETE /api/admin/docs/{doc_id}` - 刪除文件

詳見 **http://localhost:8000/docs** (Swagger UI)

## 🐛 常見問題

### Q: 上傳文件後無法查詢
**A**: 文件需要 admin 批准才能被 QA 檢索。進入 Admin 後台，在 Documents Tab 批准文件。

### Q: 登入失敗
**A**: 確認帳號密碼正確。預設帳號是 `admin`，密碼是 `admin12345`。

### Q: 提問返回「找不到依據」
**A**: 可能是：
1. 文件未被批准（進入 Admin 後台批准）
2. 文件已下架（進入 Admin 後台上架）
3. 您的角色無權查看該文件（檢查文件的 allowed_roles）

### Q: 無法進入 Admin 後台
**A**: 只有 role=admin 的使用者才能進入。檢查您的角色設定。

## 📝 生產環境部署清單

- [ ] 修改 `JWT_SECRET` 為強密鑰
- [ ] 修改預設 admin 密碼
- [ ] 配置 `ALLOWED_ORIGINS` 為實際域名
- [ ] 設定 `OPENAI_API_KEY`（可選）
- [ ] 啟用 HTTPS
- [ ] 配置資料庫備份
- [ ] 添加審計日誌
- [ ] 設定監控告警
- [ ] 對接企業認證系統（LDAP/AD）

## 📞 技術支援

- 📖 查閱 **backend/README.md** 獲取後端詳細文檔
- 📖 查閱 **frontend-vue/README.md** 獲取前端詳細文檔
- 🔗 訪問 **http://localhost:8000/docs** 查看 Swagger API 文檔

## 📄 授權

MIT License

---

**版本**: 3.0.0 Admin Console  
**最後更新**: 2026-02-08  
**狀態**: ✅ 完全可部署
