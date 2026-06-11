<template>
  <div class="kw-table-panel">
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
      class="kw-table"
      data-key="id"
      paginator
      :rows="8"
      scrollable
      scroll-height="flex"
      size="small"
      responsive-layout="scroll"
      :table-style="{ minWidth: '980px' }"
    >
      <Column
        :header="t('common.title')"
        style="width: 18rem"
      >
        <template #body="slotProps">
          <CellText :text="slotProps.data.title || slotProps.data.problem" />
        </template>
      </Column>
      <Column
        :header="t('common.tags')"
        style="width: 14rem"
      >
        <template #body="slotProps">
          <span
            class="kw-chip-list"
            :title="slotProps.data.tags || ''"
          >
            <span
              v-for="tag in visibleTags(slotProps.data.tags)"
              :key="tag"
              class="kw-chip"
            >{{ tag }}</span>
            <span
              v-if="hiddenTagCount(slotProps.data.tags) > 0"
              class="kw-chip"
            >+{{ hiddenTagCount(slotProps.data.tags) }}</span>
            <CellText
              v-if="!visibleTags(slotProps.data.tags).length"
              text="-"
              muted
            />
          </span>
        </template>
      </Column>
      <Column
        field="source_type"
        :header="t('common.source')"
        style="width: 8rem"
      />
      <Column
        :header="t('common.sourceRef')"
        style="width: 5rem"
      >
        <template #body="slotProps">
          <span
            class="kw-icon-cell"
            :title="slotProps.data.source_ref || '-'"
          >
            <i
              class="pi pi-link"
              aria-hidden="true"
            />
          </span>
        </template>
      </Column>
      <Column
        field="status"
        :header="t('common.status')"
        style="width: 8rem"
      />
      <Column
        :header="t('common.updated')"
        style="width: 10rem"
      >
        <template #body="slotProps">
          <CellText
            :text="formatDateTime(slotProps.data.updated_at)"
            :title="formatDateTime(slotProps.data.updated_at)"
          />
        </template>
      </Column>
      <Column
        :header="t('common.actions')"
        style="width: 9rem"
      >
        <template #body="slotProps">
          <div class="kw-actions-inline">
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
import { formatDateTime } from '../../utils/date'
import CellText from '../common/CellText.vue'
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

function parseTags(value: string | null | undefined): string[] {
  return String(value || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

function visibleTags(value: string | null | undefined): string[] {
  return parseTags(value).slice(0, 2)
}

function hiddenTagCount(value: string | null | undefined): number {
  return Math.max(0, parseTags(value).length - 2)
}
</script>

<style scoped>
.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
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
