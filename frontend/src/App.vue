<template>
  <div class="app-shell">
    <Toast />

    <section
      v-if="!isLoggedIn"
      class="login-shell"
    >
      <Card class="login-card">
        <template #title>
          Personal AI Knowledge Workspace for Engineers
        </template>
        <template #subtitle>
          Capture solutions, index docs & screenshots, ask AI with traceable sources, and recycle AutoTest results into reusable troubleshooting knowledge.
        </template>
        <template #content>
          <div class="stack-md">
            <label
              class="field-label"
              for="userId"
            >User ID</label>
            <InputText
              id="userId"
              v-model="loginForm.user_id"
              autocomplete="username"
            />

            <label
              class="field-label"
              for="password"
            >Password</label>
            <Password
              id="password"
              v-model="loginForm.password"
              :feedback="false"
              toggle-mask
              input-class="w-full"
            />

            <Button
              label="Sign In"
              :loading="loginLoading"
              @click="login"
            />
            <p class="muted-text">
              Default provider: Ollama (configure `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in backend).
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
          <h1>Personal AI Knowledge Workspace</h1>
          <p>{{ currentUser.display_name }}</p>
        </div>
        <div class="toolbar-actions">
          <Button
            label="Logout"
            severity="secondary"
            @click="logout()"
          />
        </div>
      </header>

      <main class="main-grid">
        <TabView :lazy="true">
          <TabPanel
            header="Activity"
            value="activity"
          >
            <Suspense>
              <ActivityDashboard />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Search"
            value="search"
          >
            <Suspense>
              <GlobalSearchPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Knowledge Base"
            value="knowledge"
          >
            <Suspense>
              <KnowledgeBase />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Problem Logbook"
            value="logbook"
          >
            <Suspense>
              <LogbookPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Documents & Photos"
            value="docsPhotos"
          >
            <Suspense>
              <DocsPhotosPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Auto Test"
            value="autotest"
          >
            <Suspense>
              <AutoTestPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Prompts"
            value="prompts"
          >
            <Suspense>
              <PromptsPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Generator"
            value="generator"
          >
            <Suspense>
              <TemplateGeneratorPanel />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
          <TabPanel
            header="Settings"
            value="settings"
          >
            <Suspense>
              <SettingsPanel :current-user="currentUser" />
              <template #fallback>
                <div class="panel-loading">
                  Loading…
                </div>
              </template>
            </Suspense>
          </TabPanel>
        </TabView>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import TabPanel from 'primevue/tabpanel'
import TabView from 'primevue/tabview'
import Toast from 'primevue/toast'

const ActivityDashboard = defineAsyncComponent(() => import('./components/ActivityDashboard.vue'))
const GlobalSearchPanel = defineAsyncComponent(() => import('./components/GlobalSearchPanel.vue'))
const KnowledgeBase = defineAsyncComponent(() => import('./components/KnowledgeBase.vue'))
const LogbookPanel = defineAsyncComponent(() => import('./components/LogbookPanel.vue'))
const DocsPhotosPanel = defineAsyncComponent(() => import('./components/DocsPhotosPanel.vue'))
const AutoTestPanel = defineAsyncComponent(() => import('./components/AutoTestPanel.vue'))
const PromptsPanel = defineAsyncComponent(() => import('./components/PromptsPanel.vue'))
const TemplateGeneratorPanel = defineAsyncComponent(() => import('./components/TemplateGeneratorPanel.vue'))
const SettingsPanel = defineAsyncComponent(() => import('./components/SettingsPanel.vue'))

import { createInitialUser } from './app-state'
import { get, post } from './api'
import { clearToken, onUnauthorized, restoreToken, setToken } from './auth'
import { useWorkspaceStore } from './workspace-store'
import type { LoginRequest, LoginResponse, MeResponse } from './types'

const toast = useToast()

const loginLoading = ref(false)
const currentUser = ref(createInitialUser())
const loginForm = ref<LoginRequest>({ user_id: '', password: '' })
const workspaceStore = useWorkspaceStore()

const isLoggedIn = computed(() => Boolean(currentUser.value.user_id))

async function login() {
  if (!loginForm.value.user_id || !loginForm.value.password) {
    toast.add({ severity: 'warn', summary: 'Missing fields', detail: 'Enter user ID and password.', life: 3000 })
    return
  }

  loginLoading.value = true
  try {
    const response = await post<LoginResponse, LoginRequest>('/api/login', loginForm.value, { skipAuth: true })
    setToken(response.access_token)
    await bootstrapSession()
    toast.add({ severity: 'success', summary: 'Signed in', detail: 'Workspace ready.', life: 3000 })
  } catch (error: unknown) {
    const apiError = error as { message?: string; status?: number }
    toast.add({ severity: 'error', summary: 'Login failed', detail: apiError?.message || 'Login failed.', life: 4000 })
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
    toast.add({ severity: 'info', summary: 'Logged out', detail: 'Session cleared.', life: 3000 })
  }
}

async function bootstrapSession() {
  const token = restoreToken()
  if (!token) {
    return
  }
  const me = await get<MeResponse>('/api/me')
  currentUser.value = me
}

const removeUnauthorizedListener = onUnauthorized((event) => {
  if (isLoggedIn.value) {
    toast.add({ severity: 'warn', summary: 'Session expired', detail: event.detail || 'Please sign in again.', life: 4000 })
  }
  logout(false)
})

onMounted(async () => {
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
  min-height: 100vh;
  padding: 24px;
  background: radial-gradient(circle at top left, rgba(69, 138, 255, 0.22), transparent 52%),
    radial-gradient(circle at bottom right, rgba(0, 184, 148, 0.15), transparent 50%),
    linear-gradient(140deg, #f7f7fb 0%, #eef4ff 45%, #f5fff9 100%);
}

.login-shell {
  min-height: calc(100vh - 48px);
  display: grid;
  place-items: center;
}

.login-card {
  width: min(520px, 100%);
}

.workspace-shell {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.topbar {
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
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-weight: 600;
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
  .topbar {
    flex-direction: column;
    align-items: flex-start;
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
