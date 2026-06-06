<template>
  <Card>
    <template #title>
      {{ t('knowledge.recentNotes') }}
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
          :label="t('common.refresh')"
          outlined
          icon="pi pi-refresh"
          :loading="loadingRecent"
          @click="$emit('refresh')"
        />
        <InputText
          :model-value="filterText"
<<<<<<< HEAD
          :placeholder="t('knowledge.recentFilter')"
=======
          :placeholder="t('knowledge.filterRecent')"
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
                  icon="pi pi-archive"
                  text
                  severity="secondary"
                  @click="$emit('archive', slotProps.data)"
                />
              </div>
            </template>
          </Column>
          <template #empty>
            <EmptyStateBlock
              icon="pi pi-book"
              :title="t('knowledge.emptyTitle')"
              :description="t('knowledge.emptyDescription')"
            />
          </template>
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

<<<<<<< HEAD
import { useI18n } from '../../i18n'
=======
import { t } from '../../i18n'
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
import type { KnowledgeEntryResponse } from '../../types'
import EmptyStateBlock from '../common/EmptyStateBlock.vue'
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

const { t } = useI18n()

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
