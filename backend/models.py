from pydantic import BaseModel, Field
from typing import List, Optional

# ============ 請求/回應模型 ============

# 【注】DocumentResponse 已移除，使用實際 API 回傳的 dict 結構
# - /api/docs（一般使用者）：id, filename, file_size, uploaded_at, approved, is_active, uploaded_by
# - /api/admin/docs（admin）：id, filename, saved_filename, file_size, uploaded_at, approved, is_active, uploaded_by, allowed_roles

class QARequest(BaseModel):
    """問答請求"""
    question: str = Field(description="問題")
    # 注意：使用者角色由 JWT token 決定，不由 request body 提供

class Source(BaseModel):
    """引用來源"""
    doc_name: str = Field(description="文件名稱")
    chunk_text: str = Field(description="文本片段")
    page_or_section: str = Field(description="頁碼或段落")

class QAResponse(BaseModel):
    """問答回應"""
    answer: str = Field(description="回答")
    sources: List[Source] = Field(default=[], description="引用來源")

class GenerateRequest(BaseModel):
    """表單生成請求"""
    template_type: str = Field(description="模板類型")
    inputs: dict = Field(description="表單輸入")
    # 注意：使用者角色由 JWT token 決定，不由 request body 提供

class GenerateResponse(BaseModel):
    """表單生成回應"""
    content: str = Field(description="生成的內容")

# ============ SQLite 資料庫模型 ============

class DocumentRecord:
    """文件記錄（SQLite 表）"""
    def __init__(self, doc_id: str, filename: str, saved_filename: str, 
                 allowed_roles: str, uploaded_at: str, file_size: int = 0):
        self.doc_id = doc_id
        self.filename = filename
        self.saved_filename = saved_filename
        self.allowed_roles = allowed_roles  # 逗號分隔的字符串
        self.uploaded_at = uploaded_at
        self.file_size = file_size

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.doc_id,
            "filename": self.filename,
            "saved_filename": self.saved_filename,
            "allowed_roles": self.allowed_roles.split(","),
            "uploaded_at": self.uploaded_at,
            "file_size": self.file_size
        }
