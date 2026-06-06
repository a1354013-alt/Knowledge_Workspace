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
<<<<<<< HEAD
          {{ t('common.appNameLong') }}
        </template>
        <template #subtitle>
          {{ t('auth.subtitle') }}
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

=======
          {{ t('app.title') }}
        </template>
        <template #subtitle>
          {{ t('app.subtitle') }}
        </template>
        <template #content>
          <div class="stack-md">
            <div class="language-row">
              <label
                class="field-label"
                for="loginLocale"
              >{{ t('app.language') }}</label>
              <select
                id="loginLocale"
                class="locale-select"
                :value="currentLocale"
                @change="changeLocale"
              >
                <option value="zh-TW">
                  zh-TW
                </option>
                <option value="en">
                  en
                </option>
              </select>
            </div>
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
              :placeholder="t('auth.password')"
              :prompt-label="t('auth.password')"
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
<<<<<<< HEAD
              {{ t('auth.defaultProvider') }}
=======
              {{ t('app.providerHint') }}
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
            </p>
          </div>
        </template>
      </Card>
    </section>

    <section
      v-else
      class="workspace-layout"
    >
<<<<<<< HEAD
      <aside class="sidebar surface-card">
        <div class="sidebar-header">
          <p class="sidebar-eyebrow">
            {{ t('common.appName') }}
          </p>
          <h1>{{ t('common.appNameLong') }}</h1>
        </div>
=======
      <header class="topbar">
        <div>
          <h1>{{ t('app.name') }}</h1>
          <p>{{ t('nav.owner') }}: {{ currentUser.display_name }}</p>
        </div>
        <div class="toolbar-actions">
          <select
            class="locale-select"
            :aria-label="t('app.language')"
            :value="currentLocale"
            @change="changeLocale"
          >
            <option value="zh-TW">
              zh-TW
            </option>
            <option value="en">
              en
            </option>
          </select>
          <Button
            :label="t('auth.logout')"
            severity="secondary"
            @click="logout()"
          />
        </div>
      </header>
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71

        <nav
          class="sidebar-nav"
          :aria-label="t('nav.aria')"
        >
          <section
            v-for="group in navGroups"
            :key="group.labelKey"
            class="sidebar-group"
          >
<<<<<<< HEAD
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
=======
            {{ t(tab.labelKey) }}
          </button>
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
        </nav>
      </aside>

      <div class="workspace-main">
        <header class="topbar surface-card">
          <div class="topbar-copy">
            <h2>{{ t('common.appName') }}</h2>
            <p>{{ currentUser.display_name || t('common.owner') }}</p>
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
              :label="t('common.logout')"
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
<<<<<<< HEAD
                {{ t('common.loading') }}
=======
                {{ t('app.loading') }}
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
<<<<<<< HEAD
import { useI18n, type Locale } from './i18n'
=======
import { currentLocale, setLocale, t, type Locale } from './i18n'
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
import { useWorkspaceStore } from './workspace-store'
import { useWorkspaceNavigation } from './workspace-navigation'
import AppConfirmDialog from './components/AppConfirmDialog.vue'
import type { LoginRequest, LoginResponse, MeResponse } from './types'

type TabKey = import('./workspace-navigation').WorkspaceSectionKey

type LazyTab = {
  key: TabKey
  labelKey: string
<<<<<<< HEAD
  icon: string
=======
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
  component: Component
  preload: AsyncComponentLoader<Component>
}

<<<<<<< HEAD
function lazyTab(key: TabKey, labelKey: string, icon: string, loader: AsyncComponentLoader<Component>): LazyTab {
  return {
    key,
    labelKey,
    icon,
=======
function lazyTab(key: TabKey, labelKey: string, loader: AsyncComponentLoader<Component>): LazyTab {
  return {
    key,
    labelKey,
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
    component: markRaw(defineAsyncComponent(loader)),
    preload: loader,
  }
}

const tabs: readonly LazyTab[] = [
<<<<<<< HEAD
  lazyTab('health', 'nav.health', 'pi-chart-line', () => import('./components/ProjectHealthDashboard.vue')),
  lazyTab('activity', 'nav.activity', 'pi-history', () => import('./components/ActivityDashboard.vue')),
  lazyTab('search', 'nav.search', 'pi-search', () => import('./components/GlobalSearchPanel.vue')),
  lazyTab('knowledge', 'nav.knowledge', 'pi-book', () => import('./components/KnowledgeBase.vue')),
  lazyTab('logbook', 'nav.logbook', 'pi-file-edit', () => import('./components/LogbookPanel.vue')),
  lazyTab('docsPhotos', 'nav.docsPhotos', 'pi-images', () => import('./components/DocsPhotosPanel.vue')),
  lazyTab('autotest', 'nav.autotest', 'pi-check-square', () => import('./components/AutoTestPanel.vue')),
  lazyTab('prompts', 'nav.prompts', 'pi-comment', () => import('./components/PromptsPanel.vue')),
  lazyTab('generator', 'nav.generator', 'pi-sparkles', () => import('./components/TemplateGeneratorPanel.vue')),
  lazyTab('settings', 'nav.settings', 'pi-cog', () => import('./components/SettingsPanel.vue')),
=======
  lazyTab('health', 'nav.health', () => import('./components/ProjectHealthDashboard.vue')),
  lazyTab('activity', 'nav.activity', () => import('./components/ActivityDashboard.vue')),
  lazyTab('search', 'nav.search', () => import('./components/GlobalSearchPanel.vue')),
  lazyTab('knowledge', 'nav.knowledge', () => import('./components/KnowledgeBase.vue')),
  lazyTab('logbook', 'nav.logbook', () => import('./components/LogbookPanel.vue')),
  lazyTab('docsPhotos', 'nav.docsPhotos', () => import('./components/DocsPhotosPanel.vue')),
  lazyTab('autotest', 'nav.autotest', () => import('./components/AutoTestPanel.vue')),
  lazyTab('prompts', 'nav.prompts', () => import('./components/PromptsPanel.vue')),
  lazyTab('generator', 'nav.generator', () => import('./components/TemplateGeneratorPanel.vue')),
  lazyTab('settings', 'nav.settings', () => import('./components/SettingsPanel.vue')),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
]

const toast = useToast()
const { locale, setLocale, t } = useI18n()
const { activeSection, navigate } = useWorkspaceNavigation()

const loginLoading = ref(false)
const currentUser = ref(createInitialUser())
const loginForm = ref<LoginRequest>({ user_id: '', password: '' })
const workspaceStore = useWorkspaceStore()
const activeTabKey = ref<TabKey>('health')

const navGroups = [
  { labelKey: 'nav.sections.overview', items: tabs.filter((tab) => ['health', 'activity'].includes(tab.key)) },
  { labelKey: 'nav.sections.knowledgeManagement', items: tabs.filter((tab) => ['search', 'knowledge', 'logbook'].includes(tab.key)) },
  { labelKey: 'nav.sections.docsAndTesting', items: tabs.filter((tab) => ['docsPhotos', 'autotest'].includes(tab.key)) },
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

function changeLocale(event: Event) {
  const nextLocale = (event.target as HTMLSelectElement | null)?.value
  if (nextLocale === 'zh-TW' || nextLocale === 'en') {
    setLocale(nextLocale as Locale)
  }
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
<<<<<<< HEAD
    toast.add({ severity: 'error', summary: t('auth.loginFailed'), detail: apiError?.message || t('auth.invalidCredentials'), life: 4000 })
=======
    toast.add({ severity: 'error', summary: t('auth.loginFailed'), detail: apiError?.status === 401 ? t('auth.invalidCredentials') : apiError?.message || t('auth.loginFailed'), life: 4000 })
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
<<<<<<< HEAD
  height: 100dvh;
  overflow: hidden;
  padding: 20px;
=======
  height: 100%;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: 24px;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
  background: radial-gradient(circle at top left, rgba(69, 138, 255, 0.22), transparent 52%),
    radial-gradient(circle at bottom right, rgba(0, 184, 148, 0.15), transparent 50%),
    linear-gradient(140deg, #f7f7fb 0%, #eef4ff 45%, #f5fff9 100%);
  box-sizing: border-box;
}

.login-shell {
<<<<<<< HEAD
  height: 100%;
=======
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
  display: grid;
  place-items: center;
  padding-block: 8px;
}

.login-card {
  width: min(520px, 100%);
}

.workspace-shell {
<<<<<<< HEAD
}

.workspace-layout {
  display: flex;
  gap: 18px;
  height: 100%;
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
=======
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
  flex: 0 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
<<<<<<< HEAD
  padding: 14px 18px;
  flex: 0 0 auto;
=======
  padding: 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  min-width: 0;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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

.topbar h1 {
  font-size: clamp(1.25rem, 2vw, 1.75rem);
  line-height: 1.2;
}

.topbar p {
  overflow-wrap: anywhere;
}

.toolbar-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
<<<<<<< HEAD
  flex-wrap: wrap;
}

.language-switch {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
=======
  align-items: center;
}

.main-grid {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tab-strip {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
  min-width: 0;
}

.tab-chip {
  min-height: 42px;
  border: 1px solid rgba(38, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2f46;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
<<<<<<< HEAD
=======
  white-space: normal;
  overflow-wrap: anywhere;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
}

.lang-btn-active {
  background: #fff;
  color: #1b4d8e;
  box-shadow: 0 6px 12px rgba(31, 76, 132, 0.12);
}

<<<<<<< HEAD
.page-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
=======
.tab-chip-active {
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.22);
}

.tab-panel-shell {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  min-width: 0;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-weight: 600;
}

<<<<<<< HEAD
.login-actions {
  display: flex;
  justify-content: flex-end;
=======
.language-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.locale-select {
  min-height: 38px;
  padding: 8px 32px 8px 10px;
  border: 1px solid rgba(38, 63, 103, 0.18);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  color: #1f2f46;
  font: inherit;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
<<<<<<< HEAD
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
=======
    padding: 12px;
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
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
