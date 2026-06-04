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
              {{ t('app.providerHint') }}
            </p>
          </div>
        </template>
      </Card>
    </section>

    <section
      v-else
      class="workspace-shell"
    >
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

      <main class="main-grid">
        <nav
          class="tab-strip"
          aria-label="Workspace sections"
        >
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-chip"
            :class="{ 'tab-chip-active': tab.key === activeTabKey }"
            :aria-pressed="tab.key === activeTabKey"
            @click="selectTab(tab.key)"
            @mouseenter="tab.preload()"
            @focus="tab.preload()"
          >
            {{ t(tab.labelKey) }}
          </button>
        </nav>

        <section class="tab-panel-shell">
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
        </section>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, markRaw, onBeforeUnmount, onMounted, ref, type AsyncComponentLoader, type Component } from 'vue'
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
import { currentLocale, setLocale, t, type Locale } from './i18n'
import { useWorkspaceStore } from './workspace-store'
import AppConfirmDialog from './components/AppConfirmDialog.vue'
import type { LoginRequest, LoginResponse, MeResponse } from './types'

type TabKey =
  | 'health'
  | 'activity'
  | 'search'
  | 'knowledge'
  | 'logbook'
  | 'docsPhotos'
  | 'autotest'
  | 'prompts'
  | 'generator'
  | 'settings'

type LazyTab = {
  key: TabKey
  labelKey: string
  component: Component
  preload: AsyncComponentLoader<Component>
}

function lazyTab(key: TabKey, labelKey: string, loader: AsyncComponentLoader<Component>): LazyTab {
  return {
    key,
    labelKey,
    component: markRaw(defineAsyncComponent(loader)),
    preload: loader,
  }
}

const tabs: readonly LazyTab[] = [
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
]

const toast = useToast()

const loginLoading = ref(false)
const currentUser = ref(createInitialUser())
const loginForm = ref<LoginRequest>({ user_id: '', password: '' })
const workspaceStore = useWorkspaceStore()
const activeTabKey = ref<TabKey>('health')

const isLoggedIn = computed(() => Boolean(currentUser.value.user_id))
const activeTab = computed(() => tabs.find((tab) => tab.key === activeTabKey.value) ?? tabs[0])
const activeTabProps = computed(() => (activeTab.value.key === 'settings' ? { currentUser: currentUser.value } : {}))

function selectTab(tabKey: TabKey) {
  activeTabKey.value = tabKey
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
    toast.add({ severity: 'error', summary: t('auth.loginFailed'), detail: apiError?.status === 401 ? t('auth.invalidCredentials') : apiError?.message || t('auth.loginFailed'), life: 4000 })
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
</script>

<style scoped>
.app-shell {
  height: 100dvh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: 24px;
  background: radial-gradient(circle at top left, rgba(69, 138, 255, 0.22), transparent 52%),
    radial-gradient(circle at bottom right, rgba(0, 184, 148, 0.15), transparent 50%),
    linear-gradient(140deg, #f7f7fb 0%, #eef4ff 45%, #f5fff9 100%);
}

.login-shell {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  display: grid;
  place-items: center;
}

.login-card {
  width: min(520px, 100%);
}

.workspace-shell {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.topbar {
  flex: 0 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
}

.topbar h1,
.topbar p {
  margin: 0;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
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
}

.tab-chip {
  border: 1px solid rgba(38, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2f46;
  border-radius: 999px;
  padding: 10px 14px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.tab-chip:hover,
.tab-chip:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.28);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.12);
  outline: none;
}

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
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-weight: 600;
}

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
    padding: 12px;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: space-between;
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
