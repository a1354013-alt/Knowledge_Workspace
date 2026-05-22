<template>
  <Card>
    <template #title>
      Recent notes
    </template>
    <template #content>
      <div class="stack-md">
        <p
          v-if="loadMessage"
          class="inline-status"
          :class="{ 'inline-status-warning': showReloadWarning }"
        >
          {{ loadMessage }}
        </p>
        <Button
          label="Refresh"
          outlined
          icon="pi pi-refresh"
          :loading="loadingRecent"
          @click="$emit('refresh')"
        />
        <InputText
          :model-value="filterText"
          placeholder="Filter recent (title/tags/status)"
          @update:model-value="emitFilterText"
        />
        <DataTable
          :value="items"
          :loading="loadingRecent"
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
                  @click="$emit('edit', slotProps.data)"
                />
                <Button
                  icon="pi pi-sitemap"
                  text
                  severity="secondary"
                  @click="$emit('selectRelated', slotProps.data)"
                />
                <Button
                  icon="pi pi-archive"
                  text
                  severity="secondary"
                  @click="$emit('archive', slotProps.data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>

        <RelatedItemsPanel
          v-if="selectedRelatedItemId"
          :item-id="selectedRelatedItemId || ''"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'

import type { KnowledgeEntryResponse } from '../../types'
import RelatedItemsPanel from '../RelatedItemsPanel.vue'

defineProps<{
  filterText: string
  items: KnowledgeEntryResponse[]
  loadMessage: string
  loadingRecent: boolean
  selectedRelatedItemId: string
  showReloadWarning: boolean
}>()

const emit = defineEmits<{
  archive: [value: KnowledgeEntryResponse]
  edit: [value: KnowledgeEntryResponse]
  refresh: []
  selectRelated: [value: KnowledgeEntryResponse]
  'update:filterText': [value: string]
}>()

function emitFilterText(value: string | undefined) {
  emit('update:filterText', value || '')
}
</script>

<style scoped>
.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.inline-status {
  margin: 0;
  color: #b45309;
  font-size: 13px;
}

.inline-status-warning {
  font-weight: 600;
}
</style>
