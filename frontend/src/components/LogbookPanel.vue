<template>
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
            />
          </div>
        </div>
      </template>
    </Card>
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
