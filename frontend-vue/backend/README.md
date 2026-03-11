# 企業 AI 助理 - 後端 API

FastAPI 後端應用，提供文件管理、RAG 問答、表單生成等功能。

## 🔒 安全性強化

### 檔案上傳安全
- ✅ **UUID 檔名** - 使用 UUID + 原副檔名，防止路徑穿越
- ✅ **副檔名驗證** - 僅允許 `.pdf`, `.txt`, `.md`
- ✅ **檔案大小限制** - 最大 50MB
- ✅ **路徑清理** - 移除 `../` 等危險字符

### 持久化存儲
- ✅ **SQLite 資料庫** - 文件元資料持久化存儲
- ✅ **完整刪除** - 刪除時同時清理向量庫、資料庫、實體檔案
- ✅ **角色權限** - 文件級別的權限控制

### 非同步性能
- ✅ **執行緒池** - LLM 呼叫使用執行緒池，不阻塞主線程
- ✅ **非同步支援** - 優先使用 `ainvoke`，否則用執行緒池

### CORS 配置
- ✅ **環境變數控制** - `ALLOWED_ORIGINS` 環境變數
- ✅ **生產安全** - 預設不允許 `*`，需明確指定來源

## 📁 專案結構

```
backend/
├── main.py              # FastAPI 應用主程式
├── models.py            # Pydantic 資料模型
├── database.py          # SQLite + ChromaDB 操作層
├── services.py          # 業務邏輯層
├── utils.py             # 工具函數
├── requirements.txt     # Python 依賴
├── .env.example         # 環境變數範例
├── .env                 # 環境變數配置（本地）
├── documents.db         # SQLite 資料庫（自動生成）
├── chroma_db/           # ChromaDB 向量庫（自動生成）
├── uploads/             # 上傳的檔案存儲目錄
└── sample_docs/         # 範例文件
    ├── leave_policy.txt
    ├── overtime_policy.txt
    └── meeting_template.txt
```

## 🚀 快速啟動

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 配置環境變數
複製 `.env.example` 為 `.env`：
```bash
cp .env.example .env
```

編輯 `.env` 檔案（可選）：
```env
# OpenAI API Key (可選，無則使用 Demo Mode)
OPENAI_API_KEY=sk-...

# CORS 允許的來源
ALLOWED_ORIGINS=http://localhost:3000

# 資料庫路徑
DATABASE_PATH=documents.db
```

### 3. 啟動應用
```bash
python main.py
```

✅ 看到 `Uvicorn running on http://0.0.0.0:8000` 表示啟動成功

## 📚 API 文檔

### 文件管理

#### 上傳文件
```http
POST /api/docs/upload
Content-Type: multipart/form-data

file: <binary>
allowed_roles: employee,manager
```

**回應:**
```json
{
  "id": "uuid",
  "filename": "原始檔名.pdf",
  "saved_filename": "uuid.pdf",
  "file_size": 12345,
  "message": "文件上傳成功"
}
```

#### 列出文件
```http
GET /api/docs
```

**回應:**
```json
[
  {
    "id": "uuid",
    "filename": "leave_policy.txt",
    "saved_filename": "uuid.txt",
    "allowed_roles": ["employee", "manager"],
    "uploaded_at": "2026-02-05T10:30:00",
    "file_size": 5000
  }
]
```

#### 刪除文件
```http
DELETE /api/docs/{doc_id}
```

**回應:**
```json
{
  "message": "文件已刪除"
}
```

### 問答

#### 提交問題
```http
POST /api/qa
Content-Type: application/json

{
  "question": "請假規定是什麼？",
  "user_role": "employee"
}
```

**回應:**
```json
{
  "answer": "根據規定...",
  "sources": [
    {
      "doc_name": "leave_policy.txt",
      "chunk_text": "請假規定：...",
      "page_or_section": "0"
    }
  ]
}
```

### 表單生成

#### 生成表單內容
```http
POST /api/generate
Content-Type: application/json

{
  "template_type": "請假通知",
  "inputs": {
    "請假類型": "年假",
    "請假日期": "2026-02-10",
    "請假天數": "1",
    "原因": "個人事務"
  },
  "user_role": "employee"
}
```

**回應:**
```json
{
  "content": "親愛的團隊，\n\n我需要請假..."
}
```

### 健康檢查

```http
GET /health
```

**回應:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## 🔌 Swagger API 文檔

訪問 `http://localhost:8000/docs` 查看互動式 API 文檔。

## 🛠️ 技術棧

| 組件 | 版本 | 說明 |
|------|------|------|
| FastAPI | 0.104+ | REST API 框架 |
| Uvicorn | 0.24+ | ASGI 伺服器 |
| ChromaDB | 0.4+ | 向量資料庫 |
| LangChain | 0.1+ | 文本分割 & LLM 整合 |
| PyPDF | 3.17+ | PDF 解析 |
| SQLite | 3.x | 關聯式資料庫 |
| Pydantic | 2.0+ | 資料驗證 |

## 🔐 環境變數說明

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OPENAI_API_KEY` | 無 | OpenAI API Key（可選） |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS 允許的來源 |
| `DATABASE_PATH` | `documents.db` | SQLite 資料庫路徑 |
| `UPLOAD_DIR` | `./uploads` | 上傳檔案存儲目錄 |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB 資料庫路徑 |

## 📝 Demo Mode

如果未設定 `OPENAI_API_KEY`，應用會自動進入 Demo Mode：
- 問答會返回模擬回答
- 表單生成會返回預設模板
- 所有功能正常運作，便於測試

## 🚨 故障排除

### 1. "找不到依據"
**原因**: 未上傳相關文件或文件未被正確索引  
**解決**: 上傳 `sample_docs/` 中的範例文件

### 2. "檔案過大"
**原因**: 上傳的檔案超過 50MB  
**解決**: 使用較小的檔案或分割大檔案

### 3. "不允許的副檔名"
**原因**: 上傳了非 PDF/TXT/MD 檔案  
**解決**: 僅上傳 `.pdf`, `.txt`, `.md` 檔案

### 4. CORS 錯誤
**原因**: 前端來源未在 `ALLOWED_ORIGINS` 中  
**解決**: 編輯 `.env` 添加前端 URL

## 📊 資料庫架構

### documents 表
```sql
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    saved_filename TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    file_size INTEGER DEFAULT 0
);
```

## 🔄 工作流程

1. **上傳** → 文件保存 + SQLite 記錄 + ChromaDB 向量化
2. **查詢** → ChromaDB 檢索 + 權限過濾 + LLM 生成回答
3. **刪除** → 刪除向量 + 刪除記錄 + 刪除檔案

## 📞 支援

- 🐛 發現 Bug？檢查 `/health` 端點確認服務狀態
- 📖 查看 API 文檔：`http://localhost:8000/docs`
- 💡 需要幫助？查閱本文檔或查看範例文件

---

**版本**: 1.0.0 MVP  
**最後更新**: 2026-02-05
