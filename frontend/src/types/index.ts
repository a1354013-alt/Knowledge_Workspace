/**
 * Frontend API contracts.
 *
 * Backend-shaped request/response types must come from the OpenAPI generator so
 * response_model changes fail frontend typecheck. UI-only state belongs in
 * adapters or local component types instead of being duplicated here.
 */

export type {
  AutoTestCapabilitiesResponse,
  AutoTestRunListItemResponse,
  AutoTestRunResponse,
  AutoTestStepResponse,
  AutoTestTimelineItemResponse,
  BulkImportResult,
  EmbeddingProviderStatusResponse,
  DashboardAutoTestMetrics,
  DashboardDocumentMetrics,
  DashboardHealthResponse,
  DashboardKnowledgeMetrics,
  DashboardLogbookMetrics,
  DashboardRecentActivity,
  DocumentResponse,
  DocumentUpdateRequest,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  IndexRebuildResponse,
  IndexStatusItemResponse,
  IndexStatusResponse,
  ItemLinkResolved,
  ItemLinksResponse,
  ItemSummary,
  KnowledgeBulkImportRequest,
  KnowledgeEntryCreateRequest,
  KnowledgeEntryPageResponse,
  KnowledgeEntryResponse,
  KnowledgeEntryUpdateRequest,
  KnowledgeImportRow,
  LogbookBulkImportRequest,
  LogbookEntryCreateRequest,
  LogbookEntryPageResponse,
  LogbookEntryResponse,
  LogbookEntryUpdateRequest,
  LogbookImportRow,
  LoginRequest,
  LoginResponse,
  MeResponse,
  MessageResponse,
  PhotoPageResponse,
  PhotoResponse,
  PhotoUpdateRequest,
  PromptBulkImportRequest,
  PromptImportRow,
  PromoteToKnowledgeResponse,
  QARequest,
  QAResponse,
  ResolveItemsRequest,
  ResolveItemsResponse,
  SavedPromptCreateRequest,
  SavedPromptPageResponse,
  SavedPromptResponse,
  SettingsLLMResponse,
  SettingsOCRResponse,
  Source,
  TemplateMetaItem,
  TemplatesMetaResponse,
  UploadDocumentResponse,
  UploadPhotoResponse,
} from '../api/generated/api-types'

import type {
  AutoTestRunResponse,
  AutoTestStepResponse,
  AutoTestTimelineItemResponse,
  DocumentResponse,
  KnowledgeEntryResponse,
} from '../api/generated/api-types'

export type KnowledgeStatus = NonNullable<KnowledgeEntryResponse['status']>
export type KnowledgeSourceType = NonNullable<KnowledgeEntryResponse['source_type']>
export type AutoTestRunStatus = AutoTestRunResponse['status']
export type AutoTestStepStatus = AutoTestStepResponse['status']
export type AutoTestTimelineStatus = AutoTestTimelineItemResponse['status']
export type AutoTestExportFormat = 'md' | 'html'
export type AutoTestExecutionMode = NonNullable<AutoTestRunResponse['execution_mode']>
export type DocumentIndexStatus = NonNullable<DocumentResponse['index_status']>

// API Error Structure is client-side normalized state, not a backend model.
export interface ApiError {
  status: number
  code?: string
  message: string
  details?: unknown
  detail?: string
}
