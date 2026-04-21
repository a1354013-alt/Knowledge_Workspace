import { computed, reactive } from 'vue'
import { get } from './api'
import type {
  AutoTestRunListItemResponse,
  DocumentResponse,
  KnowledgeEntryResponse,
  LogbookEntryResponse,
  SavedPromptResponse,
  PhotoResponse,
} from './types'

type LoadState = 'idle' | 'loading' | 'ready' | 'error'

type WorkspaceLists = {
  documents: DocumentResponse[]
  photos: PhotoResponse[]
  knowledgeEntries: KnowledgeEntryResponse[]
  logbookEntries: LogbookEntryResponse[]
  autotestRuns: AutoTestRunListItemResponse[]
  prompts: SavedPromptResponse[]
}

type WorkspaceStore = {
  state: {
    lists: WorkspaceLists
    status: Record<keyof WorkspaceLists, LoadState>
    error: Record<keyof WorkspaceLists, string>
    lastLoadedAt: Record<keyof WorkspaceLists, number>
  }
  anyLoading: Readonly<{ value: boolean }>
  reset(): void
  refreshAll(opts?: { force?: boolean }): Promise<void>
  refreshDocuments(opts?: { force?: boolean }): Promise<void>
  refreshPhotos(opts?: { force?: boolean }): Promise<void>
  refreshKnowledgeEntries(opts?: { force?: boolean }): Promise<void>
  refreshLogbookEntries(opts?: { force?: boolean }): Promise<void>
  refreshAutotestRuns(opts?: { force?: boolean }): Promise<void>
  refreshPrompts(opts?: { force?: boolean }): Promise<void>
}

const CACHE_TTL_MS = 30_000

function createEmptyLists(): WorkspaceLists {
  return {
    documents: [],
    photos: [],
    knowledgeEntries: [],
    logbookEntries: [],
    autotestRuns: [],
    prompts: [],
  }
}

function createBlankErrors(): Record<keyof WorkspaceLists, string> {
  return {
    documents: '',
    photos: '',
    knowledgeEntries: '',
    logbookEntries: '',
    autotestRuns: '',
    prompts: '',
  }
}

function createBlankStatus(): Record<keyof WorkspaceLists, LoadState> {
  return {
    documents: 'idle',
    photos: 'idle',
    knowledgeEntries: 'idle',
    logbookEntries: 'idle',
    autotestRuns: 'idle',
    prompts: 'idle',
  }
}

function createBlankLoadedAt(): Record<keyof WorkspaceLists, number> {
  return {
    documents: 0,
    photos: 0,
    knowledgeEntries: 0,
    logbookEntries: 0,
    autotestRuns: 0,
    prompts: 0,
  }
}

function nowMs() {
  return Date.now()
}

function shouldUseCache(lastLoadedAt: number, force?: boolean) {
  if (force) {
    return false
  }
  if (!lastLoadedAt) {
    return false
  }
  return nowMs() - lastLoadedAt < CACHE_TTL_MS
}

let singleton: WorkspaceStore | null = null

export function useWorkspaceStore(): WorkspaceStore {
  if (singleton) {
    return singleton
  }

  const lists = reactive<WorkspaceLists>(createEmptyLists())
  const status = reactive<Record<keyof WorkspaceLists, LoadState>>(createBlankStatus())
  const error = reactive<Record<keyof WorkspaceLists, string>>(createBlankErrors())
  const lastLoadedAt = reactive<Record<keyof WorkspaceLists, number>>(createBlankLoadedAt())

  async function refreshOne<K extends keyof WorkspaceLists>(
    key: K,
    loader: () => Promise<WorkspaceLists[K]>,
    opts?: { force?: boolean }
  ) {
    if (shouldUseCache(lastLoadedAt[key], opts?.force)) {
      return
    }
    status[key] = 'loading'
    error[key] = ''
    try {
      const data = await loader()
      lists[key] = Array.isArray(data) ? (data as WorkspaceLists[K]) : ([] as unknown as WorkspaceLists[K])
      status[key] = 'ready'
      lastLoadedAt[key] = nowMs()
    } catch (err: unknown) {
      status[key] = 'error'
      error[key] = (err as { message?: string })?.message || 'Request failed.'
      lists[key] = [] as unknown as WorkspaceLists[K]
    }
  }

  async function refreshDocuments(opts?: { force?: boolean }) {
    await refreshOne('documents', () => get<DocumentResponse[]>('/api/docs'), opts)
  }

  async function refreshPhotos(opts?: { force?: boolean }) {
    await refreshOne('photos', () => get<PhotoResponse[]>('/api/photos'), opts)
  }

  async function refreshKnowledgeEntries(opts?: { force?: boolean }) {
    await refreshOne('knowledgeEntries', () => get<KnowledgeEntryResponse[]>('/api/knowledge/entries'), opts)
  }

  async function refreshLogbookEntries(opts?: { force?: boolean }) {
    await refreshOne('logbookEntries', () => get<LogbookEntryResponse[]>('/api/logbook/entries'), opts)
  }

  async function refreshAutotestRuns(opts?: { force?: boolean }) {
    await refreshOne('autotestRuns', () => get<AutoTestRunListItemResponse[]>('/api/autotest/runs'), opts)
  }

  async function refreshPrompts(opts?: { force?: boolean }) {
    await refreshOne('prompts', () => get<SavedPromptResponse[]>('/api/prompts'), opts)
  }

  async function refreshAll(opts?: { force?: boolean }) {
    const force = opts?.force
    await Promise.all([
      refreshDocuments({ force }),
      refreshPhotos({ force }),
      refreshKnowledgeEntries({ force }),
      refreshLogbookEntries({ force }),
      refreshAutotestRuns({ force }),
      refreshPrompts({ force }),
    ])
  }

  function reset() {
    const empty = createEmptyLists()
    lists.documents = empty.documents
    lists.photos = empty.photos
    lists.knowledgeEntries = empty.knowledgeEntries
    lists.logbookEntries = empty.logbookEntries
    lists.autotestRuns = empty.autotestRuns
    lists.prompts = empty.prompts

    const blankStatus = createBlankStatus()
    status.documents = blankStatus.documents
    status.photos = blankStatus.photos
    status.knowledgeEntries = blankStatus.knowledgeEntries
    status.logbookEntries = blankStatus.logbookEntries
    status.autotestRuns = blankStatus.autotestRuns
    status.prompts = blankStatus.prompts

    const blankErrors = createBlankErrors()
    error.documents = blankErrors.documents
    error.photos = blankErrors.photos
    error.knowledgeEntries = blankErrors.knowledgeEntries
    error.logbookEntries = blankErrors.logbookEntries
    error.autotestRuns = blankErrors.autotestRuns
    error.prompts = blankErrors.prompts

    const blankLoaded = createBlankLoadedAt()
    lastLoadedAt.documents = blankLoaded.documents
    lastLoadedAt.photos = blankLoaded.photos
    lastLoadedAt.knowledgeEntries = blankLoaded.knowledgeEntries
    lastLoadedAt.logbookEntries = blankLoaded.logbookEntries
    lastLoadedAt.autotestRuns = blankLoaded.autotestRuns
    lastLoadedAt.prompts = blankLoaded.prompts
  }

  const anyLoading = computed(() => Object.values(status).some((value) => value === 'loading'))

  singleton = {
    state: { lists, status, error, lastLoadedAt },
    anyLoading,
    reset,
    refreshAll,
    refreshDocuments,
    refreshPhotos,
    refreshKnowledgeEntries,
    refreshLogbookEntries,
    refreshAutotestRuns,
    refreshPrompts,
  }

  return singleton
}
