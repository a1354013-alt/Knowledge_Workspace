from __future__ import annotations

"""Pydantic models for API contracts and typed payloads."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ROLE_VALUES = ("owner",)
WORKFLOW_STATUS_VALUES = ("draft", "reviewed", "verified", "archived")
SOURCE_TYPE_VALUES = ("manual", "document-derived", "autotest-derived")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageResponse(StrictModel):
    message: str


class LoginRequest(StrictModel):
    user_id: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class LoginResponse(StrictModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(StrictModel):
    user_id: str
    role: str
    display_name: str


class Source(StrictModel):
    source_type: str
    title: str
    location: str | None = None
    snippet: str


class QARequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)


class QAResponse(StrictModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)


class GenerateRequest(StrictModel):
    template_type: str = Field(min_length=1, max_length=100)
    inputs: dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(StrictModel):
    content: str


class DocumentResponse(StrictModel):
    id: str
    filename: str
    category: str
    tags: str
    status: Literal["draft", "reviewed", "verified", "archived"] = "reviewed"
    uploaded_at: str
    updated_at: str
    file_size: int
    uploaded_by: str | None = None


class UploadDocumentResponse(DocumentResponse):
    message: str


class DocumentUpdateRequest(StrictModel):
    category: str | None = Field(default=None, max_length=200)
    tags: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "reviewed", "verified", "archived"] | None = None


class HealthResponse(StrictModel):
    status: str
    version: str


class SettingsLLMResponse(StrictModel):
    provider: str
    model: str
    base_url: str
    healthy: bool
    fallback_mode: bool


class SettingsOCRResponse(StrictModel):
    enabled: bool
    available: bool


class KnowledgeEntryCreateRequest(StrictModel):
    title: str = Field(default="", max_length=200)
    problem: str = Field(min_length=1, max_length=8000)
    root_cause: str = Field(default="", max_length=8000)
    solution: str = Field(min_length=1, max_length=12000)
    tags: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=8000)
    status: Literal["draft", "reviewed", "verified", "archived"] = "draft"
    source_type: Literal["manual", "document-derived", "autotest-derived"] = "manual"
    source_ref: str = Field(default="", max_length=2000)
    related_item_ids: list[str] = Field(default_factory=list)


class KnowledgeEntryResponse(StrictModel):
    id: str
    title: str
    status: Literal["draft", "reviewed", "verified", "archived"] = "draft"
    problem: str
    root_cause: str
    solution: str
    tags: str
    notes: str
    source_type: str = "manual"
    source_ref: str = ""
    related_item_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class KnowledgeEntryUpdateRequest(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    status: Literal["draft", "reviewed", "verified", "archived"] | None = None
    problem: str | None = Field(default=None, max_length=8000)
    root_cause: str | None = Field(default=None, max_length=8000)
    solution: str | None = Field(default=None, max_length=12000)
    tags: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=8000)
    source_type: Literal["manual", "document-derived", "autotest-derived"] | None = None
    source_ref: str | None = Field(default=None, max_length=2000)
    related_item_ids: list[str] | None = None


class LogbookEntryCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    problem: str = Field(min_length=1, max_length=8000)
    root_cause: str = Field(default="", max_length=8000)
    solution: str = Field(min_length=1, max_length=12000)
    tags: str = Field(default="", max_length=2000)
    status: Literal["draft", "reviewed", "verified", "archived"] = "draft"
    source_type: Literal["manual", "document-derived", "autotest-derived"] = "manual"
    source_ref: str = Field(default="", max_length=2000)
    related_item_ids: list[str] = Field(default_factory=list)


class LogbookEntryResponse(StrictModel):
    id: str
    title: str
    status: Literal["draft", "reviewed", "verified", "archived"] = "draft"
    run_id: str = ""
    problem: str
    root_cause: str
    solution: str
    tags: str
    source_type: str
    source_ref: str = ""
    related_item_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class LogbookEntryUpdateRequest(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    status: Literal["draft", "reviewed", "verified", "archived"] | None = None
    problem: str | None = Field(default=None, max_length=8000)
    root_cause: str | None = Field(default=None, max_length=8000)
    solution: str | None = Field(default=None, max_length=12000)
    tags: str | None = Field(default=None, max_length=2000)
    source_type: Literal["manual", "document-derived", "autotest-derived"] | None = None
    source_ref: str | None = Field(default=None, max_length=2000)
    related_item_ids: list[str] | None = None


class PromoteToKnowledgeResponse(StrictModel):
    message: str
    knowledge_entry_id: str


class SavedPromptCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=12000)
    tags: str = Field(default="", max_length=2000)


class SavedPromptResponse(StrictModel):
    id: str
    title: str
    content: str
    tags: str
    created_at: str
    updated_at: str


class PhotoResponse(StrictModel):
    id: str
    filename: str
    tags: str
    description: str
    status: Literal["draft", "reviewed", "verified", "archived"] = "reviewed"
    uploaded_by: str | None = None
    created_at: str
    updated_at: str
    file_size: int
    ocr_text: str


class UploadPhotoResponse(PhotoResponse):
    message: str


class PhotoUpdateRequest(StrictModel):
    tags: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=8000)
    status: Literal["draft", "reviewed", "verified", "archived"] | None = None


class AutoTestStepResponse(StrictModel):
    step_id: str
    name: str
    command: str
    status: str
    started_at: str = ""
    finished_at: str = ""
    output: str = ""
    success: int = 0
    exit_code: int
    stdout_summary: str
    stderr_summary: str
    error_type: str
    created_at: str


class AutoTestRunListItemResponse(StrictModel):
    id: str
    project_name: str
    status: str
    created_at: str
    summary: str


class AutoTestRunResponse(StrictModel):
    id: str
    source_type: str
    source_ref: str
    execution_mode: Literal["real", "simulated"] = "real"
    project_type_detected: str = ""
    working_directory: str = ""
    project_name: str = ""
    project_type: str
    status: str
    summary: str
    suggestion: str
    prompt_output: str
    problem_entry_id: str = ""
    solution_entry_id: str = ""
    created_at: str
    steps: list[AutoTestStepResponse] = Field(default_factory=list)


class ItemSummary(StrictModel):
    item_id: str
    item_type: str
    title: str
    status: str = ""
    updated_at: str = ""
    created_at: str = ""
    source_type: str = ""
    source_ref: str = ""


class ItemLinkResolved(StrictModel):
    link_id: str
    from_item_id: str
    to_item_id: str
    link_type: str
    created_at: str
    other_item: ItemSummary | None = None


class ItemLinksResponse(StrictModel):
    item_id: str
    links: list[ItemLinkResolved] = Field(default_factory=list)


class ResolveItemsRequest(StrictModel):
    item_ids: list[str] = Field(default_factory=list)



class ResolveItemsResponse(StrictModel):
    items: list[ItemSummary] = Field(default_factory=list)


# Note: model_rebuild() is no longer needed in Pydantic v2
# Models are automatically rebuilt when all forward references are resolved
