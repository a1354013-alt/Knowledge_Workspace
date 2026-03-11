# 5 分鐘快速開始

## 前置要求
- Python 3.8+
- Node.js 14+
- npm 或 pnpm

## 步驟 1：解壓縮（1 分鐘）

```bash
tar -xzf enterprise-ai-assistant-v3.2-fixed.tar.gz
cd enterprise-ai-assistant
```

## 步驟 2：啟動後端（2 分鐘）

打開**終端 1**：

```bash
cd backend
pip install -r requirements.txt
python main.py
```

等待看到：
```
✅ 企業 AI 助理 API 啟動
Uvicorn running on http://0.0.0.0:8000
```

## 步驟 3：啟動前端（2 分鐘）

打開**終端 2**：

```bash
cd frontend-vue
npm install
npm run dev
```

等待看到：
```
Local:   http://localhost:3000/
```

## 步驟 4：登入（1 分鐘）

1. 打開瀏覽器，訪問 **http://localhost:3000**
2. 輸入登入資訊：
   - **使用者 ID**: `admin`
   - **密碼**: `admin12345`
3. 點擊「登入」

## 步驟 5：測試功能

### 5.1 進入 Admin 後台
- 點擊「Admin 後台」按鈕
- 進入 Users 和 Documents 管理界面

### 5.2 上傳文件
1. 在左欄「文件管理」選擇檔案
2. 選擇允許查看的角色
3. 點擊「上傳文件」
4. 進入 Admin 後台，在 Documents Tab 批准文件

### 5.3 提問
1. 在中欄「智能問答」輸入問題
2. 點擊「提交問題」
3. 查看回答和引用來源

### 5.4 生成表單
1. 在右欄「表單生成」選擇模板
2. 填寫所有欄位
3. 點擊「生成內容」
4. 複製到剪貼簿

## 常用命令

### 後端
```bash
cd backend

# 安裝依賴
pip install -r requirements.txt

# 啟動應用
python main.py

# 查看 API 文檔
# 訪問 http://localhost:8000/docs
```

### 前端
```bash
cd frontend-vue

# 安裝依賴
npm install

# 開發模式
npm run dev

# 生產構建
npm run build

# 預覽構建
npm run preview
```

## 環境變數配置

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

# Admin 預設密碼（可選，預設值: admin12345）
# 機密建議：設定一個較強的密碼
DEFAULT_ADMIN_PASSWORD=your-strong-password-here
```

### 前端 (.env)
```env
# API 基礎 URL
VITE_API_BASE=http://localhost:8000
```

## 預設帳號

| 帳號 | 密碼 | 角色 |
|------|------|------|
| admin | admin12345 | admin |

⚠️ **重要**：生產環境必須修改預設密碼！

## 故障排除

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
→ 確認帳號密碼正確（admin / admin12345）

### 提問返回「找不到依據」
→ 確認文件已被 admin 批准

### 無法進入 Admin 後台
→ 只有 admin 角色才能進入

## 下一步

1. 📖 查閱 **README.md** 了解完整功能
2. 🔧 配置 **OpenAI API Key** 以使用 GPT-4
3. 🔐 修改預設密碼和 JWT_SECRET
4. 📤 上傳您自己的企業文件
5. 🚀 部署到生產環境

## 技術棧

- **後端**: FastAPI + ChromaDB + SQLite + PyJWT
- **前端**: Vue 3 + PrimeVue + Vite + Axios
- **認證**: JWT Token + bcrypt 密碼加密
- **文件**: PDF / TXT / MD 支援

## 更多資訊

- 📖 後端文檔：`backend/README.md`
- 📖 前端文檔：`frontend-vue/README.md`
- 🔗 API 文檔：http://localhost:8000/docs (Swagger UI)
- 📊 架構說明：`PROJECT_STRUCTURE.md`

---

**版本**: 3.2.0 Final  
**最後更新**: 2026-03-02
