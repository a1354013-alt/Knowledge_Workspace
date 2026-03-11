<template>
  <div class="admin-console">
    <TabView>
      <!-- Users Tab -->
      <TabPanel header="使用者管理">
        <div class="users-section">
          <div class="toolbar">
            <Button icon="pi pi-plus" label="新增使用者" @click="showUserDialog = true" />
          </div>
          
          <DataTable :value="users" responsiveLayout="scroll" :loading="loadingUsers">
            <Column field="user_id" header="使用者 ID" />
            <Column field="display_name" header="顯示名稱" />
            <Column field="role" header="角色">
              <template #body="slotProps">
                <Tag :value="slotProps.data.role" :severity="getRoleSeverity(slotProps.data.role)" />
              </template>
            </Column>
            <Column field="is_active" header="狀態">
              <template #body="slotProps">
                <Tag :value="slotProps.data.is_active ? '啟用' : '停用'" :severity="slotProps.data.is_active ? 'success' : 'danger'" />
              </template>
            </Column>
            <Column header="操作">
              <template #body="slotProps">
                <Button icon="pi pi-pencil" class="p-button-rounded p-button-warning" @click="editUser(slotProps.data)" />
                <Button icon="pi pi-trash" class="p-button-rounded p-button-danger" @click="deleteUser(slotProps.data)" />
              </template>
            </Column>
          </DataTable>
        </div>
      </TabPanel>
      
      <!-- Documents Tab -->
      <TabPanel header="文件審核">
        <div class="documents-section">
          <DataTable :value="documents" responsiveLayout="scroll" :loading="loadingDocs">
            <Column field="filename" header="檔案名稱" />
            <Column field="uploaded_by" header="上傳者" />
            <Column field="approved" header="審核">
              <template #body="slotProps">
                <Tag :value="slotProps.data.approved ? '已批准' : '待審核'" :severity="slotProps.data.approved ? 'success' : 'warning'" />
              </template>
            </Column>
            <Column field="is_active" header="狀態">
              <template #body="slotProps">
                <Tag :value="slotProps.data.is_active ? '上架' : '下架'" :severity="slotProps.data.is_active ? 'success' : 'danger'" />
              </template>
            </Column>
            <Column header="操作">
              <template #body="slotProps">
                <Button icon="pi pi-pencil" class="p-button-rounded p-button-warning" @click="editDocument(slotProps.data)" />
                <Button icon="pi pi-trash" class="p-button-rounded p-button-danger" @click="deleteDocument(slotProps.data)" />
              </template>
            </Column>
          </DataTable>
        </div>
      </TabPanel>
    </TabView>
    
    <!-- User Dialog -->
    <Dialog v-model:visible="showUserDialog" :header="editingUser ? '編輯使用者' : '新增使用者'" :modal="true" @hide="resetUserForm">
      <div class="p-fluid">
        <div class="field">
          <label>使用者 ID</label>
          <InputText v-model="userForm.user_id" :disabled="!!editingUser" />
        </div>
        <div class="field">
          <label>顯示名稱</label>
          <InputText v-model="userForm.display_name" />
        </div>
        <div class="field">
          <label>角色</label>
          <Dropdown v-model="userForm.role" :options="roleOptions" optionLabel="label" optionValue="value" />
        </div>
        <div class="field">
          <label>狀態</label>
          <Dropdown v-model="userForm.is_active" :options="[{ label: '啟用', value: 1 }, { label: '停用', value: 0 }]" optionLabel="label" optionValue="value" />
        </div>
        <div v-if="!editingUser" class="field">
          <label>密碼</label>
          <Password v-model="userForm.password" toggleMask />
        </div>
        <div v-else class="field">
          <label>重設密碼（留空則不改）</label>
          <Password v-model="userForm.password" toggleMask />
        </div>
      </div>
      <template #footer>
        <Button label="取消" @click="showUserDialog = false" class="p-button-text" />
        <Button label="保存" @click="saveUser" />
      </template>
    </Dialog>
    
    <!-- Document Dialog -->
    <Dialog v-model:visible="showDocDialog" header="編輯文件" :modal="true" @hide="resetDocForm">
      <div class="p-fluid">
        <div class="field">
          <label>檔案名稱</label>
          <InputText v-model="docForm.filename" disabled />
        </div>
        <div class="field">
          <label>允許查看角色</label>
          <MultiSelect v-model="docForm.allowed_roles" :options="roleOptions" optionLabel="label" optionValue="value" />
        </div>
        <div class="field">
          <label>審核狀態</label>
          <Dropdown v-model="docForm.approved" :options="[{ label: '待審核', value: 0 }, { label: '已批准', value: 1 }]" optionLabel="label" optionValue="value" />
        </div>
        <div class="field">
          <label>上下架狀態</label>
          <Dropdown v-model="docForm.is_active" :options="[{ label: '上架', value: 1 }, { label: '下架', value: 0 }]" optionLabel="label" optionValue="value" />
        </div>
      </div>
      <template #footer>
        <Button label="取消" @click="showDocDialog = false" class="p-button-text" />
        <Button label="保存" @click="saveDocument" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import axios from 'axios'

// 【重要】定義 emit（修復 ReferenceError）
const emit = defineEmits(['close'])

const toast = useToast()
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// State
const users = ref([])
const documents = ref([])
const loadingUsers = ref(false)
const loadingDocs = ref(false)
const showUserDialog = ref(false)
const showDocDialog = ref(false)
const editingUser = ref(null)
const editingDoc = ref(null)

const userForm = ref({
  user_id: '',
  password: '',
  display_name: '',
  role: 'employee',
  is_active: 1
})

const docForm = ref({
  doc_id: '',
  filename: '',
  allowed_roles: ['employee'],
  approved: 0,
  is_active: 1
})

const roleOptions = [
  { label: '員工 (Employee)', value: 'employee' },
  { label: '主管 (Manager)', value: 'manager' },
  { label: '人資 (HR)', value: 'hr' },
  { label: '管理員 (Admin)', value: 'admin' }
]

// API 呼叫
const getAuthHeader = () => {
  const token = localStorage.getItem('authToken')
  if (!token) {
    // 【重要】token 不存在時拋出錯誤
    throw new Error('Missing token')
  }
  return { Authorization: `Bearer ${token}` }
}

// 【重要】包裝 axios 呼叫，自動處理 token 缺失情況
// 接收一個函式，讓它可以包住 getAuthHeader（避免參數評估階段就拋出）
const safeAxiosCall = async (fn) => {
  try {
    return await fn()
  } catch (error) {
    if (error.message === 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: '請重新登入' })
      emit('close')
      return null
    }
    throw error
  }
}

const loadUsers = async () => {
  try {
    loadingUsers.value = true
    const response = await safeAxiosCall(() =>
      axios.get(`${API_BASE}/api/admin/users`, {
        headers: getAuthHeader()
      })
    )
    if (response) {
      users.value = response.data
    }
  } catch (error) {
    if (error.message !== 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '載入使用者失敗' })
    }
  } finally {
    loadingUsers.value = false
  }
}

const loadDocuments = async () => {
  try {
    loadingDocs.value = true
    const response = await safeAxiosCall(() =>
      axios.get(`${API_BASE}/api/admin/docs`, {
        headers: getAuthHeader()
      })
    )
    if (response) {
      documents.value = response.data
    }
  } catch (error) {
    if (error.message !== 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '載入文件失敗' })
    }
  } finally {
    loadingDocs.value = false
  }
}

const saveUser = async () => {
  try {
    const formData = new FormData()
    formData.append('user_id', userForm.value.user_id)
    formData.append('display_name', userForm.value.display_name)
    formData.append('role', userForm.value.role)
    formData.append('is_active', userForm.value.is_active)
    if (userForm.value.password) {
      formData.append('password', userForm.value.password)
    }
    
    if (editingUser.value) {
      // 更新使用者
      await safeAxiosCall(() =>
        axios.patch(`${API_BASE}/api/admin/users/${editingUser.value.user_id}`, formData, {
          headers: getAuthHeader()
        })
      )
      toast.add({ severity: 'success', summary: '成功', detail: '使用者已更新' })
    } else {
      // 新增使用者
      if (!userForm.value.password) {
        toast.add({ severity: 'error', summary: '錯誤', detail: '新增使用者需要設定密碼' })
        return
      }
      formData.append('user_id', userForm.value.user_id)
      await safeAxiosCall(() =>
        axios.post(`${API_BASE}/api/admin/users`, formData, {
          headers: getAuthHeader()
        })
      )
      toast.add({ severity: 'success', summary: '成功', detail: '使用者已建立' })
    }
    
    showUserDialog.value = false
    loadUsers()
  } catch (error) {
    toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '保存失敗' })
  }
}

const saveDocument = async () => {
  try {
    const formData = new FormData()
    formData.append('allowed_roles', docForm.value.allowed_roles.join(','))
    formData.append('approved', docForm.value.approved)
    formData.append('is_active', docForm.value.is_active)
    
    await safeAxiosCall(() =>
      axios.patch(`${API_BASE}/api/admin/docs/${docForm.value.doc_id}`, formData, {
        headers: getAuthHeader()
      })
    )
    toast.add({ severity: 'success', summary: '成功', detail: '文件已更新' })
    showDocDialog.value = false
    loadDocuments()
  } catch (error) {
    if (error.message !== 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '保存失敗' })
    }
  }
}

const editUser = (user) => {
  editingUser.value = user
  userForm.value = {
    user_id: user.user_id,
    password: '',
    display_name: user.display_name,
    role: user.role,
    is_active: user.is_active
  }
  showUserDialog.value = true
}

const editDocument = (doc) => {
  editingDoc.value = doc
  // 【重要】正規化 allowed_roles：保證是 list 且每個元素都已 trim
  let normalizedRoles = []
  if (typeof doc.allowed_roles === 'string') {
    normalizedRoles = doc.allowed_roles.split(',').map(s => s.trim()).filter(Boolean)
  } else if (Array.isArray(doc.allowed_roles)) {
    normalizedRoles = doc.allowed_roles.map(s => String(s).trim()).filter(Boolean)
  }
  
  docForm.value = {
    doc_id: doc.id,
    filename: doc.filename,
    allowed_roles: normalizedRoles,
    approved: doc.approved,
    is_active: doc.is_active
  }
  showDocDialog.value = true
}

const deleteUser = async (user) => {
  if (!confirm(`確定要刪除使用者 ${user.user_id} 嗎？`)) return
  
  try {
    // 實作：停用使用者而不是刪除
    const formData = new FormData()
    formData.append('is_active', 0)
    await safeAxiosCall(() =>
      axios.patch(`${API_BASE}/api/admin/users/${user.user_id}`, formData, {
        headers: getAuthHeader()
      })
    )
    toast.add({ severity: 'success', summary: '成功', detail: '使用者已停用' })
    loadUsers()
  } catch (error) {
    if (error.message !== 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '刪除失敗' })
    }
  }
}

const deleteDocument = async (doc) => {
  if (!confirm(`確定要刪除文件 ${doc.filename} 吗？`)) return
  
  try {
    await safeAxiosCall(() =>
      axios.delete(`${API_BASE}/api/admin/docs/${doc.id}`, {
        headers: getAuthHeader()
      })
    )
    toast.add({ severity: 'success', summary: '成功', detail: '文件已刪除' })
    loadDocuments()
  } catch (error) {
    if (error.message !== 'Missing token') {
      toast.add({ severity: 'error', summary: '錯誤', detail: error.response?.data?.detail || '刪除失敗' })
    }
  }
}

const resetUserForm = () => {
  editingUser.value = null
  userForm.value = {
    user_id: '',
    password: '',
    display_name: '',
    role: 'employee',
    is_active: 1
  }
}

const resetDocForm = () => {
  editingDoc.value = null
  docForm.value = {
    doc_id: '',
    filename: '',
    allowed_roles: ['employee'],
    approved: 0,
    is_active: 1
  }
}

const getRoleSeverity = (role) => {
  const severities = {
    'admin': 'danger',
    'hr': 'warning',
    'manager': 'info',
    'employee': 'success'
  }
  return severities[role] || 'info'
}

// Lifecycle
onMounted(() => {
  loadUsers()
  loadDocuments()
})
</script>

<style scoped>
.admin-console {
  padding: 20px;
}

.users-section,
.documents-section {
  padding: 20px;
}

.toolbar {
  margin-bottom: 20px;
}

.field {
  margin-bottom: 15px;
}

.field label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}
</style>
