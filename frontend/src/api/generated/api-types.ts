/* Generated from docs/openapi.json. Do not edit by hand. */
/* Run: npm run generate:api-types */

export interface AutoTestCapabilitiesResponse {
  message: string;
  mode: "real" | "simulated";
  real_mode_available: boolean;
  real_mode_enabled: boolean;
  real_mode_requested: boolean;
}

export interface AutoTestRunListItemResponse {
  created_at: string;
  id: string;
  project_name: string;
  status: "queued" | "running" | "passed" | "failed";
  summary: string;
}

export interface AutoTestRunResponse {
  created_at: string;
  execution_mode?: "real" | "simulated";
  failed_reason?: string;
  id: string;
  problem_entry_id?: string;
  project_name?: string;
  project_type: string;
  project_type_detected?: string;
  prompt_output: string;
  solution_entry_id?: string;
  source_ref: string;
  source_type: string;
  status: "queued" | "running" | "passed" | "failed";
  steps?: AutoTestStepResponse[];
  suggestion: string;
  summary: string;
  timeline?: AutoTestTimelineItemResponse[];
  working_directory?: string;
}

export interface AutoTestStepResponse {
  command: string;
  created_at: string;
  error_type: string;
  exit_code: number;
  finished_at?: string;
  name: string;
  output?: string;
  started_at?: string;
  status: "queued" | "running" | "passed" | "failed" | "skipped" | "unavailable";
  stderr_summary: string;
  stdout_summary: string;
  step_id: string;
  success?: number;
}

export interface AutoTestTimelineItemResponse {
  duration_ms?: number | null;
  finished_at?: string | null;
  key: string;
  label: string;
  message?: string | null;
  name: string;
  started_at?: string | null;
  status: "pending" | "running" | "success" | "failed" | "skipped";
}

export interface Body_run_autotest_api_autotest_run_post {
  file: string;
}

export interface Body_upload_document_api_docs_upload_post {
  category?: string;
  file: string;
  tags?: string;
}

export interface Body_upload_photo_api_photos_upload_post {
  description?: string;
  file: string;
  tags?: string;
}

export interface DashboardAutoTestMetrics {
  failed: number;
  pass_rate: number;
  passed: number;
  recent_runs?: AutoTestRunListItemResponse[];
  total_runs: number;
}

export interface DashboardDocumentMetrics {
  archived_documents: number;
  failed_documents: number;
  indexed: number;
  pending: number;
  total: number;
}

export interface DashboardHealthResponse {
  autotest: DashboardAutoTestMetrics;
  documents: DashboardDocumentMetrics;
  knowledge: DashboardKnowledgeMetrics;
  logbook: DashboardLogbookMetrics;
  recent_activity: DashboardRecentActivity;
}

export interface DashboardKnowledgeMetrics {
  by_status: Record<string, unknown>;
  total: number;
}

export interface DashboardLogbookMetrics {
  promoted_to_knowledge: number;
  resolution_rate: number;
  total: number;
  with_solution: number;
}

export interface DashboardRecentActivity {
  autotest_failed: number;
  autotest_passed: number;
  autotest_runs: number;
  days: number;
  documents_added: number;
  knowledge_added: number;
  logbook_added: number;
}

export interface DocumentResponse {
  category: string;
  file_size: number;
  filename: string;
  id: string;
  index_error?: string;
  index_status?: "pending" | "indexed" | "failed" | "unavailable";
  indexed_at?: string;
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  updated_at: string;
  uploaded_at: string;
  uploaded_by?: string | null;
}

export interface DocumentUpdateRequest {
  category?: string | null;
  status?: "draft" | "reviewed" | "verified" | "archived" | null;
  tags?: string | null;
}

export interface GenerateRequest {
  inputs?: Record<string, unknown>;
  template_type: string;
}

export interface GenerateResponse {
  content: string;
}

export interface GitHubAnalyzeRequest {
  repo_url: string;
}

export interface GitHubAnalyzeResponse {
  analysis_scope?: "queued_local_intake_only";
  execution_mode?: "simulated";
  message: string;
  remote_clone_performed?: boolean;
  repo_info: GitHubRepoInfoResponse;
  report_ready?: boolean;
  run_id: string;
  status: "queued";
}

export interface GitHubRepoInfoResponse {
  analysis_scope?: "queued_local_intake_only";
  clone_supported?: boolean;
  default_branch?: string;
  owner: string;
  provider?: string;
  repo: string;
  url: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface ItemLinkResolved {
  created_at: string;
  from_item_id: string;
  link_id: string;
  link_type: string;
  other_item?: ItemSummary | null;
  to_item_id: string;
}

export interface ItemLinksResponse {
  item_id: string;
  links?: ItemLinkResolved[];
}

export interface ItemSummary {
  created_at?: string;
  item_id: string;
  item_type: string;
  source_ref?: string;
  source_type?: string;
  status?: string;
  title: string;
  updated_at?: string;
}

export interface KnowledgeEntryCreateRequest {
  notes?: string;
  problem: string;
  related_item_ids?: string[];
  root_cause?: string;
  solution: string;
  source_ref?: string;
  source_type?: "manual" | "document-derived" | "autotest-derived";
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags?: string;
  title?: string;
}

export interface KnowledgeEntryResponse {
  created_at: string;
  id: string;
  notes: string;
  problem: string;
  related_item_ids?: string[];
  root_cause: string;
  solution: string;
  source_ref?: string;
  source_type?: "manual" | "document-derived" | "autotest-derived";
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  title: string;
  updated_at: string;
}

export interface KnowledgeEntryUpdateRequest {
  change_note?: string | null;
  notes?: string | null;
  problem?: string | null;
  related_item_ids?: string[] | null;
  root_cause?: string | null;
  solution?: string | null;
  source_ref?: string | null;
  source_type?: "manual" | "document-derived" | "autotest-derived" | null;
  status?: "draft" | "reviewed" | "verified" | "archived" | null;
  tags?: string | null;
  title?: string | null;
}

export interface KnowledgeRevisionDiffItem {
  field: string;
  new_value: string;
  old_value: string;
}

export interface KnowledgeRevisionDiffResponse {
  changed?: KnowledgeRevisionDiffItem[];
  entry_id: string;
  revision_id: string;
}

export interface KnowledgeRevisionResponse {
  change_note: string;
  created_at: string;
  entry_id: string;
  notes: string;
  problem: string;
  revision_id: string;
  root_cause: string;
  solution: string;
  source_ref?: string;
  source_type?: "manual" | "document-derived" | "autotest-derived";
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  title: string;
  version_number: number;
}

export interface LogbookEntryCreateRequest {
  problem: string;
  related_item_ids?: string[];
  root_cause?: string;
  solution: string;
  source_ref?: string;
  source_type?: "manual" | "document-derived" | "autotest-derived";
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags?: string;
  title: string;
}

export interface LogbookEntryResponse {
  created_at: string;
  id: string;
  problem: string;
  related_item_ids?: string[];
  root_cause: string;
  run_id?: string;
  solution: string;
  source_ref?: string;
  source_type?: "manual" | "document-derived" | "autotest-derived";
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  title: string;
  updated_at: string;
}

export interface LogbookEntryUpdateRequest {
  problem?: string | null;
  related_item_ids?: string[] | null;
  root_cause?: string | null;
  solution?: string | null;
  source_ref?: string | null;
  source_type?: "manual" | "document-derived" | "autotest-derived" | null;
  status?: "draft" | "reviewed" | "verified" | "archived" | null;
  tags?: string | null;
  title?: string | null;
}

export interface LoginRequest {
  password: string;
  user_id: string;
}

export interface LoginResponse {
  access_token: string;
  token_type?: string;
}

export interface MeResponse {
  display_name: string;
  role: string;
  user_id: string;
}

export interface MessageResponse {
  message: string;
}

export interface PhotoResponse {
  created_at: string;
  description: string;
  file_size: number;
  filename: string;
  id: string;
  ocr_text: string;
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  updated_at: string;
  uploaded_by?: string | null;
}

export interface PhotoUpdateRequest {
  description?: string | null;
  status?: "draft" | "reviewed" | "verified" | "archived" | null;
  tags?: string | null;
}

export interface PromoteToKnowledgeResponse {
  knowledge_entry_id: string;
  message: string;
}

export interface QARequest {
  question: string;
}

export interface QAResponse {
  answer: string;
  sources?: Source[];
}

export interface ResolveItemsRequest {
  item_ids?: string[];
}

export interface ResolveItemsResponse {
  items?: ItemSummary[];
}

export interface SavedPromptCreateRequest {
  content: string;
  tags?: string;
  title: string;
}

export interface SavedPromptResponse {
  content: string;
  created_at: string;
  id: string;
  index_error?: string;
  index_status?: "indexed" | "failed" | "unavailable";
  tags: string;
  title: string;
  updated_at: string;
}

export interface SettingsLLMResponse {
  active_provider: string;
  base_url: string;
  error_message?: string;
  fallback_enabled: boolean;
  llm_ready_for_generation: boolean;
  model: string;
  primary_healthy: boolean;
  primary_provider: string;
}

export interface SettingsOCRResponse {
  available: boolean;
  details?: string;
  enabled: boolean;
  tesseract_cmd?: string;
  tesseract_version?: string;
}

export interface Source {
  location?: string | null;
  snippet: string;
  source_type: string;
  title: string;
}

export interface TemplateMetaItem {
  fields?: string[];
  label: string;
  value: string;
}

export interface TemplatesMetaResponse {
  templates?: TemplateMetaItem[];
}

export interface UploadDocumentResponse {
  category: string;
  file_size: number;
  filename: string;
  id: string;
  index_error?: string;
  index_status?: "pending" | "indexed" | "failed" | "unavailable";
  indexed_at?: string;
  message: string;
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  updated_at: string;
  uploaded_at: string;
  uploaded_by?: string | null;
}

export interface UploadPhotoResponse {
  created_at: string;
  description: string;
  file_size: number;
  filename: string;
  id: string;
  message: string;
  ocr_text: string;
  status?: "draft" | "reviewed" | "verified" | "archived";
  tags: string;
  updated_at: string;
  uploaded_by?: string | null;
}

export interface ValidationError {
  loc: string | number[];
  msg: string;
  type: string;
}
