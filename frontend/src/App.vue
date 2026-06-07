<template>
  <div class="app-shell">
    <Toast />
    <AppConfirmDialog />

    <section
      v-if="!isLoggedIn"
      class="login-shell"
    >
      <Card class="login-card">
        <template #title>
          {{ t('app.title') }}
        </template>
        <template #subtitle>
          {{ t('app.subtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="login-actions">
              <div class="language-switch">
                <button
                  v-for="option in languageOptions"
                  :key="option.value"
                  type="button"
                  class="lang-btn"
                  :class="{ 'lang-btn-active': locale === option.value }"
                  @click="setLocale(option.value)"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>

            <label
              class="field-label"
              for="userId"
            >{{ t('auth.userId') }}</label>
            <InputText
              id="userId"
              v-model="loginForm.user_id"
              autocomplete="username"
            />

            <label
              class="field-label"
              for="password"
            >{{ t('auth.password') }}</label>
            <Password
              id="password"
              v-model="loginForm.password"
              :feedback="false"
              toggle-mask
              input-class="w-full"
            />

            <Button
              :label="t('auth.signIn')"
              :loading="loginLoading"
              @click="login"
            />
            <p class="muted-text">
              {{ t('app.providerHint') }}
            </p>
          </div>
        </template>
      </Card>
    </section>

    <section
      v-else
      class="workspace-layout"
    >
      <aside class="sidebar surface-card">
        <div class="sidebar-header">
          <p class="sidebar-eyebrow">
            {{ t('app.name') }}
          </p>
          <h1>{{ t('app.title') }}</h1>
        </div>

        <nav
          class="sidebar-nav"
          :aria-label="t('nav.aria')"
        >
          <section
            v-for="group in navGroups"
            :key="group.labelKey"
            class="sidebar-group"
          >
            <p class="sidebar-group-title">
              {{ t(group.labelKey) }}
            </p>
            <button
              v-for="tab in group.items"
              :key="tab.key"
              type="button"
              class="sidebar-link"
              :class="{ 'sidebar-link-active': tab.key === activeTabKey }"
              :aria-pressed="tab.key === activeTabKey"
              @click="selectTab(tab.key)"
              @mouseenter="tab.preload()"
              @focus="tab.preload()"
            >
              <i
                class="sidebar-link-icon pi"
                :class="tab.icon"
                aria-hidden="true"
              />
              <span>{{ t(tab.labelKey) }}</span>
            </button>
          </section>
        </nav>
      </aside>

      <div class="workspace-main">
        <header class="topbar surface-card">
          <div class="topbar-copy">
            <h2>{{ t('app.name') }}</h2>
            <p>{{ t('nav.owner') }}: {{ currentUser.display_name || '-' }}</p>
          </div>
          <div class="topbar-search">
            <InputText
              v-model="globalSearchText"
              :placeholder="t('app.globalSearchPlaceholder')"
              class="topbar-search-input"
              @keyup.enter="submitGlobalSearch"
            />
            <Button
              icon="pi pi-search"
              severity="secondary"
              outlined
              :aria-label="t('app.globalSearchAction')"
              @click="submitGlobalSearch"
            />
          </div>
          <div class="toolbar-actions">
            <div class="language-switch">
              <button
                v-for="option in languageOptions"
                :key="option.value"
                type="button"
                class="lang-btn"
                :class="{ 'lang-btn-active': locale === option.value }"
                @click="setLocale(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <Button
              :label="t('auth.logout')"
              severity="secondary"
              @click="logout()"
            />
          </div>
        </header>

        <main class="page-content">
          <Suspense>
            <component
              :is="activeTab.component"
              v-bind="activeTabProps"
            />
            <template #fallback>
              <div class="panel-loading">
                {{ t('app.loading') }}
              </div>
            </template>
          </Suspense>
        </main>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, markRaw, onBeforeUnmount, onMounted, ref, watch, type AsyncComponentLoader, type Component } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Toast from 'primevue/toast'

import { createInitialUser } from './app-state'
import { get, post } from './api'
import { apiPaths } from './api/endpoints'
import { clearToken, onUnauthorized, restoreToken, setToken } from './auth'
import { useI18n, type Locale } from './i18n'
import { useWorkspaceStore } from './workspace-store'
import { useWorkspaceNavigation } from './workspace-navigation'
import AppConfirmDialog from './components/AppConfirmDialog.vue'
import type { LoginRequest, LoginResponse, MeResponse } from './types'

type TabKey = import('./workspace-navigation').WorkspaceSectionKey

type LazyTab = {
  key: TabKey
  labelKey: string
  icon: string
  component: Component
  preload: AsyncComponentLoader<Component>
}

function lazyTab(key: TabKey, labelKey: string, icon: string, loader: AsyncComponentLoader<Component>): LazyTab {
  return {
    key,
    labelKey,
    icon,
    component: markRaw(defineAsyncComponent(loader)),
    preload: loader,
  }
}

const tabs: readonly LazyTab[] = [
  lazyTab('health', 'nav.health', 'pi-chart-line', () => import('./components/ProjectHealthDashboard.vue')),
  lazyTab('activity', 'nav.activity', 'pi-history', () => import('./components/ActivityDashboard.vue')),
  lazyTab('search', 'nav.search', 'pi-search', () => import('./components/GlobalSearchPanel.vue')),
  lazyTab('knowledge', 'nav.knowledge', 'pi-book', () => import('./components/KnowledgeBase.vue')),
  lazyTab('logbook', 'nav.logbook', 'pi-file-edit', () => import('./components/LogbookPanel.vue')),
  lazyTab('docsPhotos', 'nav.docsPhotos', 'pi-images', () => import('./components/DocsPhotosPanel.vue')),
  lazyTab('autotest', 'nav.autotest', 'pi-check-square', () => import('./components/AutoTestPanel.vue')),
  lazyTab('dataImport', 'nav.dataImport', 'pi-file-import', () => import('./components/DataImportPanel.vue')),
  lazyTab('prompts', 'nav.prompts', 'pi-comment', () => import('./components/PromptsPanel.vue')),
  lazyTab('generator', 'nav.generator', 'pi-sparkles', () => import('./components/TemplateGeneratorPanel.vue')),
  lazyTab('settings', 'nav.settings', 'pi-cog', () => import('./components/SettingsPanel.vue')),
]

const toast = useToast()
const { locale, setLocale, t } = useI18n()
const { activeSection, navigate, openSearch } = useWorkspaceNavigation()

const loginLoading = ref(false)
const currentUser = ref(createInitialUser())
const loginForm = ref<LoginRequest>({ user_id: '', password: '' })
const workspaceStore = useWorkspaceStore()
const activeTabKey = ref<TabKey>('health')
const globalSearchText = ref('')

const navGroups = [
  { labelKey: 'nav.sections.overview', items: tabs.filter((tab) => ['health', 'activity'].includes(tab.key)) },
  { labelKey: 'nav.sections.knowledgeManagement', items: tabs.filter((tab) => ['search', 'knowledge', 'logbook'].includes(tab.key)) },
  { labelKey: 'nav.sections.docsAndTesting', items: tabs.filter((tab) => ['docsPhotos', 'autotest', 'dataImport'].includes(tab.key)) },
  { labelKey: 'nav.sections.aiTools', items: tabs.filter((tab) => ['prompts', 'generator'].includes(tab.key)) },
  { labelKey: 'nav.sections.system', items: tabs.filter((tab) => ['settings'].includes(tab.key)) },
] as const

const languageOptions: { label: string; value: Locale }[] = [
  { label: '繁中', value: 'zh-TW' },
  { label: 'EN', value: 'en' },
]

const isLoggedIn = computed(() => Boolean(currentUser.value.user_id))
const activeTab = computed(() => tabs.find((tab) => tab.key === activeTabKey.value) ?? tabs[0])
const activeTabProps = computed(() => (activeTab.value.key === 'settings' ? { currentUser: currentUser.value } : {}))

function selectTab(tabKey: TabKey) {
  activeTabKey.value = tabKey
  navigate(tabKey)
  activeTab.value.preload()
}

function submitGlobalSearch() {
  openSearch(globalSearchText.value)
}

async function login() {
  if (!loginForm.value.user_id || !loginForm.value.password) {
    toast.add({ severity: 'warn', summary: t('auth.missingFields'), detail: t('auth.enterCredentials'), life: 3000 })
    return
  }

  loginLoading.value = true
  try {
    const response = await post<LoginResponse, LoginRequest>(apiPaths.auth.login, loginForm.value, { skipAuth: true })
    setToken(response.access_token)
    await bootstrapSession()
    toast.add({ severity: 'success', summary: t('auth.signedIn'), detail: t('auth.workspaceReady'), life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string; status?: number }
    toast.add({
      severity: 'error',
      summary: t('auth.loginFailed'),
      detail: apiError?.status === 401 ? t('auth.invalidCredentials') : apiError?.message || t('auth.loginFailed'),
      life: 4000,
    })
    if (apiError?.status === 401) {
      clearToken()
    }
  } finally {
    loginLoading.value = false
  }
}

function logout(showToast = true) {
  clearToken()
  currentUser.value = createInitialUser()
  loginForm.value = { user_id: '', password: '' }
  workspaceStore.reset()
  if (showToast) {
    toast.add({ severity: 'info', summary: t('auth.loggedOut'), detail: t('auth.sessionCleared'), life: 3000 })
  }
}

async function bootstrapSession() {
  const token = restoreToken()
  if (!token) {
    return
  }
  const me = await get<MeResponse>(apiPaths.auth.me)
  currentUser.value = me
}

const removeUnauthorizedListener = onUnauthorized((event) => {
  if (isLoggedIn.value) {
    toast.add({ severity: 'warn', summary: t('auth.sessionExpired'), detail: event.detail || t('auth.signInAgain'), life: 4000 })
  }
  logout(false)
})

onMounted(async () => {
  activeTab.value.preload()
  navigate(activeTabKey.value)
  try {
    await bootstrapSession()
  } catch (error: unknown) {
    const apiError = error as { status?: number }
    if (apiError?.status === 401) {
      clearToken()
    }
  }
})

onBeforeUnmount(() => {
  removeUnauthorizedListener()
})

watch(activeSection, (value) => {
  if (value !== activeTabKey.value) {
    activeTabKey.value = value
    activeTab.value.preload()
  }
})
</script>

<style scoped>
.app-shell {
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: radial-gradient(circle at top left, rgba(69, 138, 255, 0.22), transparent 52%),
    radial-gradient(circle at bottom right, rgba(0, 184, 148, 0.15), transparent 50%),
    linear-gradient(140deg, #f7f7fb 0%, #eef4ff 45%, #f5fff9 100%);
  box-sizing: border-box;
}

.login-shell {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  place-items: center;
  overflow: auto;
}

.login-card {
  width: min(520px, 100%);
}

.workspace-layout {
  display: flex;
  gap: 18px;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.sidebar {
  flex: 0 0 260px;
  min-height: 0;
  overflow: auto;
  padding: 18px;
}

.sidebar-header {
  margin-bottom: 18px;
}

.sidebar-header h1,
.topbar-copy h2,
.topbar-copy p {
  margin: 0;
}

.sidebar-eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #55708a;
}

.sidebar-header h1 {
  font-size: 1.1rem;
  line-height: 1.45;
  color: #16324a;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-group-title {
  margin: 0;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6c8194;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #244663;
  padding: 11px 12px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.sidebar-link:hover,
.sidebar-link:focus-visible {
  background: rgba(255, 255, 255, 0.82);
  transform: translateY(-1px);
  outline: none;
}

.sidebar-link-active {
  background: linear-gradient(135deg, rgba(39, 107, 209, 0.95), rgba(37, 163, 154, 0.92));
  color: #fff;
  box-shadow: 0 18px 32px rgba(41, 111, 185, 0.22);
}

.sidebar-link-icon {
  width: 1.1rem;
}

.workspace-main {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  flex: 0 0 auto;
}

.topbar-copy h2 {
  font-size: 1rem;
  color: #17324d;
}

.topbar-copy p {
  margin-top: 4px;
  color: #5e7488;
  font-size: 0.92rem;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.topbar-search {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 360px;
  justify-content: flex-end;
  min-width: 0;
}

.topbar-search-input {
  width: min(100%, 460px);
}

.language-switch {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(233, 241, 251, 0.95);
}

.lang-btn {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #33536d;
  padding: 6px 10px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

.lang-btn-active {
  background: #fff;
  color: #1b4d8e;
  box-shadow: 0 6px 12px rgba(31, 76, 132, 0.12);
}

.page-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-weight: 600;
}

.login-actions {
  display: flex;
  justify-content: flex-end;
}

.muted-text {
  margin: 0;
  color: #51606f;
  font-size: 13px;
}

.w-full {
  width: 100%;
}

@media (max-width: 720px) {
  .app-shell {
    padding: 14px;
  }

  .workspace-layout {
    flex-direction: column;
  }

  .sidebar {
    flex: 0 0 auto;
    overflow: auto hidden;
  }

  .sidebar-nav {
    flex-direction: row;
    align-items: flex-start;
    gap: 12px;
    min-width: max-content;
  }

  .sidebar-group {
    min-width: 190px;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .topbar-search {
    width: 100%;
    justify-content: stretch;
  }

  .topbar-search-input {
    flex: 1 1 auto;
    width: 100%;
  }
}

.panel-loading {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #51606f;
  font-size: 13px;
}
</style>
