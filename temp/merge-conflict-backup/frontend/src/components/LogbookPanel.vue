<template>
<<<<<<< HEAD
  <div class="page-panel">
    <div class="page-heading">
      <h2>{{ t('logbook.title') }}</h2>
      <p>{{ t('logbook.subtitle') }}</p>
    </div>

    <div class="grid">
      <Card>
        <template #content>
          <div class="stack-md">
            <p
              v-if="loadMessage"
              class="inline-status"
              :class="{ 'inline-status-warning': showReloadWarning }"
            >
              {{ loadMessage }}
            </p>
            <div class="row">
              <Button
                :label="t('common.refresh')"
                outlined
                icon="pi pi-refresh"
                :loading="loading"
                @click="loadEntries"
              />
            </div>
            <DataTable
              :value="entries"
              :loading="loading"
              data-key="id"
              size="small"
              responsive-layout="scroll"
            >
              <Column
                field="title"
                header="Title"
              />
              <Column
                field="tags"
                header="Tags"
              />
              <Column
                field="source_type"
                header="Source"
              />
              <Column
                field="source_ref"
                header="Source ref"
              />
              <Column
                field="status"
                header="Status"
              />
              <Column
                field="updated_at"
                header="Updated"
              />
              <Column header="Actions">
                <template #body="slotProps">
                  <div class="actions-inline">
                    <Button
                      icon="pi pi-pencil"
                      text
                      severity="secondary"
                      @click="openEditor(slotProps.data)"
                    />
                    <Button
                      icon="pi pi-sitemap"
                      text
                      severity="secondary"
                      @click="selectForRelated(slotProps.data)"
                    />
                    <Button
                      icon="pi pi-check"
                      text
                      severity="success"
                      @click="promoteEntry(slotProps.data)"
                    />
                    <Button
                      icon="pi pi-trash"
                      text
                      severity="danger"
                      @click="deleteEntry(slotProps.data)"
                    />
                  </div>
                </template>
              </Column>
              <template #empty>
                <EmptyStateBlock
                  icon="pi pi-file-edit"
                  :title="t('logbook.emptyTitle')"
                  :description="t('logbook.emptyDescription')"
                />
              </template>
            </DataTable>

            <RelatedItemsPanel
              v-if="selectedRelatedItemId"
              :item-id="selectedRelatedItemId"
=======
  <div class="grid">
    <Card>
      <template #title>
        {{ t('logbook.pageTitle') }}
      </template>
      <template #subtitle>
        {{ t('logbook.pageSubtitle') }}
      </template>
      <template #content>
        <LogbookEntryList
          :entries="entries"
          :load-message="loadMessage"
          :loading="loading"
          :selected-related-item-id="selectedRelatedItemId"
          :show-reload-warning="showReloadWarning"
          @refresh="loadEntries"
          @edit="openEditor"
          @select-related="selectForRelated"
          @promote="promoteEntry"
          @delete="deleteEntry"
        />
      </template>
    </Card>

    <Card>
      <template #title>
        {{ t('logbook.addEntry') }}
      </template>
      <template #content>
        <div class="stack-md">
          <InputText
            v-model="form.title"
            :placeholder="t('common.title')"
          />
          <Textarea
            v-model="form.problem"
            rows="3"
            :placeholder="t('common.problem')"
          />
          <Textarea
            v-model="form.root_cause"
            rows="3"
            :placeholder="t('common.rootCause')"
          />
          <Textarea
            v-model="form.solution"
            rows="4"
            :placeholder="t('common.solution')"
          />
          <InputText
            v-model="form.tags"
            :placeholder="t('prompts.tagsPlaceholder')"
          />
          <Dropdown
            v-model="form.status"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('common.status')"
          />
          <Dropdown
            v-model="form.source_type"
            :options="sourceTypes"
            option-label="label"
            option-value="value"
            :placeholder="t('common.sourceType')"
          />
          <InputText
            v-model="form.source_ref"
            :placeholder="t('knowledge.sourceRefFull')"
          />
          <Chips
            v-model="form.related_item_ids"
            separator=","
            :placeholder="t('knowledge.relatedItemIdsFull')"
          />
          <div class="row">
            <Button
              :label="t('common.save')"
              icon="pi pi-save"
              :loading="saving"
              @click="saveEntry"
            />
            <Button
              :label="t('common.reset')"
              outlined
              severity="secondary"
              :disabled="saving"
              @click="resetForm"
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
            />
          </div>
        </template>
      </Card>

      <Card>
        <template #title>
          {{ t('logbook.addEntry') }}
        </template>
        <template #content>
          <div class="stack-md">
            <InputText
              v-model="form.title"
              placeholder="Title"
            />
            <Textarea
              v-model="form.problem"
              rows="3"
              placeholder="Problem"
            />
            <Textarea
              v-model="form.root_cause"
              rows="3"
              placeholder="Root cause"
            />
            <Textarea
              v-model="form.solution"
              rows="4"
              placeholder="Solution"
            />
            <InputText
              v-model="form.tags"
              placeholder="Tags (comma separated)"
            />
            <Dropdown
              v-model="form.status"
              :options="statusOptions"
              option-label="label"
              option-value="value"
              placeholder="Status"
            />
            <Dropdown
              v-model="form.source_type"
              :options="sourceTypes"
              option-label="label"
              option-value="value"
              placeholder="Source type"
            />
            <InputText
              v-model="form.source_ref"
              placeholder="Source ref (optional, e.g. doc:..., autotest_run:...)"
            />
            <Chips
              v-model="form.related_item_ids"
              separator=","
              placeholder="Related item IDs (comma-separated, e.g. document:..., photo:..., prompt:...)"
            />
            <div class="row">
              <Button
                label="Save"
                icon="pi pi-save"
                :loading="saving"
                @click="saveEntry"
              />
              <Button
                label="Reset"
                outlined
                severity="secondary"
                :disabled="saving"
                @click="resetForm"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>

  <LogbookEntryEditorDialog
    :visible="editorVisible"
    :editor="editor"
    :editor-saving="editorSaving"
    :picker-options="pickerOptions"
    :picker-selected="pickerSelected"
    :source-types="sourceTypes"
    :status-options="statusOptions"
    @update:editor="updateEditor"
    @update:picker-selected="updatePickerSelected"
    @update:visible="updateEditorVisible"
    @add-related="addPickedRelated"
    @save="saveEditor"
  />
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chips from 'primevue/chips'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

<<<<<<< HEAD
import { del, patch, post } from '../api'
import { apiPaths } from '../api/endpoints'
import { useI18n } from '../i18n'
import { confirmDanger } from '../services/confirm'
import { useWorkspaceStore } from '../workspace-store'
import type {
  AutoTestRunListItemResponse,
  DocumentResponse,
  KnowledgeEntryResponse,
  LogbookEntryCreateRequest,
  LogbookEntryResponse,
  LogbookEntryUpdateRequest,
  MessageResponse,
  PhotoResponse,
  PromoteToKnowledgeResponse,
  SavedPromptResponse,
} from '../types'
import RelatedItemsPanel from './RelatedItemsPanel.vue'
import EmptyStateBlock from './common/EmptyStateBlock.vue'

const toast = useToast()
const { t } = useI18n()
=======
import { t } from '../i18n'
import type { LogbookEntryCreateRequest } from '../types'
import LogbookEntryEditorDialog from './logbook/LogbookEntryEditorDialog.vue'
import LogbookEntryList from './logbook/LogbookEntryList.vue'
import { useLogbookEntries } from './logbook/useLogbookEntries'

const {
  addPickedRelated,
  deleteEntry,
  editor,
  editorSaving,
  editorVisible,
  entries,
  form,
  loadEntries,
  loadMessage,
  loading,
  openEditor,
  pickerOptions,
  pickerSelected,
  promoteEntry,
  resetForm,
  saveEditor,
  saveEntry,
  saving,
  selectForRelated,
  selectedRelatedItemId,
  showReloadWarning,
  sourceTypes,
  statusOptions,
} = useLogbookEntries()
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71

function updateEditor(value: LogbookEntryCreateRequest & { id: string }) {
  editor.value = value
}

function updatePickerSelected(value: string) {
  pickerSelected.value = value
}

function updateEditorVisible(value: boolean) {
  editorVisible.value = value
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1.35fr 0.65fr;
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

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
