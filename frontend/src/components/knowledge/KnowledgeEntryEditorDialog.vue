<template>
  <Dialog
    :visible="visible"
    modal
    :header="t('knowledge.editEntry')"
    :style="{ width: 'min(920px, 95vw)' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="stack-md">
      <InputText
        :model-value="editor.title"
        :placeholder="t('common.title')"
        @update:model-value="updateField('title', $event)"
      />
      <Textarea
        :model-value="editor.problem"
        rows="3"
        :placeholder="t('common.problem')"
        @update:model-value="updateField('problem', $event)"
      />
      <Textarea
        :model-value="editor.root_cause"
        rows="3"
        :placeholder="t('common.rootCause')"
        @update:model-value="updateField('root_cause', $event)"
      />
      <Textarea
        :model-value="editor.solution"
        rows="4"
        :placeholder="t('common.solution')"
        @update:model-value="updateField('solution', $event)"
      />
      <InputText
        :model-value="editor.tags"
        :placeholder="t('common.tags')"
        @update:model-value="updateField('tags', $event)"
      />
      <Textarea
        :model-value="editor.notes"
        rows="2"
        :placeholder="t('common.notes')"
        @update:model-value="updateField('notes', $event)"
      />
      <div class="row">
        <Dropdown
          :model-value="editor.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.status')"
          @update:model-value="updateField('status', $event)"
        />
        <Dropdown
          :model-value="editor.source_type"
          :options="sourceTypes"
          option-label="label"
          option-value="value"
          :placeholder="t('common.sourceType')"
          @update:model-value="updateField('source_type', $event)"
        />
      </div>
      <InputText
        :model-value="editor.source_ref"
        :placeholder="t('knowledge.sourceRefFull')"
        @update:model-value="updateField('source_ref', $event)"
      />
      <Chips
        :model-value="editor.related_item_ids"
        separator=","
        :placeholder="t('knowledge.relatedItemIds')"
        @update:model-value="updateField('related_item_ids', $event)"
      />

      <div class="row">
        <Dropdown
          :model-value="pickerSelected"
          :options="pickerOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('knowledge.addRelatedItem')"
          class="picker"
          @update:model-value="$emit('update:pickerSelected', $event)"
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
import type { KnowledgeEntryCreateRequest } from '../../types'

type KnowledgeEditorModel = KnowledgeEntryCreateRequest & { id: string }

const props = defineProps<{
  editor: KnowledgeEditorModel
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
  'update:editor': [value: KnowledgeEditorModel]
  'update:pickerSelected': [value: string]
  'update:visible': [value: boolean]
}>()

function updateField<Key extends keyof KnowledgeEditorModel>(key: Key, value: KnowledgeEditorModel[Key]) {
  emit('update:editor', {
    ...props.editor,
    [key]: value,
  })
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
