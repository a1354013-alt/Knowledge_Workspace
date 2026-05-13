/**
 * Shared TypeScript interfaces for frontend-backend type safety.
 * These interfaces mirror the backend Pydantic models to ensure contract consistency.
 */

// User & Auth
export interface LoginRequest {
  user_id: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  user_id: string;
  role: string;
  display_name: string;
}

// QA & Search
export interface Source {
  source_type: string;
  title: string;
  location: string | null;
  snippet: string;
}

export interface QARequest {
  question: string;
}

export interface QAResponse {
  answer: string;
  sources: Source[];
}

// Generator templates
export interface TemplateMetaItem {
  value: string;
  label: string;
  fields: string[];
}

export interface TemplatesMetaResponse {
  templates: TemplateMetaItem[];
}

export interface GenerateRequest {
  template_type: string;
  inputs: Record<string, string>;
}

export interface GenerateResponse {
  content: string;
}

// Knowledge Entry
export type KnowledgeStatus = 'draft' | 'reviewed' | 'verified' | 'archived';
export type KnowledgeSourceType = 'manual' | 'document-derived' | 'autotest-derived';

export interface KnowledgeEntryCreateRequest {
  title: string;
  problem: string;
  root_cause: string;
  solution: string;
  tags: string;
  notes: string;
  status: KnowledgeStatus;
  source_type: KnowledgeSourceType;
  source_ref: string;
  related_item_ids: string[];
}

export interface KnowledgeEntryResponse {
  id: string;
  title: string;
  status: KnowledgeStatus;
  problem: string;
  root_cause: string;
  solution: string;
  tags: string;
  notes: string;
  source_type: KnowledgeSourceType;
  source_ref: string;
  related_item_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface KnowledgeEntryUpdateRequest {
  title?: string;
  status?: KnowledgeStatus;
  problem?: string;
  root_cause?: string;
  solution?: string;
  tags?: string;
  notes?: string;
  source_type?: KnowledgeSourceType;
  source_ref?: string;
  related_item_ids?: string[];
}

// Logbook Entry
export interface LogbookEntryCreateRequest {
  title: string;
  problem: string;
  root_cause: string;
  solution: string;
  tags: string;
  status: KnowledgeStatus;
  source_type: KnowledgeSourceType;
  source_ref: string;
  related_item_ids: string[];
}

export interface LogbookEntryResponse {
  id: string;
  title: string;
  status: KnowledgeStatus;
  run_id: string;
  problem: string;
  root_cause: string;
  solution: string;
  tags: string;
  source_type: KnowledgeSourceType;
  source_ref: string;
  related_item_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface LogbookEntryUpdateRequest {
  title?: string;
  status?: KnowledgeStatus;
  problem?: string;
  root_cause?: string;
  solution?: string;
  tags?: string;
  source_type?: KnowledgeSourceType;
  source_ref?: string;
  related_item_ids?: string[];
}

export interface PromoteToKnowledgeResponse {
  message: string;
  knowledge_entry_id: string;
}

// Document
export interface DocumentResponse {
  id: string;
  filename: string;
  category: string;
  tags: string;
  status: KnowledgeStatus;
  uploaded_at: string;
  updated_at: string;
  file_size: number;
  uploaded_by: string | null;
  index_status: 'pending' | 'indexed' | 'failed';
  index_error: string;
  indexed_at: string;
}

export interface DocumentUpdateRequest {
  category?: string;
  tags?: string;
  status?: KnowledgeStatus;
}

export interface UploadDocumentResponse extends DocumentResponse {
  message: string;
}

// Photo
export interface PhotoResponse {
  id: string;
  filename: string;
  tags: string;
  description: string;
  status: KnowledgeStatus;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
  file_size: number;
  ocr_text: string;
}

export interface PhotoUpdateRequest {
  tags?: string;
  description?: string;
  status?: KnowledgeStatus;
}

export interface UploadPhotoResponse extends PhotoResponse {
  message: string;
}

// AutoTest
export type AutoTestRunStatus = 'queued' | 'running' | 'passed' | 'failed';
export type AutoTestStepStatus = AutoTestRunStatus | 'skipped' | 'unavailable';
export type AutoTestExportFormat = 'md' | 'html';
export type AutoTestExecutionMode = 'real' | 'simulated';

export interface AutoTestCapabilitiesResponse {
  mode: AutoTestExecutionMode;
  real_mode_requested: boolean;
  real_mode_enabled: boolean;
  real_mode_available: boolean;
  message: string;
}

export interface AutoTestStepResponse {
  step_id: string;
  name: string;
  command: string;
  status: AutoTestStepStatus;
  started_at: string;
  finished_at: string;
  output: string;
  success: number;
  exit_code: number;
  stdout_summary: string;
  stderr_summary: string;
  error_type: string;
  created_at: string;
}

export interface AutoTestRunListItemResponse {
  id: string;
  project_name: string;
  status: AutoTestRunStatus;
  created_at: string;
  summary: string;
}

export type AutoTestTimelineStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

export interface AutoTestTimelineItemResponse {
  key: string;
  label: string;
  name: string;
  status: AutoTestTimelineStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  message: string | null;
}

export interface AutoTestRunResponse {
  id: string;
  source_type: string;
  source_ref: string;
  execution_mode: AutoTestExecutionMode;
  project_type_detected: string;
  working_directory: string;
  project_name: string;
  project_type: string;
  status: AutoTestRunStatus;
  summary: string;
  suggestion: string;
  prompt_output: string;
  failed_reason: string;
  problem_entry_id: string;
  solution_entry_id: string;
  created_at: string;
  steps: AutoTestStepResponse[];
  timeline: AutoTestTimelineItemResponse[];
}

// Saved Prompt
export interface SavedPromptCreateRequest {
  title: string;
  content: string;
  tags: string;
}

export interface SavedPromptResponse {
  id: string;
  title: string;
  content: string;
  tags: string;
  created_at: string;
  updated_at: string;
  index_status: 'indexed' | 'failed';
  index_error: string;
}

// Item Links & Relations
export interface ItemSummary {
  item_id: string;
  item_type: string;
  title: string;
  status: string;
  updated_at: string;
  created_at: string;
  source_type: string;
  source_ref: string;
}

export interface ItemLinkResolved {
  link_id: string;
  from_item_id: string;
  to_item_id: string;
  link_type: string;
  created_at: string;
  other_item: ItemSummary | null;
}

export interface ItemLinksResponse {
  item_id: string;
  links: ItemLinkResolved[];
}

export interface ResolveItemsRequest {
  item_ids: string[];
}

export interface ResolveItemsResponse {
  items: ItemSummary[];
}

// Dashboard
export interface DashboardKnowledgeMetrics {
  total: number;
  by_status: Record<string, number>;
}

export interface DashboardLogbookMetrics {
  total: number;
  with_solution: number;
  promoted_to_knowledge: number;
  resolution_rate: number;
}

export interface DashboardAutoTestMetrics {
  total_runs: number;
  passed: number;
  failed: number;
  pass_rate: number;
  recent_runs: AutoTestRunListItemResponse[];
}

export interface DashboardDocumentMetrics {
  total: number;
  indexed: number;
  pending: number;
  failed_documents: number;
  archived_documents: number;
}

export interface DashboardRecentActivity {
  days: number;
  documents_added: number;
  knowledge_added: number;
  logbook_added: number;
  autotest_runs: number;
  autotest_passed: number;
  autotest_failed: number;
}

export interface DashboardHealthResponse {
  knowledge: DashboardKnowledgeMetrics;
  logbook: DashboardLogbookMetrics;
  autotest: DashboardAutoTestMetrics;
  documents: DashboardDocumentMetrics;
  recent_activity: DashboardRecentActivity;
}

// Settings & Health
export interface HealthResponse {
  status: string;
  version: string;
}

export interface SettingsLLMResponse {
  primary_provider: string;
  active_provider: string;
  model: string;
  base_url: string;
  primary_healthy: boolean;
  fallback_enabled: boolean;
  llm_ready_for_generation: boolean;
  error_message: string;
}

export interface SettingsOCRResponse {
  enabled: boolean;
  available: boolean;
  tesseract_cmd: string;
  tesseract_version: string;
  details: string;
}

// Generic Response
export interface MessageResponse {
  message: string;
}

// API Error Structure
export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}
