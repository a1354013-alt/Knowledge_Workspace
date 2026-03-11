import os
import sqlite3
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import bcrypt

# ============ Embedding Function 快取 ============

_EMBEDDING_FUNCTION = None
_COLLECTION = None

def get_embedding_function():
    """
    獲取 embedding function（快取版本）
    優先使用 OpenAI，如果沒有 key 則使用 sentence-transformers
    """
    global _EMBEDDING_FUNCTION
    
    if _EMBEDDING_FUNCTION is not None:
        return _EMBEDDING_FUNCTION
    
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if openai_key:
        try:
            # 使用 OpenAI embeddings
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            _EMBEDDING_FUNCTION = OpenAIEmbeddingFunction(
                api_key=openai_key,
                model_name="text-embedding-3-small"
            )
            print("✅ 使用 OpenAI embeddings")
            return _EMBEDDING_FUNCTION
        except Exception as e:
            print(f"⚠️ OpenAI embedding 初始化失敗 ({e})，改用 sentence-transformers")
    
    # 備選：使用 sentence-transformers（本地模型）
    try:
        _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        print("✅ 使用 sentence-transformers embeddings")
        return _EMBEDDING_FUNCTION
    except Exception as e:
        print(f"❌ 無法載入 embedding function: {e}")
        raise RuntimeError("No embedding function available")

# ============ SQLite 資料庫管理 ============

class DocumentDatabase:
    """文件資料庫（SQLite）"""
    
    def __init__(self, db_path: str = "documents.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化資料庫（包含 migration）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 建立 users 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'employee',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 建立 documents 表（新增審核欄位）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    saved_filename TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    uploaded_by TEXT,
                    uploaded_at TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    approved INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Migration：添加新欄位（如果不存在）
            self._migrate_documents_table(cursor)
            
            # Seed 預設 admin 使用者
            self._seed_admin_user(cursor)
            
            conn.commit()
    
    def _migrate_documents_table(self, cursor):
        """Migration：為既有表添加新欄位"""
        # 檢查欄位是否存在
        cursor.execute("PRAGMA table_info(documents)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "uploaded_by" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN uploaded_by TEXT")
        if "approved" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN approved INTEGER DEFAULT 0")
        if "is_active" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN is_active INTEGER DEFAULT 1")
        if "updated_at" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    
    def _seed_admin_user(self, cursor):
        """Seed 預設 admin 使用者（如果 users 表為空）"""
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # 預設密碼：admin12345（README 提醒必改）
            password_hash = bcrypt.hashpw(b"admin12345", bcrypt.gensalt()).decode()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("admin", password_hash, "Administrator", "admin", 1, now, now))
            print("✅ 預設 admin 使用者已建立（密碼：admin12345，請立即修改！）")
    
    # ============ Users 操作 ============
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """取得使用者"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """驗證密碼"""
        user = self.get_user(user_id)
        if not user:
            return False
        return bcrypt.checkpw(password.encode(), user["password_hash"].encode())
    
    def list_users(self) -> List[Dict]:
        """列出所有使用者"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, display_name, role, is_active, created_at FROM users ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def add_user(self, user_id: str, password: str, display_name: str, role: str = "employee") -> bool:
        """新增使用者"""
        try:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            now = datetime.utcnow().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, password_hash, display_name, role, 1, now, now))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新使用者（支援 role, is_active, display_name, password）"""
        try:
            updates = []
            params = []
            now = datetime.utcnow().isoformat()
            
            for key, value in kwargs.items():
                if key == "password":
                    updates.append("password_hash = ?")
                    params.append(bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode())
                elif key in ("role", "is_active", "display_name"):
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(now)
            params.append(user_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
                cursor.execute(query, params)
                conn.commit()
            return True
        except Exception:
            return False
    
    # ============ Documents 操作 ============
    
    def add_document(self, doc_id: str, filename: str, saved_filename: str,
                     allowed_roles: List[str], file_size: int = 0, uploaded_by: str = None) -> bool:
        """添加文件記錄"""
        try:
            now = datetime.utcnow().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO documents 
                    (doc_id, filename, saved_filename, allowed_roles, uploaded_by, uploaded_at, file_size, approved, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (doc_id, filename, saved_filename, ",".join(allowed_roles), uploaded_by, now, file_size, 0, 1, now))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """取得文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_documents(self) -> List[Dict]:
        """列出所有文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_id, filename, allowed_roles, uploaded_by, uploaded_at, approved, is_active, updated_at
                FROM documents ORDER BY uploaded_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_document(self, doc_id: str, **kwargs) -> bool:
        """更新文件（支援 allowed_roles, approved, is_active）"""
        try:
            updates = []
            params = []
            now = datetime.utcnow().isoformat()
            
            for key, value in kwargs.items():
                if key == "allowed_roles" and isinstance(value, list):
                    updates.append("allowed_roles = ?")
                    params.append(",".join(value))
                elif key in ("approved", "is_active"):
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(now)
            params.append(doc_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE documents SET {', '.join(updates)} WHERE doc_id = ?"
                cursor.execute(query, params)
                conn.commit()
            return True
        except Exception:
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """刪除文件記錄"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
                conn.commit()
            return True
        except Exception:
            return False

# ============ ChromaDB 向量庫操作 ============

def get_collection():
    """取得 ChromaDB collection（快取版本）"""
    global _COLLECTION
    
    if _COLLECTION is not None:
        return _COLLECTION
    
    client = chromadb.Client()
    _COLLECTION = client.get_or_create_collection(
        name="documents",
        embedding_function=get_embedding_function()
    )
    return _COLLECTION

def add_to_vector_db(doc_id: str, chunks: List[str], metadatas: List[Dict], allowed_roles: List[str]) -> bool:
    """
    添加文件到向量庫
    
    metadatas 應包含：doc_id, page_or_section, approved, is_active
    並自動添加角色旗標：role_employee, role_manager, role_hr, role_admin
    """
    try:
        collection = get_collection()
        
        # 為每個 chunk 添加角色旗標
        for metadata in metadatas:
            # 【重要】不強制設定 approved/is_active，由流程控制
            # 添加角色旗標（用於 where_filter）
            for role in ["employee", "manager", "hr", "admin"]:
                metadata[f"role_{role}"] = role in allowed_roles
        
        # 生成 IDs
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return True
    except Exception as e:
        print(f"❌ 向量庫添加失敗: {e}")
        return False

def query_vector_db(question: str, user_role: str, n_results: int = 5) -> List[Tuple[str, str, Dict]]:
    """
    查詢向量庫（帶權限過濾）
    
    返回：[(doc_id, chunk_text, metadata), ...]
    
    where_filter：只查詢 approved=1 & is_active=1 & role_{user_role}=true
    """
    try:
        collection = get_collection()
        
        # 構建 where_filter
        where_filter = {
            "$and": [
                {"approved": 1},
                {"is_active": 1},
                {f"role_{user_role}": True}
            ]
        }
        
        # 特殊處理 admin：可查看所有已批准的文件
        if user_role == "admin":
            where_filter = {
                "$and": [
                    {"approved": 1},
                    {"is_active": 1}
                ]
            }
        
        results = collection.query(
            query_texts=[question],
            n_results=n_results,
            where=where_filter
        )
        
        # 解析結果
        output = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                output.append((metadata.get("doc_id", ""), doc, metadata))
        
        return output
    except Exception as e:
        print(f"❌ 向量庫查詢失敗: {e}")
        return []

def delete_from_vector_db(doc_id: str) -> bool:
    """刪除文件的所有 chunks"""
    try:
        collection = get_collection()
        # 刪除所有 doc_id 開頭的 IDs
        collection.delete(where={"doc_id": doc_id})
        return True
    except Exception as e:
        print(f"❌ 向量庫刪除失敗: {e}")
        return False
