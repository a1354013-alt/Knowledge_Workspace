<template>
  <Dialog
    :visible="visible"
    modal
    :header="t('logbook.editEntry')"
    :style="{ width: 'min(920px, 95vw)' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="stack-md">
      <InputText
        :model-value="editor.title"
        :placeholder="t('common.title')"
        @update:model-value="updateEditor('title', $event || '')"
      />
      <Textarea
        :model-value="editor.problem"
        rows="3"
        :placeholder="t('common.problem')"
        @update:model-value="updateEditor('problem', $event || '')"
      />
      <Textarea
        :model-value="editor.root_cause"
        rows="3"
        :placeholder="t('common.rootCause')"
        @update:model-value="updateEditor('root_cause', $event || '')"
      />
      <Textarea
        :model-value="editor.solution"
        rows="4"
        :placeholder="t('common.solution')"
        @update:model-value="updateEditor('solution', $event || '')"
      />
      <InputText
        :model-value="editor.tags"
        :placeholder="t('common.tags')"
        @update:model-value="updateEditor('tags', $event || '')"
      />
      <div class="row">
        <Dropdown
          :model-value="editor.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.status')"
          @update:model-value="updateEditor('status', $event)"
        />
        <Dropdown
          :model-value="editor.source_type"
          :options="sourceTypes"
          option-label="label"
          option-value="value"
          :placeholder="t('common.sourceType')"
          @update:model-value="updateEditor('source_type', $event)"
        />
      </div>
      <InputText
        :model-value="editor.source_ref"
        :placeholder="t('logbook.sourceRefOptional')"
        @update:model-value="updateEditor('source_ref', $event || '')"
      />
      <Chips
        :model-value="editor.related_item_ids"
        separator=","
        :placeholder="t('logbook.relatedItemIds')"
        @update:model-value="updateEditor('related_item_ids', $event)"
      />

      <div class="row">
        <Dropdown
          :model-value="pickerSelected"
          :options="pickerOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('logbook.addRelatedItem')"
          class="picker"
          @update:model-value="$emit('update:pickerSelected', $event || '')"
        />
        <Button
          :label="t('common.add')"
          icon="pi pi-plus"
          outlined
          :disabled="!pickerSelected"
          @click="$emit('addRelated')"
        />
      </div>

      <div class="row">
        <Button
          :label="t('common.saveChanges')"
          icon="pi pi-save"
          :loading="editorSaving"
          @click="$emit('save')"
        />
        <Button
          :label="t('common.close')"
          outlined
          severity="secondary"
          :disabled="editorSaving"
          @click="$emit('update:visible', false)"
        />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Chips from 'primevue/chips'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import { t } from '../../i18n'
import type { LogbookEntryCreateRequest } from '../../types'
import type { LogbookEditorModel } from './useLogbookEntries'

const props = defineProps<{
  editor: LogbookEditorModel
  editorSaving: boolean
  pickerOptions: Array<{ label: string; value: string }>
  pickerSelected: string
  sourceTypes: Array<{ label: string; value: string }>
  statusOptions: Array<{ label: string; value: string }>
  visible: boolean
}>()

const emit = defineEmits<{
  addRelated: []
  save: []
  'update:editor': [value: LogbookEditorModel]
  'update:pickerSelected': [value: string]
  'update:visible': [value: boolean]
}>()

function updateEditor<K extends keyof LogbookEntryCreateRequest>(key: K, value: LogbookEntryCreateRequest[K]) {
  emit('update:editor', { ...props.editor, [key]: value })
}
</script>

<style scoped>
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

.picker {
  min-width: min(520px, 100%);
}
</style>
