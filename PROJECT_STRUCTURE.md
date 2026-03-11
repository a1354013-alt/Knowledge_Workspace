# 📁 專案結構說明

## 完整目錄樹

```
enterprise-ai-assistant/
│
├── README.md                    # 完整文檔（技術棧、API、部署等）
├── QUICK_START.md              # 快速開始指南（5分鐘上手）
├── PROJECT_STRUCTURE.md        # 本檔案
│
├── start_backend.sh            # 後端啟動腳本
├── start_frontend.sh           # 前端啟動腳本
│
├── backend/                    # 🔧 FastAPI 後端
│   ├── main.py                # 主應用程式
│   │   ├── FastAPI 應用初始化
│   │   ├── CORS 中間件配置
│   │   ├── 文件上傳 API (/api/docs/upload)
│   │   ├── 文件列表 API (/api/docs)
│   │   ├── 文件刪除 API (/api/docs/{doc_id})
│   │   ├── 問答 API (/api/qa)
│   │   └── 表單生成 API (/api/generate)
│   │
│   ├── models.py               # Pydantic 資料模型
│   │   ├── DocumentResponse
│   │   ├── QARequest / QAResponse
│   │   ├── Source
│   │   ├── GenerateRequest / GenerateResponse
│   │   └── 所有 API 請求/回應的型別定義
│   │
│   ├── database.py             # ChromaDB 操作層
│   │   ├── get_collection()     # 取得或建立集合
│   │   ├── add_to_vector_db()   # 新增向量
│   │   ├── query_vector_db()    # 查詢相似文本
│   │   └── delete_from_vector_db() # 刪除向量
│   │
│   ├── services.py             # 業務邏輯層
│   │   ├── get_llm()            # 初始化 LLM (OpenAI 或 Mock)
│   │   ├── process_file()       # 文件處理與索引
│   │   │   ├── 支援 PDF/TXT/MD
│   │   │   ├── 文本分割 (500 tokens, 100 overlap)
│   │   │   └── 元數據保存
│   │   ├── perform_qa()         # RAG 問答
│   │   │   ├── 向量檢索
│   │   │   ├── 權限過濾
│   │   │   ├── LLM 生成回答
│   │   │   └── 返回引用來源
│   │   └── generate_form()      # 表單生成
│   │       ├── 模板選擇
│   │       ├── LLM 生成
│   │       └── Demo Mode 支援
│   │
│   ├── requirements.txt         # Python 依賴
│   │   ├── fastapi, uvicorn
│   │   ├── chromadb
│   │   ├── langchain, langchain-openai, langchain-community
│   │   ├── pypdf, python-dotenv
│   │   └── 其他工具庫
│   │
│   ├── .env                    # 環境變數 (可選)
│   │   └── OPENAI_API_KEY=sk-... (可選)
│   │
│   ├── sample_docs/            # 📚 範例文件
│   │   ├── leave_policy.txt    # 請假規定
│   │   ├── overtime_policy.txt # 加班規定
│   │   └── meeting_template.txt # 會議紀錄模板
│   │
│   ├── uploads/                # 📤 上傳文件目錄 (自動建立)
│   │
│   └── chroma_db/              # 🗄️ ChromaDB 本機存儲 (自動建立)
│
└── frontend/                   # 🎨 React 前端
    ├── client/
    │   ├── src/
    │   │   ├── pages/
    │   │   │   ├── Home.tsx     # 🏠 主頁面 (核心功能)
    │   │   │   │   ├── 左欄：文件管理
    │   │   │   │   ├── 中欄：智能問答
    │   │   │   │   └── 右欄：表單生成
    │   │   │   ├── NotFound.tsx
    │   │   │   └── ...
    │   │   │
    │   │   ├── components/      # UI 元件 (shadcn/ui)
    │   │   │   ├── ui/
    │   │   │   │   ├── button.tsx
    │   │   │   │   ├── card.tsx
    │   │   │   │   ├── input.tsx
    │   │   │   │   ├── textarea.tsx
    │   │   │   │   ├── select.tsx
    │   │   │   │   ├── tabs.tsx
    │   │   │   │   └── ...
    │   │   │   └── ErrorBoundary.tsx
    │   │   │
    │   │   ├── contexts/        # React Context
    │   │   │   └── ThemeContext.tsx
    │   │   │
    │   │   ├── App.tsx          # 路由配置
    │   │   ├── main.tsx         # React 入口
    │   │   └── index.css        # 全局樣式 (Tailwind)
    │   │
    │   ├── index.html           # HTML 模板
    │   └── public/              # 靜態資源
    │
    ├── package.json             # Node 依賴
    ├── vite.config.ts           # Vite 配置
    ├── tsconfig.json            # TypeScript 配置
    └── ...
```

## 🔄 數據流

### 1. 文件上傳流程
```
前端 (Home.tsx)
  ↓
  POST /api/docs/upload (FormData)
  ↓
後端 (main.py)
  ↓
  services.process_file()
  ↓
  ├─ 文件解析 (PyPDF/TextLoader)
  ├─ 文本分割 (RecursiveCharacterTextSplitter)
  ├─ 向量化 (ChromaDB)
  └─ 元數據保存
  ↓
  返回 { id, filename, allowed_roles }
  ↓
前端顯示成功提示
```

### 2. 問答流程
```
前端 (Home.tsx)
  ↓
  POST /api/qa { question, user_role }
  ↓
後端 (services.perform_qa)
  ↓
  ├─ 向量檢索 (query_vector_db)
  ├─ 權限過濾 (user_role 檢查)
  ├─ LLM 生成回答 (ChatOpenAI or Mock)
  └─ 收集引用來源
  ↓
  返回 { answer, sources[] }
  ↓
前端顯示回答和引用卡片
```

### 3. 表單生成流程
```
前端 (Home.tsx)
  ↓
  POST /api/generate { template_type, inputs, user_role }
  ↓
後端 (services.generate_form)
  ↓
  ├─ 選擇模板
  ├─ 構建 Prompt
  ├─ LLM 生成 (ChatOpenAI or Mock)
  └─ 返回內容
  ↓
  返回 { content }
  ↓
前端顯示生成結果，支援複製
```

## 📊 核心模型

### Document (文件)
```python
{
  "id": "uuid",
  "filename": "leave_policy.txt",
  "allowed_roles": ["employee", "manager"]
}
```

### QA Request/Response
```python
Request:
{
  "question": "請假規定是什麼？",
  "user_role": "employee"
}

Response:
{
  "answer": "根據企業規定...",
  "sources": [
    {
      "doc_name": "leave_policy.txt",
      "chunk_text": "年假：新員工第一年 10 天...",
      "page_or_section": "0"
    }
  ]
}
```

### Generate Request/Response
```python
Request:
{
  "template_type": "請假通知",
  "inputs": {
    "請假類型": "年假",
    "請假日期": "2026-02-10",
    "請假天數": "3",
    "原因": "個人休息"
  },
  "user_role": "employee"
}

Response:
{
  "content": "親愛的團隊，\n關於請假通知...\n此致，\nemployee 助理代筆"
}
```

## 🔐 權限模型

### 角色定義
- `employee`: 員工 (預設權限)
- `manager`: 主管 (員工 + 主管級別)
- `hr`: 人資 (全部權限)

### 權限過濾
```python
# 上傳時設定
allowed_roles = ["employee", "manager"]

# 檢索時過濾
if user_role in allowed_roles:
    # 返回該文件
```

## 🛠️ 技術棧細節

### 後端
| 組件 | 用途 |
|------|------|
| FastAPI | Web 框架 |
| Uvicorn | ASGI 伺服器 |
| Pydantic | 資料驗證 |
| ChromaDB | 向量庫 |
| LangChain | 文本分割、LLM 整合 |
| PyPDF | PDF 解析 |
| OpenAI API | LLM (可選) |

### 前端
| 組件 | 用途 |
|------|------|
| React 19 | UI 框架 |
| Tailwind 4 | CSS 框架 |
| shadcn/ui | UI 元件庫 |
| Axios | HTTP 客戶端 |
| Sonner | Toast 通知 |
| Lucide | 圖標 |

## 📈 擴展點

### 1. 添加新的表單模板
編輯 `backend/services.py`:
```python
templates = {
    "新模板": "提示詞...",
}
```

### 2. 支援更多文件格式
編輯 `backend/services.py`:
```python
elif ext == ".docx":
    loader = DocxLoader(file_path)
```

### 3. 自訂 LLM
編輯 `backend/services.py`:
```python
def get_llm():
    return ChatAnthropic(model="claude-3-sonnet")
```

### 4. 添加資料庫持久化
添加 SQLAlchemy 模型和遷移

### 5. 添加使用者認證
集成 OAuth 或 JWT

## 🚀 部署清單

- [ ] 後端: 使用 Gunicorn 或 Docker
- [ ] 前端: 構建並部署到 CDN
- [ ] 資料庫: 遷移到生產 ChromaDB 或 Pinecone
- [ ] LLM: 配置生產 API Key
- [ ] 日誌: 設定日誌系統
- [ ] 監控: 添加 APM 工具
- [ ] 安全: HTTPS、CORS、速率限制

---

**版本**: 1.0.0 MVP  
**最後更新**: 2026-02-05
