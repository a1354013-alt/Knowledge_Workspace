<template>
  <div class="app-container">
    <!-- 【改進】Toast UI 元件 -->
    <Toast />
    
    <!-- 登入頁面 -->
    <div v-if="!isLoggedIn" class="login-page">
      <Card class="login-card">
        <template #header>
          <div class="login-header">
            <i class="pi pi-shield"></i>
            <h2>企業 AI 助理 - 登入</h2>
          </div>
        </template>
        
        <template #content>
          <div class="login-form">
            <div class="form-group">
              <label>使用者 ID</label>
              <InputText 
                v-model="loginUserId" 
                placeholder="輸入您的使用者 ID"
                class="w-full"
              />
            </div>

            <div class="form-group">
              <label>密碼</label>
              <InputText 
                v-model="loginPassword" 
                type="password"
                placeholder="輸入密碼"
                class="w-full"
              />
            </div>

            <Button 
              @click="login" 
              :loading="loginLoading"
              class="w-full"
              label="登入"
              size="large"
            />
          </div>
        </template>
      </Card>
    </div>

    <!-- 主應用 -->
    <div v-else class="main-app">
      <div class="header">
        <h1>企業 AI 助理</h1>
        <p>文件查詢、RAG 問答、表單生成一站式解決方案</p>
      </div>

      <div class="user-info">
        <span>👤 {{ currentUser.user_id }} ({{ currentUser.role }}) - {{ currentUser.display_name }}</span>
        <div class="user-actions">
          <!-- Admin 入口 -->
          <Button 
            v-if="currentUser.role === 'admin'"
            @click="showAdminConsole = !showAdminConsole"
            :severity="showAdminConsole ? 'success' : 'info'"
            size="small"
            label="Admin 後台"
          />
          <Button 
            @click="logout" 
            label="登出"
            severity="secondary"
            size="small"
          />
        </div>
      </div>

      <!-- Admin Console -->
      <AdminConsole 
        v-if="showAdminConsole && currentUser.role === 'admin'"
        :token="authToken"
        @close="showAdminConsole = false"
      />

      <!-- 主內容（非 Admin 頁面） -->
      <div v-if="!showAdminConsole" class="main-grid">
        <!-- 左欄：文件管理 -->
        <Card class="left-panel">
          <template #header>
            <div class="panel-header">
              <i class="pi pi-file"></i>
              <span>文件管理</span>
            </div>
          </template>
          
          <template #content>
            <div class="panel-content">
              <!-- 上傳區域 -->
              <div class="upload-area">
                <input 
                  type="file" 
                  ref="fileInput"
                  @change="onFileSelected"
                  accept=".pdf,.txt,.md"
                  style="display: none"
                />
                <div class="upload-box" @click="openFilePicker">
                  <i class="pi pi-upload"></i>
                  <p>選擇文件 (PDF/TXT/MD)</p>
                  <p v-if="selectedFile" class="file-name">{{ selectedFile.name }}</p>
                </div>
              </div>

              <!-- 角色選擇 (MultiSelect) -->
              <div class="role-input">
                <label>允許查看角色</label>
                <MultiSelect 
                  v-model="uploadRoles" 
                  :options="roleOptions"
                  placeholder="選擇角色"
                  class="w-full"
                />
              </div>

              <!-- 上傳按鈕 -->
              <Button 
                @click="uploadFile" 
                :loading="uploadLoading"
                class="w-full"
                label="上傳文件"
                icon="pi pi-upload"
              />

              <!-- 文件列表 -->
              <div class="documents-list">
                <h3>已上傳文件</h3>
                <div v-if="documents.length === 0" class="empty-state">
                  <p>暫無文件</p>
                </div>
                <div v-else class="doc-items">
                  <div v-for="doc in documents" :key="doc.id" class="doc-item">
                    <div class="doc-info">
                      <p class="doc-name">{{ doc.filename }}</p>
                      <p class="doc-meta">
                        上傳者: {{ doc.uploaded_by }} | 
                        狀態: <span :class="doc.approved ? 'approved' : 'pending'">{{ doc.approved ? '已批准' : '待審核' }}</span>
                      </p>
                    </div>
                    <Button 
                      v-if="currentUser.user_id === doc.uploaded_by || currentUser.role === 'admin'"
                      @click="deleteDocument(doc.id)" 
                      icon="pi pi-trash"
                      severity="danger"
                      size="small"
                      text
                    />
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- 中欄：問答 -->
        <Card class="middle-panel">
          <template #header>
            <div class="panel-header">
              <i class="pi pi-comments"></i>
              <span>智能問答</span>
            </div>
          </template>
          
          <template #content>
            <div class="panel-content">
              <div class="qa-input">
                <Textarea 
                  v-model="qaQuestion" 
                  placeholder="輸入您的問題..."
                  rows="3"
                  class="w-full"
                />
                <Button 
                  @click="submitQA" 
                  :loading="qaLoading"
                  class="w-full mt-2"
                  label="提交問題"
                  icon="pi pi-send"
                />
              </div>

              <div v-if="qaAnswer" class="qa-result">
                <h3>回答</h3>
                <p class="answer-text">{{ qaAnswer }}</p>
                
                <div v-if="qaSources.length > 0" class="sources">
                  <h4>引用來源</h4>
                  <div v-for="(source, idx) in qaSources" :key="idx" class="source-card">
                    <p class="source-title">{{ source.doc_name }} - {{ source.page_or_section }}</p>
                    <p class="source-text">{{ source.chunk_text }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- 右欄：表單生成 -->
        <Card class="right-panel">
          <template #header>
            <div class="panel-header">
              <i class="pi pi-file-edit"></i>
              <span>表單生成</span>
            </div>
          </template>
          
          <template #content>
            <div class="panel-content">
              <div class="form-generator">
                <div class="template-select">
                  <label>選擇模板</label>
                  <Dropdown 
                    v-model="selectedTemplate" 
                    :options="templates"
                    option-label="label"
                    option-value="value"
                    @change="onTemplateChange"
                    class="w-full"
                  />
                </div>

                <div v-if="selectedTemplate" class="template-fields">
                  <div v-for="field in templateFields" :key="field" class="field-input">
                    <label>{{ field }}</label>
                    <Textarea 
                      v-model="formInputs[field]" 
                      :placeholder="`輸入 ${field}`"
                      rows="2"
                      class="w-full"
                    />
                  </div>
                </div>

                <Button 
                  v-if="selectedTemplate"
                  @click="generateForm" 
                  :loading="generateLoading"
                  :disabled="!isFormValid"
                  class="w-full"
                  label="生成內容"
                  icon="pi pi-magic"
                />

                <div v-if="generatedContent" class="generated-output">
                  <h3>生成結果</h3>
                  <div class="output-box">
                    <p>{{ generatedContent }}</p>
                  </div>
                  <Button 
                    @click="copyToClipboard" 
                    class="w-full mt-2"
                    label="複製到剪貼簿"
                    icon="pi pi-copy"
                  />
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import MultiSelect from 'primevue/multiselect'
import AdminConsole from './components/AdminConsole.vue'

export default {
  name: 'App',
  components: {
    Card,
    Button,
    InputText,
    Textarea,
    Dropdown,
    MultiSelect,
    AdminConsole
  },
  setup() {
    const toast = useToast()
    const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

    // 登入相關
    const isLoggedIn = ref(false)
    const authToken = ref('')
    const loginUserId = ref('')
    const loginPassword = ref('')
    const loginLoading = ref(false)
    const currentUser = ref({
      user_id: '',
      role: '',
      display_name: ''
    })

    // Admin 相關
    const showAdminConsole = ref(false)

    // 文件管理相關
    const documents = ref([])
    const selectedFile = ref(null)
    const uploadRoles = ref(['employee'])
    const uploadLoading = ref(false)
    const fileInput = ref(null)

    // 問答相關
    const qaQuestion = ref('')
    const qaAnswer = ref('')
    const qaSources = ref([])
    const qaLoading = ref(false)

    // 表單生成相關
    const selectedTemplate = ref(null)
    const formInputs = ref({})
    const generatedContent = ref('')
    const generateLoading = ref(false)

    // 下拉選項
    const roleOptions = ref([
      { label: 'Employee', value: 'employee' },
      { label: 'Manager', value: 'manager' },
      { label: 'HR', value: 'hr' }
    ])

    const templates = ref([
      { label: '請假通知', value: '請假通知' },
      { label: '加班申請說明', value: '加班申請說明' },
      { label: '變更申請摘要', value: '變更申請摘要' },
      { label: '會議紀錄', value: '會議紀錄' }
    ])

    const templateFieldsMap = {
      '請假通知': ['申請人', '請假類型', '開始日期', '結束日期', '原因'],
      '加班申請說明': ['申請人', '加班日期', '加班時數', '加班原因', '預期完成工作'],
      '變更申請摘要': ['申請人', '變更項目', '原內容', '新內容', '變更原因'],
      '會議紀錄': ['會議名稱', '開會日期', '參與人員', '討論內容', '決議事項']
    }

    // 計算屬性
    const templateFields = computed(() => {
      return selectedTemplate.value ? templateFieldsMap[selectedTemplate.value] : []
    })

    const isFormValid = computed(() => {
      if (!selectedTemplate.value) return false
      const fields = templateFields.value
      return fields.every(field => formInputs.value[field] && formInputs.value[field].trim())
    })

    // 登入函數
    const login = async () => {
      if (!loginUserId.value || !loginPassword.value) {
        toast.add({ severity: 'warn', summary: '警告', detail: '請輸入使用者 ID 和密碼', life: 3000 })
        return
      }

      loginLoading.value = true
      try {
        const formData = new FormData()
        formData.append('user_id', loginUserId.value)
        formData.append('password', loginPassword.value)

        const response = await fetch(`${API_BASE}/api/login`, {
          method: 'POST',
          body: formData
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '登入失敗')
        }

        const data = await response.json()
        authToken.value = data.access_token
        localStorage.setItem('authToken', data.access_token)

        // 取得使用者資訊
        const meResponse = await fetch(`${API_BASE}/api/me`, {
          headers: {
            'Authorization': `Bearer ${data.access_token}`
          }
        })

        if (!meResponse.ok) {
          throw new Error('無法取得使用者資訊')
        }

        const userData = await meResponse.json()
        currentUser.value = userData
        isLoggedIn.value = true

        toast.add({ severity: 'success', summary: '成功', detail: '登入成功', life: 3000 })
        
        // 載入文件列表
        loadDocuments()
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      } finally {
        loginLoading.value = false
      }
    }

    // 登出函數
    const logout = () => {
      isLoggedIn.value = false
      authToken.value = ''
      loginUserId.value = ''
      loginPassword.value = ''
      currentUser.value = { user_id: '', role: '', display_name: '' }
      documents.value = []
      qaQuestion.value = ''
      qaAnswer.value = ''
      qaSources.value = []
      selectedTemplate.value = null
      formInputs.value = {}
      generatedContent.value = ''
      showAdminConsole.value = false
      localStorage.removeItem('authToken')
      toast.add({ severity: 'info', summary: '提示', detail: '已登出', life: 3000 })
    }

    // 檔案選擇
    const onFileSelected = (event) => {
      selectedFile.value = event.target.files[0]
    }

    // 上傳檔案
    const uploadFile = async () => {
      if (!selectedFile.value) {
        toast.add({ severity: 'warn', summary: '警告', detail: '請選擇檔案', life: 3000 })
        return
      }

      if (uploadRoles.value.length === 0) {
        toast.add({ severity: 'warn', summary: '警告', detail: '請選擇至少一個角色', life: 3000 })
        return
      }

      uploadLoading.value = true
      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('allowed_roles', uploadRoles.value.join(','))

        const response = await fetch(`${API_BASE}/api/docs/upload`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken.value}`
          },
          body: formData
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '上傳失敗')
        }

        toast.add({ severity: 'success', summary: '成功', detail: '檔案上傳成功（待 admin 審核）', life: 3000 })
        selectedFile.value = null
        uploadRoles.value = ['employee']
        fileInput.value.value = ''
        loadDocuments()
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      } finally {
        uploadLoading.value = false
      }
    }

    // 載入文件列表
    const loadDocuments = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/docs`, {
          headers: {
            'Authorization': `Bearer ${authToken.value}`
          }
        })

        if (!response.ok) {
          throw new Error('無法載入文件列表')
        }

        documents.value = await response.json()
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      }
    }

    // 刪除文件
    const deleteDocument = async (docId) => {
      if (!confirm('確定要刪除此文件嗎？')) {
        return
      }

      try {
        const response = await fetch(`${API_BASE}/api/docs/${docId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${authToken.value}`
          }
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '刪除失敗')
        }

        toast.add({ severity: 'success', summary: '成功', detail: '文件已刪除', life: 3000 })
        loadDocuments()
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      }
    }

    // 提交問題
    const submitQA = async () => {
      if (!qaQuestion.value.trim()) {
        toast.add({ severity: 'warn', summary: '警告', detail: '請輸入問題', life: 3000 })
        return
      }

      qaLoading.value = true
      try {
        const response = await fetch(`${API_BASE}/api/qa`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken.value}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            question: qaQuestion.value
          })
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '問答失敗')
        }

        const data = await response.json()
        qaAnswer.value = data.answer
        qaSources.value = data.sources || []
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      } finally {
        qaLoading.value = false
      }
    }

    // 模板切換
    const onTemplateChange = () => {
      formInputs.value = {}
      generatedContent.value = ''
    }

    // 生成表單
    const generateForm = async () => {
      if (!isFormValid.value) {
        toast.add({ severity: 'warn', summary: '警告', detail: '請填寫所有必填欄位', life: 3000 })
        return
      }

      generateLoading.value = true
      try {
        const response = await fetch(`${API_BASE}/api/generate`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken.value}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            template_type: selectedTemplate.value,
            inputs: formInputs.value
          })
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || '生成失敗')
        }

        const data = await response.json()
        generatedContent.value = data.content
        toast.add({ severity: 'success', summary: '成功', detail: '內容已生成', life: 3000 })
      } catch (error) {
        toast.add({ severity: 'error', summary: '錯誤', detail: error.message, life: 3000 })
      } finally {
        generateLoading.value = false
      }
    }

    // 複製到剪貼簿
    const copyToClipboard = () => {
      navigator.clipboard.writeText(generatedContent.value)
      toast.add({ severity: 'success', summary: '成功', detail: '已複製到剪貼簿', life: 3000 })
    }

    // 【新增】打開檔案選擇器
    const openFilePicker = () => {
      fileInput.value?.click()
    }

    // 初始化
    onMounted(async () => {
      const token = localStorage.getItem('authToken')
      if (token) {
        authToken.value = token
        // 【新增】驗證 token 是否仍有效，並恢複登入狀態
        try {
          const response = await fetch(`${API_BASE}/api/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if (response.ok) {
            const userData = await response.json()
            currentUser.value = userData
            isLoggedIn.value = true
            await loadDocuments()
          } else {
            // token 無效，清除
            localStorage.removeItem('authToken')
            authToken.value = ''
          }
        } catch (error) {
          console.error('驗證 token 失敗:', error)
          localStorage.removeItem('authToken')
          authToken.value = ''
        }
      }
    })

    return {
      isLoggedIn,
      authToken,
      loginUserId,
      loginPassword,
      loginLoading,
      currentUser,
      showAdminConsole,
      openFilePicker,
      documents,
      selectedFile,
      uploadRoles,
      uploadLoading,
      fileInput,
      qaQuestion,
      qaAnswer,
      qaSources,
      qaLoading,
      selectedTemplate,
      formInputs,
      generatedContent,
      generateLoading,
      roleOptions,
      templates,
      templateFields,
      isFormValid,
      login,
      logout,
      onFileSelected,
      uploadFile,
      loadDocuments,
      deleteDocument,
      submitQA,
      onTemplateChange,
      generateForm,
      copyToClipboard
    }
  }
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
}

.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.login-card {
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.login-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 24px;
  font-weight: bold;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 500;
  color: #333;
}

.main-app {
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header h1 {
  font-size: 36px;
  margin: 0;
}

.header p {
  font-size: 16px;
  margin: 10px 0 0 0;
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.user-actions {
  display: flex;
  gap: 10px;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

@media (max-width: 1200px) {
  .main-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: bold;
  font-size: 18px;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.upload-area {
  margin-bottom: 15px;
}

.upload-box {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-box:hover {
  border-color: #007bff;
  background: #f0f8ff;
}

.upload-box i {
  font-size: 32px;
  color: #007bff;
}

.file-name {
  color: #28a745;
  font-weight: bold;
  margin-top: 10px;
}

.role-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.documents-list {
  margin-top: 20px;
}

.documents-list h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 20px;
}

.doc-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.doc-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.doc-info {
  flex: 1;
}

.doc-name {
  margin: 0;
  font-weight: bold;
  color: #333;
}

.doc-meta {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #666;
}

.approved {
  color: #28a745;
  font-weight: bold;
}

.pending {
  color: #ffc107;
  font-weight: bold;
}

.qa-input {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.qa-result {
  margin-top: 20px;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 6px;
}

.qa-result h3 {
  margin: 0 0 10px 0;
}

.answer-text {
  line-height: 1.6;
  color: #333;
}

.sources {
  margin-top: 15px;
}

.sources h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
}

.source-card {
  padding: 10px;
  background: white;
  border-left: 3px solid #28a745;
  margin-bottom: 10px;
  border-radius: 4px;
}

.source-title {
  margin: 0;
  font-weight: bold;
  font-size: 12px;
  color: #007bff;
}

.source-text {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.form-generator {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.template-select {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.field-input {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-input label {
  font-weight: 500;
  font-size: 14px;
}

.generated-output {
  margin-top: 15px;
  padding: 15px;
  background: #f0f8ff;
  border-radius: 6px;
}

.generated-output h3 {
  margin: 0 0 10px 0;
}

.output-box {
  background: white;
  padding: 12px;
  border-radius: 4px;
  border-left: 3px solid #28a745;
  max-height: 200px;
  overflow-y: auto;
}

.output-box p {
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.w-full {
  width: 100%;
}

.mt-2 {
  margin-top: 8px;
}
</style>
