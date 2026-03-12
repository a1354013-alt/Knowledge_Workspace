import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Header, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 【新增】設置 logging（提升維運可觀渫性）
logger = logging.getLogger("enterprise-ai-assistant")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 載入 .env 檔案（必須在最前面）
load_dotenv()

from models import QARequest, QAResponse, GenerateRequest, GenerateResponse
from database import DocumentDatabase, delete_from_vector_db
from services import process_file, perform_qa, generate_form
from auth import create_token, verify_token, extract_token_from_header
from utils import (
    generate_safe_filename,
    validate_file_extension,
    parse_user_roles,
    parse_doc_roles,
    stream_write_file,
    MAX_FILE_SIZE
)

# ============ 配置 ============

# 上傳目錄（從環境變數讀取）
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 資料庫（從環境變數讀取）
db = DocumentDatabase(os.getenv("DATABASE_PATH", "documents.db"))

# CORS 配置（修復：避免 * 與 credentials 衝突）
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").strip()

if ALLOWED_ORIGINS_STR == "*":
    ALLOWED_ORIGINS = ["*"]
    ALLOW_CREDENTIALS = False
else:
    # 【改進】修正 CORS ORIGINS 解析：避免空字串
    # 目的：保證每個 origin 都是有效的，不會有空字串
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in ALLOWED_ORIGINS_STR.split(",")
        if origin.strip()
    ]
    ALLOW_CREDENTIALS = True

# ============ 應用生命週期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    print("✅ 企業 AI 助理 API 啟動")
    print(f"📝 允許的來源: {ALLOWED_ORIGINS}")
    print(f"🔐 Allow Credentials: {ALLOW_CREDENTIALS}")
    print(f"🔑 OpenAI API Key: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置（使用 sentence-transformers）'}")
    print(f"🔐 JWT 驗證: 已啟用")
    print(f"👤 Admin 管理: 已啟用")
    yield
    print("✅ 應用關閉")

app = FastAPI(
    title="企業 AI 助理 API",
    description="文件管理、RAG 問答、表單生成、Admin 管理（JWT 驗證版本）",
    version="3.3.0",
    lifespan=lifespan
)

# 添加 CORS 中間件（修復：正確處理 credentials）
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 輔助函數 ============

def require_admin(token_data: dict) -> None:
    """檢查是否為 admin 角色"""
    if token_data.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作需要 admin 權限"
        )

# ============ 認證 API ============

@app.post("/api/login")
async def login(user_id: str = Form(...), password: str = Form(...)):
    """
    使用者登入
    
    request: user_id + password
    response: token
    """
    try:
        # 驗證使用者
        if not db.verify_password(user_id, password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="使用者名稱或密碼錯誤"
            )
        
        # 檢查使用者是否啟用
        user = db.get_user(user_id)
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="使用者已被停用"
            )
        
        # 建立 JWT token
        token = create_token(
            user_id=user_id,
            role=user["role"],
            display_name=user["display_name"]
        )
        
        return {"access_token": token, "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登入失敗: {str(e)}")

@app.get("/api/me")
async def get_current_user(authorization: str = Header(None)):
    """
    取得目前使用者資訊
    
    需要 JWT token 驗證
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        
        return {
            "user_id": token_data["sub"],
            "role": token_data["role"],
            "display_name": token_data.get("display_name", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

# ============ 文件管理 API ============

@app.post("/api/docs/upload")
async def upload_document(
    file: UploadFile = File(...),
    allowed_roles: str = Form("employee"),
    authorization: str = Header(None)
):
    """
    上傳文件
    
    需要 JWT token 驗證
    預設 approved=0（需要 admin 審核）、is_active=1
    【重要】禁止在上傳時 process_file/add_to_vector_db，只存檔 + 寫 DB
    """
    try:
        # 驗證 JWT token
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        user_id = token_data["sub"]
        
        # 驗證檔名
        if not file.filename:
            raise HTTPException(status_code=400, detail="檔名無效")
        
        # 驗證副檔名（白名單：.pdf, .txt, .md）
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支援的檔案格式。允許: .pdf, .txt, .md"
            )
        
        # 生成安全的檔名
        try:
            safe_filename = generate_safe_filename(file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 流式上傳檔案
        file_path = UPLOAD_DIR / safe_filename
        try:
            file_size = await stream_write_file(file, file_path, MAX_FILE_SIZE)
        except HTTPException:
            raise
        
        # 驗證並解析角色
        try:
            roles_list = parse_doc_roles(allowed_roles)
        except ValueError as e:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e))
        
        # 生成文件 ID
        doc_id = str(uuid.uuid4())
        
        # 【重要】只存檔 + 寫 DB，禁止入庫
        # 保存到資料庫（uploaded_by 記錄上傳者、approved=0 等待審核、is_active=1）
        db.add_document(doc_id, file.filename, safe_filename, roles_list, file_size, uploaded_by=user_id)
        
        # 【新增】logging：記錄文件上傳事件
        logger.info(
            f"UPLOAD success doc_id={doc_id} user={user_id} file={file.filename}"
        )
        
        return {
            "id": doc_id,
            "filename": file.filename,
            "file_size": file_size,
            "message": "文件上傳成功（待 admin 審核，審核後才會進入 RAG 檢索庫）"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

@app.get("/api/docs")
async def list_documents(authorization: str = Header(None)):
    """
    列出所有文件
    
    需要 JWT token 驗證
    """
    try:
        # 驗證 JWT token
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        
        user_id = token_data.get("sub")
        user_role = token_data.get("role")
        
        documents = db.list_documents()
        
        # 【重要】權限過濾：admin 看全部，非 admin 只看 approved=1 AND is_active=1 AND user_role in allowed_roles，或自己上傳的
        filtered_docs = []
        for doc in documents:
            if user_role == "admin":
                filtered_docs.append(doc)
            else:
                is_approved = doc.get("approved", 0) == 1
                is_active = doc.get("is_active", 1) == 1
                # 【重要】正規化 allowed_roles 為 list（可能是字串或 list）
                allowed_roles = doc.get("allowed_roles", [])
                if not isinstance(allowed_roles, list):
                    allowed_roles = [r.strip() for r in str(allowed_roles).split(",") if r.strip()]
                
                uploaded_by = doc.get("uploaded_by", "")
                is_own_doc = uploaded_by == user_id
                is_visible = is_approved and is_active and user_role in allowed_roles
                if is_own_doc or is_visible:
                    filtered_docs.append(doc)
        
        # 【重要】回傳必要欄位（包含 uploaded_by 和 approved，但不含 saved_filename 以避免內部檔名洩漏）
        result = []
        for doc in filtered_docs:
            # 【重要】正規化 allowed_roles 為 list，保證前後端一致
            allowed_roles = doc.get("allowed_roles", [])
            if not isinstance(allowed_roles, list):
                allowed_roles = [r.strip() for r in str(allowed_roles).split(",") if r.strip()]
            
            result.append({
                "id": doc["doc_id"],
                "filename": doc["filename"],
                "allowed_roles": allowed_roles,
                "uploaded_at": doc["uploaded_at"],
                "file_size": doc.get("file_size", 0),
                "uploaded_by": doc.get("uploaded_by", ""),
                "approved": doc.get("approved", 0),
                "is_active": doc.get("is_active", 1)
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@app.delete("/api/docs/{doc_id}")
async def delete_document(doc_id: str, authorization: str = Header(None)):
    """
    刪除文件
    
    需要 JWT token 驗證
    限制：只有 admin 或 uploaded_by==token.sub 才能刪
    """
    try:
        # 驗證 JWT token
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        user_id = token_data["sub"]
        user_role = token_data["role"]
        
        # 獲取文件資訊
        doc = db.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 權限檢查：只有 admin 或上傳者才能刪
        if user_role != "admin" and doc["uploaded_by"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權刪除此文件"
            )
        
        # 刪除向量庫
        delete_from_vector_db(doc_id)
        
        # 刪除檔案
        file_path = UPLOAD_DIR / doc["saved_filename"]
        file_path.unlink(missing_ok=True)
        
        # 刪除資料庫記錄
        db.delete_document(doc_id)
        
        return {"message": "文件已刪除"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")

# ============ QA API ============

@app.post("/api/qa", response_model=QAResponse)
async def qa_endpoint(request: QARequest, authorization: str = Header(None)):
    """
    提交問題（RAG 問答）
    
    只能查詢 approved=1 & is_active=1 的文件
    需要 JWT token 驗證
    """
    try:
        # 驗證 JWT token
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        user_role = token_data["role"]
        
        # 直接 await（修復：不需要 executor + asyncio.run）
        answer, sources = await perform_qa(request.question, user_role)
        
        # 【新增】logging：記錄 QA 查詢事件
        logger.info(
            f"QA_QUERY user={token_data['sub']} role={user_role} chunks={len(sources)}"
        )
        
        return QAResponse(answer=answer, sources=sources)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"問答失敗: {str(e)}")

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_endpoint(request: GenerateRequest, authorization: str = Header(None)):
    """
    生成表單內容
    
    需要 JWT token 驗證
    """
    try:
        # 驗證 JWT token
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        user_role = token_data["role"]
        
        # 直接 await（修復：不需要 executor + asyncio.run）
        content = await generate_form(request.template_type, request.inputs, user_role)
        
        return GenerateResponse(content=content)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失敗: {str(e)}")

# ========== Admin API ==========

@app.get("/api/admin/users")
async def admin_list_users(authorization: str = Header(None)):
    """
    列出所有使用者（僅 admin）
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        # 【重要】DB 層已經不選 password_hash，直接回傳
        users = db.list_users()
        return users
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@app.post("/api/admin/users")
async def admin_create_user(
    user_id: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    role: str = Form("employee"),
    authorization: str = Header(None)
):
    """
    新增使用者（僅 admin）
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        # 驗證角色
        try:
            parse_user_roles(role)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 新增使用者
        if db.add_user(user_id, password, display_name, role):
            return {"message": "使用者已建立"}
        else:
            raise HTTPException(status_code=400, detail="使用者已存在")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立失敗: {str(e)}")

@app.patch("/api/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    display_name: str = Form(None),
    role: str = Form(None),
    is_active: int = Form(None),
    password: str = Form(None),
    authorization: str = Header(None)
):
    """
    更新使用者（僅 admin）
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        # 【重要】驗證 is_active 只能是 0 或 1
        if is_active is not None and is_active not in [0, 1]:
            raise HTTPException(status_code=400, detail="is_active 只能是 0 或 1")
        
        # 驗證角色
        if role:
            try:
                parse_user_roles(role)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # 準備更新資料
        updates = {}
        if display_name:
            updates["display_name"] = display_name
        if role:
            updates["role"] = role
        if is_active is not None:
            updates["is_active"] = is_active
        if password:
            updates["password"] = password
        
        if db.update_user(user_id, **updates):
            return {"message": "使用者已更新"}
        else:
            raise HTTPException(status_code=404, detail="使用者不存在或更新失敗")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")

@app.get("/api/admin/docs")
async def admin_list_documents(authorization: str = Header(None)):
    """
    列出所有文件（僅 admin）
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        documents = db.list_documents()
        # 【重要】統一回傳 id 而非 doc_id，與一般使用者的 /api/docs 一致
        return [
            {
                "id": doc["doc_id"],  # 映射 doc_id 為 id
                "filename": doc["filename"],
                "saved_filename": doc["saved_filename"],
                "allowed_roles": doc["allowed_roles"],
                "uploaded_at": doc["uploaded_at"],
                "file_size": doc.get("file_size", 0),
                "approved": doc.get("approved", 0),
                "is_active": doc.get("is_active", 1),
                "uploaded_by": doc.get("uploaded_by", "")
            }
            for doc in documents
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

@app.patch("/api/admin/docs/{doc_id}")
async def admin_update_document(
    doc_id: str,
    allowed_roles: str = Form(None),
    approved: int = Form(None),
    is_active: int = Form(None),
    authorization: str = Header(None)
):
    """
    更新文件（僅 admin）
    
    【重要邏輯】
    - 若 approved 從 0->1：從 uploads 讀檔，process_file 後 add_to_vector_db
    - 若 approved 從 1->0 或 is_active 從 1->0：delete_from_vector_db
    - 若 allowed_roles 改變且 approved=1 & is_active=1：delete 後重新 process_file/add
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        # 獲取文件資訊
        doc = db.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 【重要】驗證 approved 只能是 0 或 1
        if approved is not None and approved not in [0, 1]:
            raise HTTPException(status_code=400, detail="approved 只能是 0 或 1")
        
        # 【重要】驗證 is_active 只能是 0 或 1
        if is_active is not None and is_active not in [0, 1]:
            raise HTTPException(status_code=400, detail="is_active 只能是 0 或 1")
        
        # 驗證角色
        if allowed_roles:
            try:
                parse_doc_roles(allowed_roles)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # 記錄舊狀態
        old_approved = doc["approved"]
        old_is_active = doc["is_active"]
        old_allowed_roles = doc["allowed_roles"]
        
        # 準備更新資料
        updates = {}
        if allowed_roles:
            # 【重要】使用已驗證 + strip 的角色列表
            updates["allowed_roles"] = parse_doc_roles(allowed_roles)
        if approved is not None:
            updates["approved"] = approved
        if is_active is not None:
            updates["is_active"] = is_active
        
        # 更新資料庫
        if not db.update_document(doc_id, **updates):
            raise HTTPException(status_code=500, detail="更新失敗")
        
        # 【重要】處理向量庫邏輯
        
        # 情況 1：approved 從 0->1（審核通過，入庫）
        if old_approved == 0 and approved == 1:
            try:
                file_path = UPLOAD_DIR / doc["saved_filename"]
                if not file_path.exists():
                    raise HTTPException(status_code=500, detail="檔案不存在")
                
                # 【重要】使用新角色（若有改變）或舊角色
                new_allowed_roles = allowed_roles if allowed_roles else old_allowed_roles
                roles_list = parse_doc_roles(new_allowed_roles) if isinstance(new_allowed_roles, str) else new_allowed_roles
                # 【重要】第一個參數是 doc_id，不是 file_path！
                process_file(doc_id, str(file_path), doc["filename"], roles_list, approved=1, is_active=1)
                
                # 【新增】logging：記錄文件審核通過事件
                logger.info(
                    f"APPROVED doc_id={doc_id} by={token_data['sub']}"
                )
            except Exception as e:
                # 【新增】logging：記錄向量庫入庫失敗
                logger.error(
                    f"VECTOR_INSERT_FAIL doc_id={doc_id}"
                )
                # 【重要】先清掉可能殘留的 chunk，再回滚 DB 狀態
                delete_from_vector_db(doc_id)
                db.update_document(doc_id, approved=old_approved, is_active=old_is_active, allowed_roles=old_allowed_roles)
                raise HTTPException(status_code=500, detail=f"入庫失敗: {str(e)}")
        
        # 情況 2：approved 從 1->0 或 is_active 從 1->0（撤審/下架，移出庫）
        if (old_approved == 1 and approved == 0) or (old_is_active == 1 and is_active == 0):
            delete_from_vector_db(doc_id)
            
            # 【新增】logging：記錄向量庫刪除事件
            logger.info(
                f"VECTOR_DELETE doc_id={doc_id}"
            )
        
        # 情況 3：allowed_roles 改變且目前 approved=1 & is_active=1（更新觖色旗標）
        new_approved = approved if approved is not None else old_approved
        new_is_active = is_active if is_active is not None else old_is_active
        new_allowed_roles = allowed_roles if allowed_roles else old_allowed_roles
        
        # 【重要】統一成 list 並比較，避免类型不一致導致誤判
        normalized_new_roles = parse_doc_roles(new_allowed_roles) if isinstance(new_allowed_roles, str) else new_allowed_roles
        normalized_old_roles = old_allowed_roles if isinstance(old_allowed_roles, list) else parse_doc_roles(old_allowed_roles)
        
        # 用 set 比較，不受順序影響
        if set(normalized_new_roles) != set(normalized_old_roles) and new_approved == 1 and new_is_active == 1:
            try:
                # 先刪除舊的
                delete_from_vector_db(doc_id)
                
                # 再重新入庫
                file_path = UPLOAD_DIR / doc["saved_filename"]
                if not file_path.exists():
                    raise HTTPException(status_code=500, detail="檔案不存在")
                
                roles_list = parse_doc_roles(new_allowed_roles) if isinstance(new_allowed_roles, str) else new_allowed_roles
                # 【重要】第一個參數是 doc_id，不是 file_path！
                process_file(doc_id, str(file_path), doc["filename"], roles_list, approved=1, is_active=1)
                
                # 【新增】logging：記錄文件審核通過事件
                logger.info(
                    f"APPROVED doc_id={doc_id} by={token_data['sub']}"
                )
            except Exception as e:
                # 【新增】logging：記錄向量庫入庫失敗
                logger.error(
                    f"VECTOR_INSERT_FAIL doc_id={doc_id}"
                )
                # 【重要】先清掉可能殘留的 chunk，再回滚 DB 狀態
                delete_from_vector_db(doc_id)
                db.update_document(doc_id, approved=old_approved, is_active=old_is_active, allowed_roles=old_allowed_roles)
                raise HTTPException(status_code=500, detail=f"更新角色旗標失敗: {str(e)}")
        
        return {"message": "文件已更新"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")

@app.delete("/api/admin/docs/{doc_id}")
async def admin_delete_document(doc_id: str, authorization: str = Header(None)):
    """
    刪除文件（僅 admin）
    
    刪除向量庫 + DB + uploads 檔
    """
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Authorization header"
            )
        
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        require_admin(token_data)
        
        # 獲取文件資訊
        doc = db.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 刪除向量庫
        delete_from_vector_db(doc_id)
        
        # 刪除檔案
        file_path = UPLOAD_DIR / doc["saved_filename"]
        file_path.unlink(missing_ok=True)
        
        # 刪除資料庫記錄
        db.delete_document(doc_id)
        
        return {"message": "文件已刪除"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")
