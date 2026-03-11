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
    
    【重要】快取機制：第一次存取後不會再改變。
    若要切換 embedding 來源，需要重新啟動服務。
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
            # 從環境變數讀取密碼，或使用預設值
            default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin12345")
            password_hash = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO users (user_id, password_hash, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("admin", password_hash, "Administrator", "admin", 1, now, now))
            
            # 警告：使用預設密碼
            if default_password == "admin12345":
                print("\n" + "="*70)
                print("⚠️  警告：Admin 使用預設密碼！")
                print("="*70)
                print("✅ 預設 admin 使用者已建立")
                print("⚠️  密碼: admin12345 (預設值)")
                print("⚠️  建議：立即修改密碼！")
                print("⚠️  方法：使用 DEFAULT_ADMIN_PASSWORD 環境變數來設定自訂密碼")
                print("="*70 + "\n")
            else:
                print("✅ 預設 admin 使用者已建立（使用自訂密碼）")
    
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
        """列出所有使用者（不選擇 password_hash）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # 【重要】只選擇必要欄位，不選 password_hash
            cursor.execute("""
                SELECT user_id, display_name, role, is_active, created_at, updated_at 
                FROM users
            """)
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
        """更新使用者（支援 password, display_name, role, is_active）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 構建 UPDATE 語句
                updates = []
                params = []
                
                if "password" in kwargs:
                    password_hash = bcrypt.hashpw(kwargs["password"].encode(), bcrypt.gensalt()).decode()
                    updates.append("password_hash = ?")
                    params.append(password_hash)
                
                if "display_name" in kwargs:
                    updates.append("display_name = ?")
                    params.append(kwargs["display_name"])
                
                if "role" in kwargs:
                    updates.append("role = ?")
                    params.append(kwargs["role"])
                
                if "is_active" in kwargs:
                    updates.append("is_active = ?")
                    params.append(kwargs["is_active"])
                
                if not updates:
                    return False
                
                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())
                params.append(user_id)
                
                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 更新使用者失敗: {e}")
            return False
    
    # ============ Documents 操作 ============
    
    def add_document(self, doc_id: str, filename: str, saved_filename: str, 
                     allowed_roles: List[str], file_size: int = 0, uploaded_by: str = None) -> bool:
        """新增文件（預設 approved=0, is_active=1）"""
        try:
            roles_str = ",".join(allowed_roles)
            now = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO documents 
                    (doc_id, filename, saved_filename, allowed_roles, uploaded_by, uploaded_at, file_size, approved, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (doc_id, filename, saved_filename, roles_str, uploaded_by, now, file_size, 0, 1, now))
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ 新增文件失敗: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """取得文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                doc = dict(row)
                doc["allowed_roles"] = doc["allowed_roles"].split(",")
                return doc
            return None
    
    def list_documents(self) -> List[Dict]:
        """列出所有文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
            docs = []
            for row in cursor.fetchall():
                doc = dict(row)
                doc["allowed_roles"] = doc["allowed_roles"].split(",")
                docs.append(doc)
            return docs
    
    def update_document(self, doc_id: str, **kwargs) -> bool:
        """更新文件（支援 approved, is_active, allowed_roles）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if "approved" in kwargs:
                    updates.append("approved = ?")
                    params.append(kwargs["approved"])
                
                if "is_active" in kwargs:
                    updates.append("is_active = ?")
                    params.append(kwargs["is_active"])
                
                if "allowed_roles" in kwargs:
                    roles_str = ",".join(kwargs["allowed_roles"])
                    updates.append("allowed_roles = ?")
                    params.append(roles_str)
                
                if not updates:
                    return False
                
                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())
                params.append(doc_id)
                
                cursor.execute(f"UPDATE documents SET {', '.join(updates)} WHERE doc_id = ?", params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 更新文件失敗: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """刪除文件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ 刪除文件失敗: {e}")
            return False

# ============ ChromaDB 向量庫操作 ============

def get_collection():
    """獲取 ChromaDB collection（快取版本）"""
    global _COLLECTION
    
    if _COLLECTION is not None:
        return _COLLECTION
    
    try:
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
        _COLLECTION = client.get_or_create_collection(
            name="documents",
            embedding_function=get_embedding_function(),
            metadata={"hnsw:space": "cosine"}
        )
        return _COLLECTION
    except Exception as e:
        print(f"❌ ChromaDB 初始化失敗: {e}")
        raise RuntimeError("ChromaDB initialization failed")

def add_to_vector_db(doc_id: str, chunks: List[str], metadata_list: List[Dict], allowed_roles: List[str] = None) -> bool:
    """
    新增文件 chunks 到向量庫
    
    參數:
        doc_id: 文件 ID
        chunks: 文本 chunks 列表
        metadata_list: 每個 chunk 的 metadata 列表
        allowed_roles: 允許查看的角色列表（用於生成角色旗標）
    
    【重要】此函數會自動在每個 metadata 中添加角色旗標：
    - role_employee: True/False
    - role_manager: True/False
    - role_hr: True/False
    - role_admin: True/False
    """
    try:
        collection = get_collection()
        
        # 為每個 chunk 生成唯一 ID
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        
        # 【重要】補充角色旗標到每個 metadata（永遠存在）
        # 若 allowed_roles 未傳入或為空，從 metadata 中解析
        if not allowed_roles:
            # 從 metadata 中解析 allowed_roles
            for metadata in metadata_list:
                roles_str = metadata.get("allowed_roles", "")
                if isinstance(roles_str, str):
                    allowed_roles = [r.strip() for r in roles_str.split(",") if r.strip()]
                elif isinstance(roles_str, list):
                    allowed_roles = roles_str
                else:
                    allowed_roles = []
                break  # 只需讀第一筆
        
        for metadata in metadata_list:
            # 初始化所有角色為 False
            metadata["role_employee"] = "employee" in allowed_roles
            metadata["role_manager"] = "manager" in allowed_roles
            metadata["role_hr"] = "hr" in allowed_roles
            metadata["role_admin"] = "admin" in allowed_roles
        
        # 新增到向量庫
        collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadata_list
        )
        return True
    except Exception as e:
        print(f"❌ 向量庫新增失敗: {e}")
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
