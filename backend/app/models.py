"""Pydantic models for API contracts and typed payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROLE_VALUES = ("owner",)
WORKFLOW_STATUS_VALUES = ("draft", "reviewed", "verified", "archived")
SOURCE_TYPE_VALUES = ("manual", "document-derived", "autotest-derived")
AUTOTEST_RUN_STATUS_VALUES = ("queued", "running", "passed", "failed")
AUTOTEST_STEP_STATUS_VALUES = ("queued", "running", "passed", "failed", "skipped", "unavailable")

AutoTestRunStatus = Literal["queued", "running", "passed", "failed"]
AutoTestStepStatus = Literal["queued", "running", "passed", "failed", "skipped", "unavailable"]
AutoTestExecutionMode = Literal["real", "simulated"]
AutoTestExportFormat = Literal["md", "html"]


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
    index_status: Literal["pending", "indexed", "failed"] = "pending"
    index_error: str = ""
    indexed_at: str = ""


class UploadDocumentResponse(DocumentResponse):
    message: str


class DocumentUpdateRequest(StrictModel):
    category: str | None = Field(default=None, max_length=200)
    tags: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "reviewed", "verified", "archived"] | None = None


class HealthResponse(StrictModel):
    status: str
    version: str


class DashboardKnowledgeMetrics(StrictModel):
    total: int
    by_status: dict[str, int]


class DashboardLogbookMetrics(StrictModel):
    total: int
    with_solution: int
    promoted_to_knowledge: int
    resolution_rate: float


# Moved DashboardAutoTestMetrics below AutoTestRunListItemResponse to avoid forward reference issues


class DashboardDocumentMetrics(StrictModel):
    total: int
    indexed: int
    pending: int
    failed_documents: int
    archived_documents: int


class DashboardRecentActivity(StrictModel):
    days: int
    documents_added: int
    knowledge_added: int
    logbook_added: int
    autotest_runs: int
    autotest_passed: int
    autotest_failed: int


# Moved DashboardHealthResponse to the bottom of the file


class SettingsLLMResponse(StrictModel):
    primary_provider: str
    active_provider: str
    model: str
    base_url: str
    primary_healthy: bool
    fallback_enabled: bool
    llm_ready_for_generation: bool
    error_message: str = ""


class SettingsOCRResponse(StrictModel):
    enabled: bool
    available: bool
    tesseract_cmd: str = ""
    tesseract_version: str = ""
    details: str = ""


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
    source_type: Literal["manual", "document-derived", "autotest-derived"] = "manual"
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
    change_note: str | None = Field(default=None, max_length=500)


class KnowledgeRevisionResponse(StrictModel):
    revision_id: str
    entry_id: str
    version_number: int
    title: str
    status: Literal["draft", "reviewed", "verified", "archived"] = "draft"
    problem: str
    root_cause: str
    solution: str
    tags: str
    notes: str
    source_type: Literal["manual", "document-derived", "autotest-derived"] = "manual"
    source_ref: str = ""
    change_note: str
    created_at: str


class KnowledgeRevisionDiffItem(StrictModel):
    field: str
    old_value: str
    new_value: str


class KnowledgeRevisionDiffResponse(StrictModel):
    revision_id: str
    entry_id: str
    changed: list[KnowledgeRevisionDiffItem] = Field(default_factory=list)


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
    source_type: Literal["manual", "document-derived", "autotest-derived"] = "manual"
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
    index_status: Literal["indexed", "failed"] = "indexed"
    index_error: str = ""


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
    status: AutoTestStepStatus
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
    status: AutoTestRunStatus
    created_at: str
    summary: str


class AutoTestTimelineItemResponse(StrictModel):
    key: str
    label: str
    name: str
    status: Literal["pending", "running", "success", "failed", "skipped"]
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    message: str | None = None


class DashboardAutoTestMetrics(StrictModel):
    total_runs: int
    passed: int
    failed: int
    pass_rate: float
    recent_runs: list[AutoTestRunListItemResponse] = Field(default_factory=list)


class AutoTestRunResponse(StrictModel):
    id: str
    source_type: str
    source_ref: str
    execution_mode: AutoTestExecutionMode = "real"
    project_type_detected: str = ""
    working_directory: str = ""
    project_name: str = ""
    project_type: str
    status: AutoTestRunStatus
    summary: str
    suggestion: str
    prompt_output: str
    failed_reason: str = ""
    problem_entry_id: str = ""
    solution_entry_id: str = ""
    created_at: str
    steps: list[AutoTestStepResponse] = Field(default_factory=list)
    timeline: list[AutoTestTimelineItemResponse] = Field(default_factory=list)


class GitHubAnalyzeRequest(StrictModel):
    repo_url: str = Field(min_length=1, max_length=2000)


class GitHubRepoInfoResponse(StrictModel):
    owner: str
    repo: str
    url: str
    default_branch: str = ""
    provider: str = "github"
    clone_supported: bool = False


class GitHubAnalyzeResponse(StrictModel):
    run_id: str
    status: Literal["queued"]
    repo_info: GitHubRepoInfoResponse


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


class DashboardHealthResponse(StrictModel):
    knowledge: DashboardKnowledgeMetrics
    logbook: DashboardLogbookMetrics
    autotest: DashboardAutoTestMetrics
    documents: DashboardDocumentMetrics
    recent_activity: DashboardRecentActivity


# Note: model_rebuild() is no longer needed in Pydantic v2
# Models are automatically rebuilt when all forward references are resolved
