<template>
  <div class="grid">
    <Card>
      <template #title>
        {{ t('docsPhotos.documentsTitle') }}
      </template>
      <template #subtitle>
        {{ t('docsPhotos.documentsSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <p
            v-if="docLoadMessage"
            class="inline-status"
            :class="{ 'inline-status-warning': showDocReloadWarning }"
          >
            {{ docLoadMessage }}
          </p>
          <p
            v-if="searchStatusMessage"
            class="index-banner"
            :class="{ 'index-banner-ok': searchStatusReady }"
          >
            {{ searchStatusMessage }}
          </p>
          <div class="row">
            <input
              ref="docInput"
              type="file"
              accept=".pdf,.txt,.md"
              class="hidden-input"
              @change="onDocSelected"
            >
            <Button
              :label="t('docsPhotos.chooseDocument')"
              icon="pi pi-upload"
              outlined
              @click="openDocPicker"
            />
            <span
              v-if="selectedDoc"
              class="muted"
            >{{ selectedDoc.name }}</span>
          </div>

          <InputText
            v-model="docCategory"
            :placeholder="t('docsPhotos.categoryOptional')"
          />
          <InputText
            v-model="docTags"
            :placeholder="t('docsPhotos.tagsOptional')"
          />
          <div class="row">
            <Button
              :label="t('common.upload')"
              :loading="uploadingDoc"
              @click="uploadDoc"
            />
            <Button
              :label="t('common.refresh')"
              outlined
              icon="pi pi-refresh"
              :loading="loadingDocs"
              @click="loadDocuments"
            />
          </div>

          <InputText
            v-model="docFilterText"
            :placeholder="t('docsPhotos.filterDocs')"
          />

          <DataTable
            :value="filteredDocuments"
            :loading="loadingDocs"
            data-key="id"
            size="small"
            responsive-layout="scroll"
          >
            <Column
              field="filename"
              :header="t('common.file')"
            />
            <Column
              field="category"
              :header="t('common.category')"
            />
            <Column
              field="tags"
              :header="t('common.tags')"
            />
            <Column
              field="status"
              :header="t('common.status')"
            />
            <Column :header="t('common.index')">
              <template #body="slotProps">
                <div class="index-cell">
                  <strong>{{ slotProps.data.index_status || t('common.pending') }}</strong>
                  <span
                    v-if="slotProps.data.index_error"
                    class="muted"
                  >{{ slotProps.data.index_error }}</span>
                  <span
                    v-else-if="slotProps.data.index_status === 'excluded'"
                    class="muted"
                  >{{ t('docsPhotos.archivedExcluded') }}</span>
                </div>
              </template>
            </Column>
            <Column :header="t('common.actions')">
              <template #body="slotProps">
                <div class="actions-inline">
                  <Button
                    v-if="slotProps.data.index_status !== 'indexed' && slotProps.data.index_status !== 'excluded'"
                    icon="pi pi-wrench"
                    text
                    severity="warning"
                    @click="rebuildDocumentIndex(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-eye"
                    text
                    severity="secondary"
                    @click="previewDocument(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-download"
                    text
                    severity="secondary"
                    @click="downloadDocument(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-pencil"
                    text
                    severity="secondary"
                    @click="openDocEditor(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-sitemap"
                    text
                    severity="secondary"
                    @click="showDocReferences(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-archive"
                    text
                    severity="secondary"
                    @click="archiveDocument(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-trash"
                    text
                    severity="danger"
                    @click="deleteDocument(slotProps.data)"
                  />
                </div>
              </template>
            </Column>
          </DataTable>

          <RelatedItemsPanel
            v-if="selectedRelatedItemId"
            :item-id="selectedRelatedItemId"
          />
        </div>
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('docsPhotos.photosTitle') }}
      </template>
      <template #subtitle>
        {{ t('docsPhotos.photosSubtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <p
            v-if="photoLoadMessage"
            class="inline-status"
            :class="{ 'inline-status-warning': showPhotoReloadWarning }"
          >
            {{ photoLoadMessage }}
          </p>
          <div class="row">
            <input
              ref="photoInput"
              type="file"
              accept="image/*"
              class="hidden-input"
              @change="onPhotoSelected"
            >
            <Button
              :label="t('docsPhotos.chooseImage')"
              icon="pi pi-image"
              outlined
              @click="openPhotoPicker"
            />
            <span
              v-if="selectedPhoto"
              class="muted"
            >{{ selectedPhoto.name }}</span>
          </div>

          <InputText
            v-model="photoTags"
            :placeholder="t('docsPhotos.tagsOptional')"
          />
          <Textarea
            v-model="photoDescription"
            rows="2"
            :placeholder="t('docsPhotos.descriptionOptional')"
          />
          <div class="row">
            <Button
              :label="t('common.upload')"
              :loading="uploadingPhoto"
              @click="uploadPhoto"
            />
            <Button
              :label="t('common.refresh')"
              outlined
              icon="pi pi-refresh"
              :loading="loadingPhotos"
              @click="loadPhotos"
            />
          </div>

          <DataTable
            :value="photos"
            :loading="loadingPhotos"
            data-key="id"
            size="small"
            responsive-layout="scroll"
          >
            <Column
              field="filename"
              :header="t('common.file')"
            />
            <Column
              field="tags"
              :header="t('common.tags')"
            />
            <Column
              field="description"
              :header="t('common.description')"
            />
            <Column :header="t('docsPhotos.ocr')">
              <template #body="slotProps">
                <Tag
                  :severity="slotProps.data.ocr_status === 'completed' ? 'success' : slotProps.data.ocr_status === 'pending' ? 'info' : 'warn'"
                  :value="slotProps.data.ocr_status || t('common.pending')"
                />
                <small
                  v-if="slotProps.data.ocr_error"
                  class="muted block"
                >{{ slotProps.data.ocr_error }}</small>
              </template>
            </Column>
            <Column
              field="created_at"
              :header="t('common.created')"
            />
            <Column :header="t('common.actions')">
              <template #body="slotProps">
                <div class="actions-inline">
                  <Button
                    icon="pi pi-eye"
                    text
                    severity="secondary"
                    @click="previewPhoto(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-download"
                    text
                    severity="secondary"
                    @click="downloadPhoto(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-pencil"
                    text
                    severity="secondary"
                    @click="openPhotoEditor(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-sitemap"
                    text
                    severity="secondary"
                    @click="showPhotoReferences(slotProps.data)"
                  />
                  <Button
                    icon="pi pi-trash"
                    text
                    severity="danger"
                    @click="deletePhoto(slotProps.data)"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </Card>
  </div>

  <Dialog
    v-model:visible="docEditorVisible"
    modal
    :header="t('docsPhotos.editDocument')"
    class="workspace-dialog"
    :style="{ width: 'min(720px, calc(100vw - 32px))' }"
  >
    <div class="dialog-body stack-md">
      <div class="muted">
        <code>{{ docEditor.id ? `document:${docEditor.id}` : '' }}</code>
      </div>
      <InputText
        v-model="docEditor.category"
        :placeholder="t('common.category')"
      />
      <InputText
        v-model="docEditor.tags"
        :placeholder="t('common.tags')"
      />
      <Dropdown
        v-model="docEditor.status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('common.status')"
      />
      <div class="row">
        <Button
          :label="t('common.save')"
          icon="pi pi-save"
          :loading="docEditorSaving"
          @click="saveDocEditor"
        />
        <Button
          :label="t('common.close')"
          outlined
          severity="secondary"
          :disabled="docEditorSaving"
          @click="docEditorVisible = false"
        />
      </div>
    </div>
  </Dialog>

  <Dialog
    v-model:visible="photoEditorVisible"
    modal
    :header="t('docsPhotos.editPhoto')"
    class="workspace-dialog"
    :style="{ width: 'min(720px, calc(100vw - 32px))' }"
  >
    <div class="dialog-body stack-md">
      <div class="muted">
        <code>{{ photoEditor.id ? `photo:${photoEditor.id}` : '' }}</code>
      </div>
      <InputText
        v-model="photoEditor.tags"
        :placeholder="t('common.tags')"
      />
      <Textarea
        v-model="photoEditor.description"
        rows="2"
        :placeholder="t('common.description')"
      />
      <Dropdown
        v-model="photoEditor.status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('common.status')"
      />
      <div class="row">
        <Button
          :label="t('common.save')"
          icon="pi pi-save"
          :loading="photoEditorSaving"
          @click="savePhotoEditor"
        />
        <Button
          :label="t('common.close')"
          outlined
          severity="secondary"
          :disabled="photoEditorSaving"
          @click="photoEditorVisible = false"
        />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import { del, get, patch, post } from '../api'
import { apiPaths } from '../api/endpoints'
import { confirmDanger } from '../services/confirm'
import { downloadDocumentFile, downloadPhotoFile, previewDocumentFile, previewPhotoFile } from '../services/downloads'
import { t } from '../i18n'
import { useWorkspaceStore } from '../workspace-store'
import RelatedItemsPanel from './RelatedItemsPanel.vue'
import type {
  DocumentUpdateRequest,
  DocumentResponse,
  IndexRebuildResponse,
  IndexStatusResponse,
  MessageResponse,
  PhotoResponse,
  PhotoUpdateRequest,
  UploadDocumentResponse,
  UploadPhotoResponse,
} from '../types'

const toast = useToast()

const docInput = ref<HTMLInputElement | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)

const documents = ref<DocumentResponse[]>([])
const photos = ref<PhotoResponse[]>([])
const store = useWorkspaceStore()
const docFilterText = ref('')

const selectedDoc = ref<File | null>(null)
const uploadingDoc = ref(false)
const loadingDocs = ref(false)
const docCategory = ref('')
const docTags = ref('')

const selectedPhoto = ref<File | null>(null)
const uploadingPhoto = ref(false)
const loadingPhotos = ref(false)
const photoTags = ref('')
const photoDescription = ref('')

const selectedRelatedItemId = ref('')

const docEditorVisible = ref(false)
const docEditorSaving = ref(false)
const docEditor = ref<Pick<DocumentResponse, 'id' | 'category' | 'tags' | 'status'>>({ id: '', category: '', tags: '', status: 'reviewed' })

const photoEditorVisible = ref(false)
const photoEditorSaving = ref(false)
const photoEditor = ref<Pick<PhotoResponse, 'id' | 'tags' | 'description' | 'status'>>({ id: '', tags: '', description: '', status: 'reviewed' })

const statusOptions = computed(() => [
  { label: t('common.draft'), value: 'draft' },
  { label: t('common.reviewed'), value: 'reviewed' },
  { label: t('common.verified'), value: 'verified' },
  { label: t('common.archivedStatus'), value: 'archived' },
])

const filteredDocuments = computed(() => {
  const query = String(docFilterText.value || '').trim().toLowerCase()
  if (!query) {
    return documents.value
  }
  return documents.value.filter((doc) => {
    const haystack = `${doc.filename || ''} ${doc.category || ''} ${doc.tags || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})
const docLoadMessage = computed(() => store.state.error.documents || '')
const photoLoadMessage = computed(() => store.state.error.photos || '')
const showDocReloadWarning = computed(() => store.state.status.documents === 'error' && documents.value.length > 0)
const showPhotoReloadWarning = computed(() => store.state.status.photos === 'error' && photos.value.length > 0)
const indexStatus = ref<IndexStatusResponse | null>(null)
const searchStatusReady = computed(() => indexStatus.value?.provider?.index_mode === 'real_semantic_embedding')
const searchStatusMessage = computed(() => {
  const mode = indexStatus.value?.provider?.index_mode
  if (mode === 'real_semantic_embedding') {
    const provider = indexStatus.value?.provider.active_provider
    return provider === 'ollama' ? t('docsPhotos.semanticOllamaEnabled') : t('docsPhotos.semanticEnabled')
  }
  if (mode === 'demo_hash_embedding') {
    return t('docsPhotos.demoHashEnabled')
  }
  if (mode === 'full_text_only') {
    return t('docsPhotos.fullTextOnly')
  }
  if (mode === 'vector_degraded') {
    return t('docsPhotos.vectorDegraded')
  }
  return ''
})

function openDocPicker() {
  docInput.value?.click()
}

function openPhotoPicker() {
  photoInput.value?.click()
}

function onDocSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedDoc.value = target?.files?.[0] || null
}

function onPhotoSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  selectedPhoto.value = target?.files?.[0] || null
}

async function loadDocuments() {
  loadingDocs.value = true
  try {
    indexStatus.value = await get<IndexStatusResponse>(apiPaths.index.status)
    await store.refreshDocuments({ force: true })
    documents.value = store.state.lists.documents || []
  } catch (error: unknown) {
    documents.value = store.state.lists.documents || []
    const apiError = error as { message?: string }
    toast.add({
      severity: documents.value.length ? 'warn' : 'error',
      summary: t('workspace.documentsReloadFailed'),
      detail: apiError?.message || store.state.error.documents || t('common.requestFailed'),
      life: 4000,
    })
  } finally {
    loadingDocs.value = false
  }
}

async function uploadDoc() {
  if (!selectedDoc.value) {
    toast.add({ severity: 'warn', summary: t('docsPhotos.noFileSelected'), detail: t('docsPhotos.chooseDocumentToUpload'), life: 3000 })
    return
  }

  uploadingDoc.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedDoc.value)
    formData.append('category', docCategory.value || '')
    formData.append('tags', docTags.value || '')
    const response = await post<UploadDocumentResponse, FormData>(apiPaths.docs.upload, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const degraded = response.vector_index_status === 'degraded' || response.vector_index_status === 'disabled'
    toast.add({
      severity: degraded ? 'warn' : 'success',
      summary: degraded ? t('docsPhotos.uploadedWithFullTextFallback') : t('common.uploaded'),
      detail: response.user_message || response.message || t('docsPhotos.documentUploaded'),
      life: 3500,
    })
    selectedDoc.value = null
    if (docInput.value) {
      docInput.value.value = ''
    }
    docCategory.value = ''
    docTags.value = ''
    await loadDocuments()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.uploadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    uploadingDoc.value = false
  }
}

async function loadPhotos() {
  loadingPhotos.value = true
  try {
    await store.refreshPhotos({ force: true })
    photos.value = store.state.lists.photos || []
  } catch (error: unknown) {
    photos.value = store.state.lists.photos || []
    const apiError = error as { message?: string }
    toast.add({
      severity: photos.value.length ? 'warn' : 'error',
      summary: t('workspace.photosReloadFailed'),
      detail: apiError?.message || store.state.error.photos || t('common.requestFailed'),
      life: 4000,
    })
  } finally {
    loadingPhotos.value = false
  }
}

async function uploadPhoto() {
  if (!selectedPhoto.value) {
    toast.add({ severity: 'warn', summary: t('docsPhotos.noFileSelected'), detail: t('docsPhotos.chooseImageToUpload'), life: 3000 })
    return
  }

  uploadingPhoto.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedPhoto.value)
    formData.append('tags', photoTags.value || '')
    formData.append('description', photoDescription.value || '')
    const response = await post<UploadPhotoResponse, FormData>(apiPaths.photos.upload, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const ocrDegraded = response.ocr_status === 'failed' || response.ocr_status === 'unavailable'
    toast.add({
      severity: ocrDegraded ? 'warn' : 'success',
      summary: ocrDegraded ? t('docsPhotos.uploadedOcrUnavailable') : t('common.uploaded'),
      detail: response.message || t('docsPhotos.imageSaved'),
      life: 3500,
    })
    selectedPhoto.value = null
    if (photoInput.value) {
      photoInput.value.value = ''
    }
    photoTags.value = ''
    photoDescription.value = ''
    await loadPhotos()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.uploadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    uploadingPhoto.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadDocuments(), loadPhotos()])
})

function showPhotoReferences(photo: PhotoResponse) {
  if (!photo?.id) {
    return
  }
  selectedRelatedItemId.value = `photo:${photo.id}`
}

function showDocReferences(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  selectedRelatedItemId.value = `document:${doc.id}`
}

async function previewDocument(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  try {
    await previewDocumentFile(doc)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.previewFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function downloadDocument(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  try {
    await downloadDocumentFile(doc)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.downloadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

function openDocEditor(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  docEditor.value = {
    id: doc.id,
    category: doc.category || '',
    tags: doc.tags || '',
    status: doc.status || 'reviewed',
  }
  docEditorVisible.value = true
}

async function saveDocEditor() {
  if (!docEditor.value?.id) {
    return
  }
  docEditorSaving.value = true
  try {
    const payload: DocumentUpdateRequest = {
      category: String(docEditor.value.category || ''),
      tags: String(docEditor.value.tags || ''),
      status: docEditor.value.status || 'reviewed',
    }
    await patch<MessageResponse, DocumentUpdateRequest>(apiPaths.docs.detail(docEditor.value.id), payload)
    toast.add({ severity: 'success', summary: t('common.saved'), detail: t('docsPhotos.documentUpdated'), life: 2500 })
    docEditorVisible.value = false
    await loadDocuments()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    docEditorSaving.value = false
  }
}

async function archiveDocument(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  if (!(await confirmDanger({ header: t('docsPhotos.archiveDocument'), message: t('docsPhotos.archiveDocumentMessage', { filename: doc.filename }), acceptLabel: t('docsPhotos.archive') }))) {
    return
  }
  try {
    await patch<MessageResponse, DocumentUpdateRequest>(apiPaths.docs.detail(doc.id), { status: 'archived' })
    toast.add({ severity: 'success', summary: t('common.archived'), detail: t('docsPhotos.documentArchived'), life: 2500 })
    await loadDocuments()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.archiveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function deleteDocument(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  if (!(await confirmDanger({ header: t('docsPhotos.deleteDocument'), message: t('docsPhotos.deleteDocumentMessage', { filename: doc.filename }), acceptLabel: t('prompts.deleteAccept') }))) {
    return
  }
  try {
    await del<MessageResponse>(apiPaths.docs.detail(doc.id))
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('docsPhotos.documentDeleted'), life: 2500 })
    await loadDocuments()
    if (selectedRelatedItemId.value === `document:${doc.id}`) {
      selectedRelatedItemId.value = ''
    }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.deleteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function rebuildDocumentIndex(doc: DocumentResponse) {
  if (!doc?.id) {
    return
  }
  try {
    const response = await post<IndexRebuildResponse>(apiPaths.index.rebuildItem('document', doc.id))
    const failed = response.failed ?? 0
    const rebuilt = response.rebuilt ?? 0
    const item = response.items?.[0]
    const detail = response.message || (failed > 0 ? t('docsPhotos.rebuildDocumentFailed') : t('docsPhotos.rebuildDocumentDone'))
    toast.add({
      severity: failed > 0 ? 'warn' : 'success',
      summary: failed > 0 ? t('docsPhotos.rebuildNeedsAttention') : t('docsPhotos.indexRebuilt'),
      detail:
        item?.error && failed > 0
          ? `${detail} ${item.error}`
          : t('docsPhotos.rebuildDetail', { detail, provider: response.provider.active_provider, rebuilt, failed }),
      life: 4000,
    })
    await loadDocuments()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('settings.indexRebuildFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function previewPhoto(photo: PhotoResponse) {
  if (!photo?.id) {
    return
  }
  try {
    await previewPhotoFile(photo)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.previewFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function downloadPhoto(photo: PhotoResponse) {
  if (!photo?.id) {
    return
  }
  try {
    await downloadPhotoFile(photo)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.downloadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

function openPhotoEditor(photo: PhotoResponse) {
  if (!photo?.id) {
    return
  }
  photoEditor.value = {
    id: photo.id,
    tags: photo.tags || '',
    description: photo.description || '',
    status: photo.status || 'reviewed',
  }
  photoEditorVisible.value = true
}

async function savePhotoEditor() {
  if (!photoEditor.value?.id) {
    return
  }
  photoEditorSaving.value = true
  try {
    const payload: PhotoUpdateRequest = {
      tags: String(photoEditor.value.tags || ''),
      description: String(photoEditor.value.description || ''),
      status: photoEditor.value.status || 'reviewed',
    }
    await patch<MessageResponse, PhotoUpdateRequest>(apiPaths.photos.detail(photoEditor.value.id), payload)
    toast.add({ severity: 'success', summary: t('common.saved'), detail: t('docsPhotos.photoUpdated'), life: 2500 })
    photoEditorVisible.value = false
    await loadPhotos()
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    photoEditorSaving.value = false
  }
}

async function deletePhoto(photo: PhotoResponse) {
  if (!photo?.id) {
    return
  }
  if (!(await confirmDanger({ header: t('docsPhotos.deletePhoto'), message: t('docsPhotos.deletePhotoMessage', { filename: photo.filename }), acceptLabel: t('prompts.deleteAccept') }))) {
    return
  }
  try {
    await del<MessageResponse>(apiPaths.photos.detail(photo.id))
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('docsPhotos.photoDeleted'), life: 2500 })
    await loadPhotos()
    if (selectedRelatedItemId.value === `photo:${photo.id}`) {
      selectedRelatedItemId.value = ''
    }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.deleteFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.hidden-input {
  display: none;
}

.muted {
  color: #51606f;
  font-size: 13px;
}

.inline-status {
  margin: 0;
  color: #b45309;
  font-size: 13px;
}

.inline-status-warning {
  font-weight: 600;
}

.index-banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #8a4b08;
  font-size: 13px;
}

.index-banner-ok {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #047857;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.index-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
