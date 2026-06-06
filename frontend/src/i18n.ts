import { computed, ref } from 'vue'

export type Locale = 'zh-TW' | 'en'

type MessageValue = string | ((params?: Record<string, string | number>) => string)
interface MessageTree {
  [key: string]: MessageValue | MessageTree
}

const LOCALE_STORAGE_KEY = 'kw-locale'

const messages: Record<Locale, MessageTree> = {
  'zh-TW': {
    common: {
      appName: '個人工程知識工作台',
      appNameLong: '工程師個人 AI 知識工作台',
      owner: '擁有者',
      logout: '登出',
      loading: '載入中...',
      refresh: '重新整理',
      save: '儲存',
      reset: '重設',
      run: '執行',
      generate: '產生文件',
      clearOutput: '清除結果',
      search: '搜尋',
      settings: '設定',
      retry: '重試',
      clear: '清除',
      ask: '提問',
      close: '關閉',
      add: '加入',
      create: '建立',
      status: '狀態',
      actions: '操作',
      updated: '更新時間',
      created: '建立時間',
      title: '標題',
      tags: '標籤',
      source: '來源',
      detail: '詳細資訊',
      type: '類型',
      item: '項目',
      project: '專案',
      noData: '目前尚無資料',
      chooseZip: '選擇 ZIP',
      chooseDocument: '選擇文件',
      chooseImage: '選擇圖片',
      upload: '上傳',
      output: '輸出結果',
      language: '語言',
      zhTW: '繁中',
      en: 'English',
    },
    auth: {
      subtitle:
        '集中保存解法、索引文件與截圖，並把 AutoTest 結果回收成可追蹤的工程知識。',
      userId: '使用者 ID',
      password: '密碼',
      signIn: '登入',
      missingFields: '缺少欄位',
      enterCredentials: '請輸入使用者 ID 與密碼。',
      defaultProvider: '預設模型供應商：Ollama（請於後端設定 `OLLAMA_BASE_URL` / `OLLAMA_MODEL`）。',
      loginFailed: '登入失敗',
      invalidCredentials: '帳號或密碼無效。',
      signedIn: '已登入',
      workspaceReady: '工作台已準備完成。',
      loggedOut: '已登出',
      sessionCleared: '工作階段已清除。',
      sessionExpired: '登入已過期',
      signInAgain: '請重新登入。',
    },
    nav: {
      sections: {
        overview: '總覽',
        knowledgeManagement: '知識管理',
        docsAndTesting: '文件與測試',
        aiTools: 'AI 工具',
        system: '系統',
      },
      health: '總覽',
      activity: '活動紀錄',
      search: '搜尋',
      knowledge: '知識庫',
      logbook: '問題紀錄',
      docsPhotos: '文件與截圖',
      autotest: '自動驗收',
      prompts: '提示詞庫',
      generator: '文件產生器',
      settings: '設定',
      aria: '工作區導覽',
    },
    dashboard: {
      title: '專案健康儀表板',
      subtitle: '系統指標與近期活動總覽',
      empty: '目前還沒有可顯示的指標資料，先新增知識、文件或測試紀錄即可看到變化。',
      loading: '正在載入儀表板資料...',
      metrics: {
        knowledgeTotal: '知識總數',
        logbookResolutionRate: '問題解決率',
        autotestPassRate: 'AutoTest 通過率',
        documentIndexRate: '文件索引率',
        withSolution: ({ solved, total }: Record<string, string | number> = {}) => `${solved} / ${total} 已有解法`,
        passed: ({ passed, total }: Record<string, string | number> = {}) => `${passed} / ${total} 已通過`,
        indexed: ({ indexed, total }: Record<string, string | number> = {}) => `${indexed} / ${total} 已索引`,
      },
      status: {
        knowledgeByStatus: '知識狀態',
        documentIndexStatus: '文件索引狀態',
        indexed: '已索引',
        pending: '待處理',
        failed: '失敗',
        archived: '已封存',
      },
      recentRuns: {
        title: '最近 AutoTest 執行紀錄',
        emptyTitle: '尚無 AutoTest 執行紀錄',
        emptyDescription: '上傳專案 ZIP 後，系統會記錄安裝、建置、測試與 lint 結果。',
      },
      recentActivity: {
        title: '近 7 天活動',
        documentsAdded: '新增文件',
        knowledgeAdded: '新增知識',
        logbookAdded: '新增問題紀錄',
        autotestRuns: 'AutoTest 次數',
        autotestPassed: 'AutoTest 通過',
        autotestFailed: 'AutoTest 失敗',
      },
      gettingStarted: {
        title: '開始使用',
        description: '你可以從下列步驟開始建立自己的工程知識工作台。',
        steps: {
          logbook: {
            title: '新增一筆問題紀錄',
            description: '先記下問題、根因與解法，建立可搜尋的 troubleshooting 知識。',
            action: '前往問題紀錄',
          },
          documents: {
            title: '上傳文件或截圖',
            description: '把規格、錯誤截圖與操作文件集中進工作台，方便後續檢索。',
            action: '前往文件與截圖',
          },
          prompts: {
            title: '建立常用提示詞',
            description: '把程式碼審查、debug 與 PR 說明等重複流程模板化。',
            action: '前往提示詞庫',
          },
          autotest: {
            title: '執行一次自動驗收',
            description: '上傳專案 ZIP，留下 install、build、test 與 lint 的驗收紀錄。',
            action: '前往自動驗收',
          },
          generator: {
            title: '使用文件產生器整理工程紀錄',
            description: '快速產生 Bug Report、排查筆記與 Postmortem，完成作品展示脈絡。',
            action: '前往文件產生器',
          },
        },
      },
    },
    activity: {
      title: '活動紀錄',
      subtitle: '跨知識、問題紀錄、文件、圖片、提示詞與 AutoTest 的可追蹤時間軸。',
      filterPlaceholder: '依標題、類型、狀態或來源篩選',
      emptyTitle: '尚無活動紀錄',
      emptyDescription: '新增知識、上傳文件或執行 AutoTest 後，這裡會自動顯示近期動態。',
      itemKinds: {
        knowledge: '知識',
        logbook: '問題紀錄',
        document: '文件',
        photo: '圖片',
        autotest: 'AutoTest',
        prompt: '提示詞',
      },
      headers: {
        type: '類型',
        title: '標題',
        status: '狀態',
        source: '來源',
        when: '時間',
        item: '項目',
      },
    },
    search: {
      title: '搜尋',
      subtitle: '用關鍵字與篩選條件搜尋知識、問題紀錄、文件、圖片、提示詞與 AutoTest 紀錄。',
      keyword: '關鍵字...',
      types: '類型',
      status: '狀態',
      tagContains: '標籤包含...',
      dateFrom: '開始日期（YYYY-MM-DD）',
      dateTo: '結束日期（YYYY-MM-DD）',
      limit: '筆數上限',
      emptyTitle: '尚無搜尋結果',
      emptyDescription: '輸入關鍵字後開始搜尋；若目前還沒有資料，也可先從文件或問題紀錄開始建立。',
      searchFailed: '搜尋失敗',
    },
    knowledge: {
      askTitle: '知識問答',
      askSubtitle: '搜尋文件、知識筆記、問題紀錄與圖片中可追溯的工程資訊。',
      askPlaceholder: '例如：Delphi CRLF build fail、nginx 502 after deploy，或已知 workaround',
      answer: '回答',
      sources: '來源',
      recentNotes: '近期知識筆記',
      recentFilter: '依標題、標籤或狀態篩選',
      emptyTitle: '尚無知識筆記',
      emptyDescription: '先建立知識筆記或把問題紀錄升級成已驗證知識，之後就能在這裡搜尋與回顧。',
    },
    logbook: {
      title: '問題紀錄',
      subtitle: '集中保存你已處理過的工程問題，並可再整理成知識庫內容。',
      addEntry: '新增紀錄',
      emptyTitle: '尚無問題紀錄',
      emptyDescription: '從第一個 issue、錯誤 log 或排查流程開始記錄，之後就能逐步沉澱成可搜尋的工程知識。',
    },
    docsPhotos: {
      title: '文件與截圖',
      docsTitle: '文件',
      docsSubtitle: '上傳與標註工程文件，系統會在工作台內立即建立索引。',
      photosTitle: '截圖與圖片',
      photosSubtitle: '上傳圖片、加入標籤與描述，OCR 為可選且預設安全的輔助功能。',
      emptyDocsTitle: '尚無文件',
      emptyDocsDescription: '先上傳規格、報告或操作文件，之後就能在搜尋與知識問答中重複利用。',
      emptyPhotosTitle: '尚無截圖或圖片',
      emptyPhotosDescription: '把錯誤畫面、操作截圖或 UI 參考圖放進工作台，方便後續檢索與整理。',
    },
    prompts: {
      title: '提示詞庫',
      subtitle: '儲存常用的 AI 工程提示詞，例如程式碼審查、錯誤 log 分析、PR 說明與測試失敗排查。',
      listTitle: '已儲存提示詞',
      createTitle: '建立提示詞',
      filter: '依標題或標籤篩選',
      promptContent: '提示詞內容',
      tagsComma: '標籤，以逗號分隔',
      emptyTitle: '尚未建立提示詞',
      emptyDescription: '你可以把常用的 AI 指令儲存在這裡，例如程式碼審查、錯誤 log 分析、PR 說明與測試失敗排查。',
    },
    autotest: {
      title: '自動驗收測試',
      subtitle: '上傳專案壓縮檔，記錄安裝、建置、測試與 lint 結果，讓測試紀錄可以回收成可追蹤的工程知識。',
      runTitle: '執行驗收流程',
      safeModeDescription: '安全模式是預設模式，不會直接執行上傳專案內的指令。Trusted local 與 Docker sandbox 可用於受控環境。',
      runnerDisabled: 'AutoTest 執行器：已停用',
      simulatedMode: '目前為安全模擬模式，不會執行上傳專案內的命令。',
      simulatedFormat: '模擬模式會記錄結果格式，適合作品展示與流程驗證。',
      dockerDisabled: 'Docker sandbox：已停用或未啟用。',
      recentRuns: '最近執行紀錄',
      emptyTitle: '尚無測試紀錄',
      emptyDescription: '上傳專案 ZIP 後，系統會記錄驗收結果，之後可回收成問題排查筆記或知識庫資料。',
      noZip: '尚未選擇 ZIP',
      chooseZipFirst: '請先選擇專案 ZIP。',
    },
    generator: {
      title: '工程文件產生器',
      subtitle: '使用範本快速產生 Bug Report、問題排查紀錄、PR 說明與 Postmortem 等工程文件。',
      panelTitle: '文件範本產生器',
      refreshTemplates: '重新載入範本',
      chooseTemplate: '選擇文件範本...',
      emptyTitle: '請先選擇文件範本',
      emptyDescription: '可產生 Bug Report、Troubleshooting Note、PR Description 或 Postmortem 等工程文件。',
      noTemplatesTitle: '尚無可用範本',
      noTemplatesDescription: '請確認後端是否已初始化預設範本，或稍後重新整理。',
      noOutput: '產生器回傳空內容。',
    },
    settings: {
      title: '設定',
    },
    statusLabels: {
      draft: '草稿',
      reviewed: '已檢閱',
      verified: '已驗證',
      archived: '已封存',
      indexed: '已索引',
      pending: '待處理',
      failed: '失敗',
      passed: '已通過',
      queued: '排隊中',
      running: '執行中',
      completed: '已完成',
      saved: '已儲存',
      disabled: '已停用',
      localTrusted: 'Trusted local',
      dockerSandbox: 'Docker sandbox',
    },
  },
  en: {
    common: {
      appName: 'Personal AI Knowledge Workspace',
      appNameLong: 'Personal AI Knowledge Workspace for Engineers',
      owner: 'Owner',
      logout: 'Logout',
      loading: 'Loading...',
      refresh: 'Refresh',
      save: 'Save',
      reset: 'Reset',
      run: 'Run',
      generate: 'Generate',
      clearOutput: 'Clear output',
      search: 'Search',
      settings: 'Settings',
      retry: 'Retry',
      clear: 'Clear',
      ask: 'Ask',
      close: 'Close',
      add: 'Add',
      create: 'Create',
      status: 'Status',
      actions: 'Actions',
      updated: 'Updated',
      created: 'Created',
      title: 'Title',
      tags: 'Tags',
      source: 'Source',
      detail: 'Detail',
      type: 'Type',
      item: 'Item',
      project: 'Project',
      noData: 'No data yet',
      chooseZip: 'Choose Zip',
      chooseDocument: 'Choose Document',
      chooseImage: 'Choose Image',
      upload: 'Upload',
      output: 'Output',
      language: 'Language',
      zhTW: '繁中',
      en: 'English',
    },
    auth: {
      subtitle:
        'Capture solutions, index docs and screenshots, and recycle AutoTest results into reusable engineering knowledge.',
      userId: 'User ID',
      password: 'Password',
      signIn: 'Sign In',
      missingFields: 'Missing fields',
      enterCredentials: 'Enter user ID and password.',
      defaultProvider: 'Default provider: Ollama (configure `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in backend).',
      loginFailed: 'Login failed',
      invalidCredentials: 'Invalid credentials.',
      signedIn: 'Signed in',
      workspaceReady: 'Workspace ready.',
      loggedOut: 'Logged out',
      sessionCleared: 'Session cleared.',
      sessionExpired: 'Session expired',
      signInAgain: 'Please sign in again.',
    },
    nav: {
      sections: {
        overview: 'Overview',
        knowledgeManagement: 'Knowledge Management',
        docsAndTesting: 'Docs & Testing',
        aiTools: 'AI Tools',
        system: 'System',
      },
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
      aria: 'Workspace navigation',
    },
    dashboard: {
      title: 'Project Health Dashboard',
      subtitle: 'System-wide metrics and recent activity overview',
      empty: 'No metrics are available yet. Start by adding knowledge, uploading docs, or running AutoTest.',
      loading: 'Loading dashboard metrics...',
      metrics: {
        knowledgeTotal: 'Knowledge Total',
        logbookResolutionRate: 'Logbook Resolution Rate',
        autotestPassRate: 'AutoTest Pass Rate',
        documentIndexRate: 'Document Index Rate',
        withSolution: ({ solved, total }: Record<string, string | number> = {}) => `${solved} / ${total} with solution`,
        passed: ({ passed, total }: Record<string, string | number> = {}) => `${passed} / ${total} passed`,
        indexed: ({ indexed, total }: Record<string, string | number> = {}) => `${indexed} / ${total} indexed`,
      },
      status: {
        knowledgeByStatus: 'Knowledge by Status',
        documentIndexStatus: 'Document Index Status',
        indexed: 'Indexed',
        pending: 'Pending',
        failed: 'Failed',
        archived: 'Archived',
      },
      recentRuns: {
        title: 'Recent AutoTest Runs',
        emptyTitle: 'No recent AutoTest runs',
        emptyDescription: 'After you upload a project ZIP, install, build, test, and lint results will appear here.',
      },
      recentActivity: {
        title: 'Last 7 Days Activity',
        documentsAdded: 'Documents Added',
        knowledgeAdded: 'Knowledge Added',
        logbookAdded: 'Logbook Added',
        autotestRuns: 'AutoTest Runs',
        autotestPassed: 'AutoTest Passed',
        autotestFailed: 'AutoTest Failed',
      },
      gettingStarted: {
        title: 'Getting started',
        description: 'Use these steps to build your own engineering knowledge workspace.',
        steps: {
          logbook: {
            title: 'Add a problem log entry',
            description: 'Capture the issue, root cause, and solution so it becomes searchable troubleshooting knowledge.',
            action: 'Open Problem Logbook',
          },
          documents: {
            title: 'Upload docs or screenshots',
            description: 'Centralize specs, screenshots, and operational notes so they can be reused later.',
            action: 'Open Documents & Photos',
          },
          prompts: {
            title: 'Save reusable prompts',
            description: 'Template recurring workflows like code reviews, debugging, and PR explanations.',
            action: 'Open Prompts',
          },
          autotest: {
            title: 'Run AutoTest once',
            description: 'Upload a project ZIP and keep a record of install, build, test, and lint results.',
            action: 'Open Auto Test',
          },
          generator: {
            title: 'Use the document generator',
            description: 'Produce Bug Reports, troubleshooting notes, and postmortems to complete the showcase flow.',
            action: 'Open Generator',
          },
        },
      },
    },
    activity: {
      title: 'Recent activity',
      subtitle: 'A traceable timeline across knowledge, logbook, documents, photos, prompts, and AutoTest runs.',
      filterPlaceholder: 'Filter by title, type, status, or source',
      emptyTitle: 'No activity yet',
      emptyDescription: 'Once you add knowledge, upload files, or run AutoTest, recent changes will show up here.',
      itemKinds: {
        knowledge: 'Knowledge',
        logbook: 'Logbook',
        document: 'Document',
        photo: 'Photo',
        autotest: 'AutoTest',
        prompt: 'Prompt',
      },
      headers: {
        type: 'Type',
        title: 'Title',
        status: 'Status',
        source: 'Source',
        when: 'When',
        item: 'Item',
      },
    },
    search: {
      title: 'Global search',
      subtitle: 'Keyword and filter search across knowledge, logbook, documents, photos, prompts, and AutoTest runs.',
      keyword: 'Keyword...',
      types: 'Types',
      status: 'Status',
      tagContains: 'Tag contains...',
      dateFrom: 'Date from (YYYY-MM-DD)',
      dateTo: 'Date to (YYYY-MM-DD)',
      limit: 'Limit',
      emptyTitle: 'No search results yet',
      emptyDescription: 'Run a search to see results here. If your workspace is still empty, start with documents or logbook entries.',
      searchFailed: 'Search failed',
    },
    knowledge: {
      askTitle: 'Ask your knowledge',
      askSubtitle: 'Search across your documents, knowledge notes, logbook entries, and image metadata.',
      askPlaceholder: 'e.g. Delphi CRLF build fail, nginx 502 after deploy, or a known workaround',
      answer: 'Answer',
      sources: 'Sources',
      recentNotes: 'Recent notes',
      recentFilter: 'Filter recent notes by title, tags, or status',
      emptyTitle: 'No knowledge notes yet',
      emptyDescription: 'Create a note or promote a solved logbook entry to verified knowledge to build the base layer.',
    },
    logbook: {
      title: 'Engineering troubleshooting logbook',
      subtitle: 'First-class module for problems you solved. Fully searchable via Knowledge Base.',
      addEntry: 'Add entry',
      emptyTitle: 'No logbook entries yet',
      emptyDescription: 'Start with your first bug, incident, or fix note. Over time this becomes reusable engineering knowledge.',
    },
    docsPhotos: {
      title: 'Documents & Photos',
      docsTitle: 'Documents',
      docsSubtitle: 'Upload and tag engineering docs. Indexing happens immediately for your workspace.',
      photosTitle: 'Photos / Images',
      photosSubtitle: 'Upload images, add tags and descriptions. OCR is optional and safe-by-default.',
      emptyDocsTitle: 'No documents yet',
      emptyDocsDescription: 'Upload specs, reports, or operational docs to make them searchable inside the workspace.',
      emptyPhotosTitle: 'No screenshots or images yet',
      emptyPhotosDescription: 'Save failure screenshots, UI captures, or references so they can support later troubleshooting.',
    },
    prompts: {
      title: 'Prompts',
      subtitle: 'Save reusable AI engineering prompts for code reviews, debugging, PR descriptions, and test failure analysis.',
      listTitle: 'Saved prompts',
      createTitle: 'Create prompt',
      filter: 'Filter by title/tags',
      promptContent: 'Prompt content',
      tagsComma: 'Tags (comma separated)',
      emptyTitle: 'No prompts yet',
      emptyDescription: 'Store recurring AI instructions here, such as code review, log analysis, PR descriptions, or failed test triage.',
    },
    autotest: {
      title: 'Auto Test',
      subtitle: 'Upload a project ZIP and record install, build, test, and lint results so the history can be reused as engineering knowledge.',
      runTitle: 'Run acceptance flow',
      safeModeDescription: 'Safe mode is the default and does not directly execute commands from uploaded projects. Trusted local and Docker sandbox are for controlled environments.',
      runnerDisabled: 'AutoTest runner: Disabled',
      simulatedMode: 'Safe simulated mode is active, so uploaded project commands are not executed.',
      simulatedFormat: 'Simulation still records the result format and is suitable for demos and flow verification.',
      dockerDisabled: 'Docker sandbox: Disabled or not enabled.',
      recentRuns: 'Recent runs',
      emptyTitle: 'No test runs yet',
      emptyDescription: 'After you upload a project ZIP, acceptance results will be recorded here and can be recycled into troubleshooting notes or knowledge entries.',
      noZip: 'No ZIP selected',
      chooseZipFirst: 'Choose a project ZIP first.',
    },
    generator: {
      title: 'Engineering document generator',
      subtitle: 'Use templates to quickly produce Bug Reports, troubleshooting notes, PR descriptions, and postmortems.',
      panelTitle: 'Template generator',
      refreshTemplates: 'Refresh templates',
      chooseTemplate: 'Choose a template...',
      emptyTitle: 'Choose a template first',
      emptyDescription: 'Generate Bug Reports, Troubleshooting Notes, PR Descriptions, or Postmortems from the available templates.',
      noTemplatesTitle: 'No templates available',
      noTemplatesDescription: 'Confirm that the backend initialized the default templates, or refresh again later.',
      noOutput: 'Generator returned empty content.',
    },
    settings: {
      title: 'Settings',
    },
    statusLabels: {
      draft: 'Draft',
      reviewed: 'Reviewed',
      verified: 'Verified',
      archived: 'Archived',
      indexed: 'Indexed',
      pending: 'Pending',
      failed: 'Failed',
      passed: 'Passed',
      queued: 'Queued',
      running: 'Running',
      completed: 'Completed',
      saved: 'Saved',
      disabled: 'Disabled',
      localTrusted: 'Local trusted',
      dockerSandbox: 'Docker sandbox',
    },
  },
}

const locale = ref<Locale>(readInitialLocale())

function readInitialLocale(): Locale {
  if (typeof window === 'undefined') {
    return 'zh-TW'
  }
  const saved = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  return saved === 'en' || saved === 'zh-TW' ? saved : 'zh-TW'
}

function resolveMessage(localeValue: Locale, key: string): MessageValue | undefined {
  return key.split('.').reduce<MessageValue | MessageTree | undefined>((current, segment) => {
    if (!current || typeof current === 'string' || typeof current === 'function') {
      return undefined
    }
    return current[segment] as MessageValue | MessageTree | undefined
  }, messages[localeValue]) as MessageValue | undefined
}

function interpolate(template: string, params?: Record<string, string | number>) {
  if (!params) {
    return template
  }
  return template.replace(/\{(\w+)\}/g, (_, token: string) => String(params[token] ?? ''))
}

export function setLocale(nextLocale: Locale) {
  locale.value = nextLocale
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale)
  }
}

export function useI18n() {
  const currentLocale = computed(() => locale.value)

  function t(key: string, params?: Record<string, string | number>) {
    const message = resolveMessage(locale.value, key) ?? resolveMessage('en', key)
    if (typeof message === 'function') {
      return message(params)
    }
    if (typeof message === 'string') {
      return interpolate(message, params)
    }
    return key
  }

  return {
    locale: currentLocale,
    setLocale,
    t,
  }
}

export function translateStatusLabel(value: string) {
  const { t } = useI18n()
  const keyMap: Record<string, string> = {
    draft: 'statusLabels.draft',
    reviewed: 'statusLabels.reviewed',
    verified: 'statusLabels.verified',
    archived: 'statusLabels.archived',
    indexed: 'statusLabels.indexed',
    pending: 'statusLabels.pending',
    failed: 'statusLabels.failed',
    passed: 'statusLabels.passed',
    queued: 'statusLabels.queued',
    running: 'statusLabels.running',
    completed: 'statusLabels.completed',
    saved: 'statusLabels.saved',
    disabled: 'statusLabels.disabled',
    local_trusted: 'statusLabels.localTrusted',
    docker_sandbox: 'statusLabels.dockerSandbox',
  }
  const key = keyMap[String(value || '').trim()]
  return key ? t(key) : value
}
