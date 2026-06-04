import { readonly, ref } from 'vue'

export type Locale = 'zh-TW' | 'en'

const LOCALE_STORAGE_KEY = 'knowledge-workspace-locale'

const messages = {
  'zh-TW': {
    app: {
      name: '個人 AI 知識工作區',
      title: '工程師的個人 AI 知識工作區',
      subtitle: '收集解法、索引文件與截圖、用可追溯來源向 AI 提問，並將 AutoTest 結果回收成可重用的問題排查知識。',
      providerHint: '預設供應商：Ollama，可在後端設定 OLLAMA_BASE_URL / OLLAMA_MODEL。',
      language: '語言',
      loading: '載入中...',
    },
    auth: {
      userId: '使用者 ID',
      password: '密碼',
      signIn: '登入',
      logout: '登出',
      loginFailed: '登入失敗',
      invalidCredentials: '帳號或密碼錯誤。',
      signedIn: '已登入',
      workspaceReady: '工作區已就緒。',
      loggedOut: '已登出',
      sessionCleared: '工作階段已清除。',
      sessionExpired: '工作階段已過期',
      signInAgain: '請重新登入。',
      missingFields: '欄位未填',
      enterCredentials: '請輸入使用者 ID 與密碼。',
    },
    nav: {
      owner: '擁有者',
      health: '健康狀態',
      activity: '活動',
      search: '搜尋',
      knowledge: '知識庫',
      logbook: '問題紀錄本',
      docsPhotos: '文件與照片',
      autotest: '自動驗收測試',
      prompts: '提示詞庫',
      generator: '工程文件產生器',
      settings: '設定',
    },
    common: {
      refresh: '重新整理',
      save: '儲存',
      reset: '重設',
      run: '執行',
      chooseZip: '選擇 ZIP',
      generate: '產生文件',
      clearOutput: '清除結果',
      actions: '操作',
      title: '標題',
      tags: '標籤',
      updated: '更新時間',
      status: '狀態',
      created: '建立時間',
      project: '專案',
      saved: '已儲存',
      requestFailed: '請求失敗。',
      saveFailed: '儲存失敗',
    },
    prompts: {
      pageTitle: '提示詞庫',
      pageSubtitle: '儲存常用的 AI 工程提示詞，例如程式碼審查、錯誤 log 分析、PR 說明與測試失敗排查。',
      savedPrompts: '已儲存提示詞',
      savedSubtitle: '將重複的 AI 工作流模板化，讓 code review、debug、PR 文件與測試失敗分析更容易重用。',
      createPrompt: '建立提示詞',
      content: '提示詞內容',
      tagsPlaceholder: '標籤，以逗號分隔',
      filterPlaceholder: '依標題或標籤篩選',
      emptyTitle: '尚未建立提示詞。',
      emptyIntro: '你可以把常用的 AI 指令儲存在這裡，例如：',
      emptyCodeReview: '程式碼審查',
      emptyLogAnalysis: '錯誤 log 分析',
      emptyPrDescription: 'PR 說明產生',
      emptyTestDebug: '測試失敗排查',
      reloadFailed: '提示詞重新載入失敗',
      missingDetail: '標題與提示詞內容為必填。',
      savedDetail: '提示詞已儲存。',
      savedIndexUnavailable: '提示詞已儲存，但向量索引目前無法使用。',
      savedIndexFailed: '提示詞已儲存，但索引建立失敗。',
      deletePrompt: '刪除提示詞',
      deleteAccept: '刪除',
      deleteMessage: '要刪除「{title}」嗎？',
      deleted: '已刪除',
      deletedDetail: '提示詞已移除。',
      deleteFailed: '刪除失敗',
      copied: '已複製',
      copiedDetail: '提示詞已複製到剪貼簿。',
      copyFailed: '複製失敗',
      clipboardDenied: '剪貼簿權限被拒絕。',
    },
    autotest: {
      pageTitle: '自動驗收測試',
      pageSubtitle: '上傳專案壓縮檔，記錄安裝、建置、測試與 lint 結果，讓測試紀錄可以回收成可追蹤的工程知識。',
      runTitle: '執行驗收流程',
      runSubtitle: '安全模式是預設模式，不會直接執行上傳專案內的指令。Trusted local 與 Docker sandbox 可用於受控環境。',
      runner: 'AutoTest 執行器：{mode}',
      disabled: '已停用',
      localTrusted: 'Trusted local',
      dockerSandbox: 'Docker sandbox',
      simulated: '安全模擬',
      simulatedIntro: '目前為安全模擬模式，不會執行上傳專案內的命令。',
      simulatedRecords: '模擬模式會記錄結果格式，適合作品展示與流程驗證。',
      dockerStatus: 'Docker sandbox：{status}。',
      dockerReady: '可用',
      dockerBlocked: '已停用或未啟用',
      localTrustedWarning: 'Trusted local 會在本機執行上傳專案中的命令，僅適合受信任專案。',
      dockerActive: 'Docker sandbox 模式已啟用。',
      tip: '小提示：建議上傳較小的 ZIP；每個步驟都有逾時限制，結果會保存為可搜尋的結構化資料。',
      recentRuns: '最近執行紀錄',
      emptyTitle: '尚無測試紀錄。',
      emptyBody: '上傳專案 ZIP 後，系統會記錄安裝、建置、測試與 lint 的驗收結果。這些紀錄可以之後轉成問題排查筆記或知識庫資料。',
      reloadFailed: '重新載入失敗',
      noZipSelected: '尚未選擇 ZIP',
      chooseZipFirst: '請先選擇專案 ZIP。',
      runQueued: '執行已排入佇列',
      runCompleted: '執行完成',
      runFailed: '執行失敗',
      timeout: 'AutoTest 上傳或建立工作逾時。請檢查 ZIP 大小、網路連線或後端狀態；若工作已建立，可重新整理最近執行紀錄。',
    },
    generator: {
      pageTitle: '工程文件產生器',
      pageSubtitle: '使用範本快速產生 Bug Report、問題排查紀錄、PR 說明與 Postmortem 等工程文件。',
      cardTitle: '文件範本產生器',
      cardSubtitle: '透過範本產生工程文件，減少重複撰寫 Bug Report、Troubleshooting Note、PR Description 與 Postmortem 的時間。',
      refreshTemplates: '重新載入範本',
      chooseTemplate: '選擇文件範本...',
      selectPrompt: '請先選擇文件範本。',
      selectPromptDetail: '可產生 Bug Report、Troubleshooting Note、PR Description 或 Postmortem 等工程文件。',
      noTemplatesTitle: '尚無可用範本。',
      noTemplatesDetail: '請確認後端是否已初始化預設範本，或稍後重新整理。',
      output: '產生結果',
      loadFailed: '載入失敗',
      generateFailed: '產生失敗',
      noOutput: '沒有輸出',
      emptyOutput: '產生器回傳空內容。',
    },
  },
  en: {
    app: {
      name: 'Personal AI Knowledge Workspace',
      title: 'Personal AI Knowledge Workspace for Engineers',
      subtitle: 'Capture solutions, index docs & screenshots, ask AI with traceable sources, and recycle AutoTest results into reusable troubleshooting knowledge.',
      providerHint: 'Default provider: Ollama (configure OLLAMA_BASE_URL / OLLAMA_MODEL in backend).',
      language: 'Language',
      loading: 'Loading...',
    },
    auth: {
      userId: 'User ID',
      password: 'Password',
      signIn: 'Sign In',
      logout: 'Logout',
      loginFailed: 'Login failed',
      invalidCredentials: 'Invalid credentials.',
      signedIn: 'Signed in',
      workspaceReady: 'Workspace ready.',
      loggedOut: 'Logged out',
      sessionCleared: 'Session cleared.',
      sessionExpired: 'Session expired',
      signInAgain: 'Please sign in again.',
      missingFields: 'Missing fields',
      enterCredentials: 'Enter user ID and password.',
    },
    nav: {
      owner: 'Owner',
      health: 'Health',
      activity: 'Activity',
      search: 'Search',
      knowledge: 'Knowledge Base',
      logbook: 'Problem Logbook',
      docsPhotos: 'Documents & Photos',
      autotest: 'Auto Test',
      prompts: 'Prompts',
      generator: 'Generator',
      settings: 'Settings',
    },
    common: {
      refresh: 'Refresh',
      save: 'Save',
      reset: 'Reset',
      run: 'Run',
      chooseZip: 'Choose Zip',
      generate: 'Generate',
      clearOutput: 'Clear output',
      actions: 'Actions',
      title: 'Title',
      tags: 'Tags',
      updated: 'Updated',
      status: 'Status',
      created: 'Created',
      project: 'Project',
      saved: 'Saved',
      requestFailed: 'Request failed.',
      saveFailed: 'Save failed',
    },
    prompts: {
      pageTitle: 'Prompts',
      pageSubtitle: 'Store reusable AI engineering prompts for code review, error log analysis, PR descriptions, and test failure debugging.',
      savedPrompts: 'Saved prompts',
      savedSubtitle: 'Turn recurring AI workflows into templates for reviews, debugging, PR docs, and test failure analysis.',
      createPrompt: 'Create prompt',
      content: 'Prompt content',
      tagsPlaceholder: 'Tags (comma separated)',
      filterPlaceholder: 'Filter by title/tags',
      emptyTitle: 'No prompts yet.',
      emptyIntro: 'Save common AI instructions here, for example:',
      emptyCodeReview: 'Code review',
      emptyLogAnalysis: 'Error log analysis',
      emptyPrDescription: 'PR description generation',
      emptyTestDebug: 'Test failure debugging',
      reloadFailed: 'Prompts reload failed',
      missingDetail: 'Title and content are required.',
      savedDetail: 'Prompt saved.',
      savedIndexUnavailable: 'Prompt saved, but the vector index is unavailable.',
      savedIndexFailed: 'Prompt saved, but indexing failed.',
      deletePrompt: 'Delete prompt',
      deleteAccept: 'Delete',
      deleteMessage: 'Delete "{title}"?',
      deleted: 'Deleted',
      deletedDetail: 'Prompt removed.',
      deleteFailed: 'Delete failed',
      copied: 'Copied',
      copiedDetail: 'Prompt copied to clipboard.',
      copyFailed: 'Copy failed',
      clipboardDenied: 'Clipboard permission denied.',
    },
    autotest: {
      pageTitle: 'Auto Test',
      pageSubtitle: 'Upload a project ZIP and record install, build, test, and lint results so test history becomes traceable engineering knowledge.',
      runTitle: 'Run acceptance flow',
      runSubtitle: 'Safe mode is the default and does not execute commands inside uploaded projects. Trusted local and Docker sandbox are for controlled environments.',
      runner: 'AutoTest runner: {mode}',
      disabled: 'Disabled',
      localTrusted: 'Trusted local',
      dockerSandbox: 'Docker sandbox',
      simulated: 'Simulated',
      simulatedIntro: 'Safe simulation mode is active and will not execute commands from uploaded projects.',
      simulatedRecords: 'Simulation records the result format, suitable for portfolio demos and workflow validation.',
      dockerStatus: 'Docker sandbox: {status}.',
      dockerReady: 'ready',
      dockerBlocked: 'disabled or not enabled',
      localTrustedWarning: 'Trusted local mode runs commands from uploaded projects on this host. Use only with trusted projects.',
      dockerActive: 'Docker sandbox mode is active.',
      tip: 'Tip: keep zips small; steps have timeouts. Results are stored as structured data for later search.',
      recentRuns: 'Recent runs',
      emptyTitle: 'No test runs yet.',
      emptyBody: 'After uploading a project ZIP, the system records install, build, test, and lint acceptance results. These records can later become troubleshooting notes or knowledge base entries.',
      reloadFailed: 'Reload failed',
      noZipSelected: 'No zip selected',
      chooseZipFirst: 'Choose a project zip first.',
      runQueued: 'Run queued',
      runCompleted: 'Run completed',
      runFailed: 'Run failed',
      timeout: 'AutoTest upload or job creation timed out. Check the ZIP size, network connection, or backend status. If the job was created, refresh and review recent runs.',
    },
    generator: {
      pageTitle: 'Generator',
      pageSubtitle: 'Use templates to quickly generate engineering docs such as Bug Reports, Troubleshooting Notes, PR Descriptions, and Postmortems.',
      cardTitle: 'Template generator',
      cardSubtitle: 'Generate engineering documents from templates and reduce repeat writing for Bug Reports, Troubleshooting Notes, PR Descriptions, and Postmortems.',
      refreshTemplates: 'Refresh templates',
      chooseTemplate: 'Choose a template...',
      selectPrompt: 'Choose a document template first.',
      selectPromptDetail: 'You can generate Bug Reports, Troubleshooting Notes, PR Descriptions, or Postmortems.',
      noTemplatesTitle: 'No templates available.',
      noTemplatesDetail: 'Confirm the backend initialized default templates, or refresh again later.',
      output: 'Output',
      loadFailed: 'Load failed',
      generateFailed: 'Generate failed',
      noOutput: 'No output',
      emptyOutput: 'Generator returned empty content.',
    },
  },
} as const

type MessageTree = Record<string, unknown>

const locale = ref<Locale>(readInitialLocale())

function readInitialLocale(): Locale {
  const saved = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  return saved === 'en' || saved === 'zh-TW' ? saved : 'zh-TW'
}

function lookup(path: string, tree: MessageTree): string | undefined {
  let current: unknown = tree
  for (const segment of path.split('.')) {
    if (!current || typeof current !== 'object' || !(segment in current)) {
      return undefined
    }
    current = (current as Record<string, unknown>)[segment]
  }
  return typeof current === 'string' ? current : undefined
}

export function setLocale(nextLocale: Locale) {
  locale.value = nextLocale
  window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale)
  document.documentElement.lang = nextLocale
}

export function t(key: string, values?: Record<string, string | number>) {
  const template = lookup(key, messages[locale.value]) ?? lookup(key, messages.en) ?? key
  if (!values) {
    return template
  }
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(values[name] ?? `{${name}}`))
}

document.documentElement.lang = locale.value

export const currentLocale = readonly(locale)
export const locales: Locale[] = ['zh-TW', 'en']
