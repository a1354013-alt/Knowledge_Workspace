export const apiPaths = {
  auth: {
    login: '/api/login',
    me: '/api/me',
  },
  autotest: {
    capabilities: '/api/autotest/capabilities',
    listRuns: '/api/autotest/runs',
    run: '/api/autotest/run',
    detail: (runId: string) => `/api/autotest/runs/${runId}`,
    exportReport: (runId: string) => `/api/autotest/${runId}/export`,
  },
  docs: {
    list: '/api/docs',
    upload: '/api/docs/upload',
    detail: (docId: string) => `/api/docs/${docId}`,
    download: (docId: string) => `/api/docs/${docId}/download`,
    references: (docId: string) => `/api/docs/${docId}/references`,
  },
  photos: {
    list: '/api/photos',
    upload: '/api/photos/upload',
    detail: (photoId: string) => `/api/photos/${photoId}`,
    download: (photoId: string) => `/api/photos/${photoId}/download`,
    references: (photoId: string) => `/api/photos/${photoId}/references`,
  },
  knowledge: {
    list: '/api/knowledge/entries',
    detail: (entryId: string) => `/api/knowledge/entries/${entryId}`,
    revisions: (entryId: string) => `/api/knowledge/${entryId}/revisions`,
    revisionDiff: (entryId: string, revisionId: string) => `/api/knowledge/${entryId}/revisions/${revisionId}/diff`,
    restoreRevision: (entryId: string, revisionId: string) => `/api/knowledge/${entryId}/revisions/${revisionId}/restore`,
  },
  logbook: {
    list: '/api/logbook/entries',
    detail: (entryId: string) => `/api/logbook/entries/${entryId}`,
    promote: (entryId: string) => `/api/logbook/entries/${entryId}/promote-to-knowledge`,
  },
  prompts: {
    list: '/api/prompts',
    detail: (promptId: string) => `/api/prompts/${promptId}`,
  },
  import: {
    knowledge: '/api/import/knowledge',
    logbook: '/api/import/logbook',
    prompts: '/api/import/prompts',
  },
  search: {
    resolve: '/api/search',
    itemLinks: '/api/item-links',
  },
  qa: {
    ask: '/api/qa',
  },
  dashboard: {
    health: '/api/dashboard/health',
  },
  index: {
    status: '/api/index/status',
    rebuildAll: '/api/index/rebuild',
    rebuildItem: (itemType: string, itemId: string) => `/api/index/rebuild/${itemType}/${itemId}`,
  },
  settings: {
    llm: '/api/settings/llm',
    ocr: '/api/settings/ocr',
    templatesMeta: '/api/meta/templates',
  },
  generator: {
    generate: '/api/generate',
  },
} as const

export const API_TIMEOUT_MS = 30_000
export const API_UPLOAD_TIMEOUT_MS = 60_000
