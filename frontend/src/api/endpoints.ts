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
  },
  photos: {
    list: '/api/photos',
    upload: '/api/photos/upload',
    detail: (photoId: string) => `/api/photos/${photoId}`,
    download: (photoId: string) => `/api/photos/${photoId}/download`,
  },
  knowledge: {
    list: '/api/knowledge/entries',
    detail: (entryId: string) => `/api/knowledge/entries/${entryId}`,
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
