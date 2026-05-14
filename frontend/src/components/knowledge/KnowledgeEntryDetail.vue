<template>
  <Card>
    <template #title>
      Quick add (Knowledge note)
    </template>
    <template #subtitle>
      Manually capture a problem / root cause / solution so it becomes searchable.
    </template>
    <template #content>
      <div class="stack-md">
        <InputText
          :model-value="entry.title"
          placeholder="Title (short)"
          @update:model-value="updateField('title', $event)"
        />
        <Textarea
          :model-value="entry.problem"
          rows="3"
          placeholder="Problem"
          @update:model-value="updateField('problem', $event)"
        />
        <Textarea
          :model-value="entry.root_cause"
          rows="3"
          placeholder="Root cause"
          @update:model-value="updateField('root_cause', $event)"
        />
        <Textarea
          :model-value="entry.solution"
          rows="4"
          placeholder="Solution (steps, commands, links)"
          @update:model-value="updateField('solution', $event)"
        />
        <InputText
          :model-value="entry.tags"
          placeholder="Tags (comma separated)"
          @update:model-value="updateField('tags', $event)"
        />
        <Textarea
          :model-value="entry.notes"
          rows="2"
          placeholder="Notes (optional)"
          @update:model-value="updateField('notes', $event)"
        />
        <div class="row">
          <Dropdown
            :model-value="entry.status"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            placeholder="Status"
            @update:model-value="updateField('status', $event)"
          />
          <Dropdown
            :model-value="entry.source_type"
            :options="sourceTypes"
            option-label="label"
            option-value="value"
            placeholder="Source type"
            @update:model-value="updateField('source_type', $event)"
          />
        </div>
        <InputText
          :model-value="entry.source_ref"
          placeholder="Source ref (optional, e.g. document:..., autotest_run:...)"
          @update:model-value="updateField('source_ref', $event)"
        />
        <Chips
          :model-value="entry.related_item_ids"
          separator=","
          placeholder="Related item IDs (comma-separated, e.g. document:..., photo:..., prompt:...)"
          @update:model-value="updateField('related_item_ids', $event)"
        />
        <div class="row">
          <Button
            label="Save"
            icon="pi pi-save"
            :loading="saving"
            @click="$emit('save')"
          />
          <Button
            label="Reset"
            outlined
            severity="secondary"
            :disabled="saving"
            @click="$emit('reset')"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chips from 'primevue/chips'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import type { KnowledgeEntryCreateRequest } from '../../types'

const props = defineProps<{
  entry: KnowledgeEntryCreateRequest
  saving: boolean
  sourceTypes: Array<{ label: string; value: string }>
  statusOptions: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  reset: []
  save: []
  'update:entry': [value: KnowledgeEntryCreateRequest]
}>()

function updateField<Key extends keyof KnowledgeEntryCreateRequest>(key: Key, value: KnowledgeEntryCreateRequest[Key]) {
  emit('update:entry', {
    ...props.entry,
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
</style>
