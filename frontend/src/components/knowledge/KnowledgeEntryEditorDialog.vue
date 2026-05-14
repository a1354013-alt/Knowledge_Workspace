<template>
  <Dialog
    :visible="visible"
    modal
    header="Edit knowledge entry"
    :style="{ width: 'min(920px, 95vw)' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="stack-md">
      <InputText
        :model-value="editor.title"
        placeholder="Title"
        @update:model-value="updateField('title', $event)"
      />
      <Textarea
        :model-value="editor.problem"
        rows="3"
        placeholder="Problem"
        @update:model-value="updateField('problem', $event)"
      />
      <Textarea
        :model-value="editor.root_cause"
        rows="3"
        placeholder="Root cause"
        @update:model-value="updateField('root_cause', $event)"
      />
      <Textarea
        :model-value="editor.solution"
        rows="4"
        placeholder="Solution"
        @update:model-value="updateField('solution', $event)"
      />
      <InputText
        :model-value="editor.tags"
        placeholder="Tags"
        @update:model-value="updateField('tags', $event)"
      />
      <Textarea
        :model-value="editor.notes"
        rows="2"
        placeholder="Notes"
        @update:model-value="updateField('notes', $event)"
      />
      <div class="row">
        <Dropdown
          :model-value="editor.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Status"
          @update:model-value="updateField('status', $event)"
        />
        <Dropdown
          :model-value="editor.source_type"
          :options="sourceTypes"
          option-label="label"
          option-value="value"
          placeholder="Source type"
          @update:model-value="updateField('source_type', $event)"
        />
      </div>
      <InputText
        :model-value="editor.source_ref"
        placeholder="Source ref (optional, e.g. document:..., autotest_run:...)"
        @update:model-value="updateField('source_ref', $event)"
      />
      <Chips
        :model-value="editor.related_item_ids"
        separator=","
        placeholder="Related item IDs (comma-separated)"
        @update:model-value="updateField('related_item_ids', $event)"
      />

      <div class="row">
        <Dropdown
          :model-value="pickerSelected"
          :options="pickerOptions"
          option-label="label"
          option-value="value"
          placeholder="Add related item..."
          class="picker"
          @update:model-value="$emit('update:pickerSelected', $event)"
        />
        <Button
          label="Add"
          icon="pi pi-plus"
          outlined
          :disabled="!pickerSelected"
          @click="$emit('addRelated')"
        />
      </div>

      <div class="row">
        <Button
          label="Save changes"
          icon="pi pi-save"
          :loading="editorSaving"
          @click="$emit('save')"
        />
        <Button
          label="Close"
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
