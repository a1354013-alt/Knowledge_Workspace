<template>
  <div class="app-shell">
    <Toast />

    <section v-if="!isLoggedIn" class="login-shell">
      <Card class="login-card">
        <template #title>Personal AI Knowledge Workspace for Engineers</template>
        <template #subtitle>Capture solutions, index docs & screenshots, ask AI with traceable sources, and recycle AutoTest results into reusable troubleshooting knowledge.</template>
        <template #content>
          <div class="stack-md">
            <label class="field-label" for="userId">User ID</label>
            <InputText id="userId" v-model="loginForm.user_id" autocomplete="username" />

            <label class="field-label" for="password">Password</label>
            <Password id="password" v-model="loginForm.password" :feedback="false" toggle-mask input-class="w-full" />

            <Button label="Sign In" :loading="loginLoading" @click="login" />
            <p class="muted-text">
              Default provider: Ollama (configure `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in backend).
            </p>
          </div>
        </template>
      </Card>
    </section>

    <section v-else class="workspace-shell">
      <header class="topbar">
        <div>
          <h1>Personal AI Knowledge Workspace</h1>
          <p>{{ currentUser.display_name }}</p>
        </div>
        <div class="toolbar-actions">
          <Button label="Logout" severity="secondary" @click="logout()" />
        </div>
      </header>

      <main class="main-grid">
        <TabView>
          <TabPanel header="Activity">
            <ActivityDashboard />
          </TabPanel>
          <TabPanel header="Search">
            <GlobalSearchPanel />
          </TabPanel>
          <TabPanel header="Knowledge Base">
            <KnowledgeBase />
          </TabPanel>
          <TabPanel header="Problem Logbook">
            <LogbookPanel />
          </TabPanel>
          <TabPanel header="Documents & Photos">
            <DocsPhotosPanel />
          </TabPanel>
          <TabPanel header="Auto Test">
            <AutoTestPanel />
          </TabPanel>
          <TabPanel header="Prompts">
            <PromptsPanel />
          </TabPanel>
          <TabPanel header="Generator">
            <TemplateGeneratorPanel />
          </TabPanel>
          <TabPanel header="Settings">
            <SettingsPanel :current-user="currentUser" />
          </TabPanel>
        </TabView>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import TabPanel from 'primevue/tabpanel'
import TabView from 'primevue/tabview'
import Toast from 'primevue/toast'

import KnowledgeBase from './components/KnowledgeBase.vue'
import ActivityDashboard from './components/ActivityDashboard.vue'
import GlobalSearchPanel from './components/GlobalSearchPanel.vue'
import LogbookPanel from './components/LogbookPanel.vue'
import DocsPhotosPanel from './components/DocsPhotosPanel.vue'
import AutoTestPanel from './components/AutoTestPanel.vue'
import PromptsPanel from './components/PromptsPanel.vue'
import TemplateGeneratorPanel from './components/TemplateGeneratorPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'

import { createInitialUser } from './app-state'
import { apiClient } from './api'
import { clearToken, onUnauthorized, restoreToken, setToken } from './auth'

const toast = useToast()

const loginLoading = ref(false)
const currentUser = ref(createInitialUser())
const loginForm = ref({ user_id: '', password: '' })

const isLoggedIn = computed(() => Boolean(currentUser.value.user_id))

async function login() {
  if (!loginForm.value.user_id || !loginForm.value.password) {
    toast.add({ severity: 'warn', summary: 'Missing fields', detail: 'Enter user ID and password.', life: 3000 })
    return
  }

  loginLoading.value = true
  try {
    const response = await apiClient.post('/api/login', loginForm.value, { skipAuth: true })
    setToken(response.access_token)
    await bootstrapSession()
    toast.add({ severity: 'success', summary: 'Signed in', detail: 'Workspace ready.', life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Login failed', detail: error.message, life: 4000 })
    if (error?.status === 401) {
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
  if (showToast) {
    toast.add({ severity: 'info', summary: 'Logged out', detail: 'Session cleared.', life: 3000 })
  }
}

async function bootstrapSession() {
  const token = restoreToken()
  if (!token) {
    return
  }
  const me = await apiClient.get('/api/me')
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
  } catch (error) {
    if (error?.status === 401) {
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
</style>
