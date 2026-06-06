<template>
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
        @click="$emit('refresh')"
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
        :header="t('common.title')"
      />
      <Column
        field="tags"
        :header="t('common.tags')"
      />
      <Column
        field="source_type"
        :header="t('common.source')"
      />
      <Column
        field="source_ref"
        :header="t('common.sourceRef')"
      />
      <Column
        field="status"
        :header="t('common.status')"
      />
      <Column
        field="updated_at"
        :header="t('common.updated')"
      />
      <Column :header="t('common.actions')">
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
              icon="pi pi-check"
              text
              severity="success"
              @click="$emit('promote', slotProps.data)"
            />
            <Button
              icon="pi pi-trash"
              text
              severity="danger"
              @click="$emit('delete', slotProps.data)"
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

<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'

import { t } from '../../i18n'
import type { LogbookEntryResponse } from '../../types'
import RelatedItemsPanel from '../RelatedItemsPanel.vue'

defineProps<{
  entries: LogbookEntryResponse[]
  loadMessage: string
  loading: boolean
  selectedRelatedItemId: string
  showReloadWarning: boolean
}>()

defineEmits<{
  delete: [value: LogbookEntryResponse]
  edit: [value: LogbookEntryResponse]
  promote: [value: LogbookEntryResponse]
  refresh: []
  selectRelated: [value: LogbookEntryResponse]
}>()
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
