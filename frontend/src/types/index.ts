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
  source_type: string;
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
  source_type: string;
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

export interface UploadPhotoResponse extends PhotoResponse {
  message: string;
}

// AutoTest
export interface AutoTestStepResponse {
  step_id: string;
  name: string;
  command: string;
  status: string;
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
  status: string;
  created_at: string;
  summary: string;
}

export interface AutoTestRunResponse {
  id: string;
  source_type: string;
  source_ref: string;
  execution_mode: 'real' | 'simulated';
  project_type_detected: string;
  working_directory: string;
  project_name: string;
  project_type: string;
  status: string;
  summary: string;
  suggestion: string;
  prompt_output: string;
  problem_entry_id: string;
  solution_entry_id: string;
  created_at: string;
  steps: AutoTestStepResponse[];
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

// Settings & Health
export interface HealthResponse {
  status: string;
  version: string;
}

export interface SettingsLLMResponse {
  provider: string;
  model: string;
  base_url: string;
  healthy: boolean;
  fallback_mode: boolean;
}

export interface SettingsOCRResponse {
  enabled: boolean;
  available: boolean;
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
