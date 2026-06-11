<template>
  <Card>
    <template #title>
      {{ t('recentItems.title') }}
    </template>
    <template #subtitle>
      {{ t('recentItems.subtitle') }}
    </template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <Button
            :label="t('common.refresh')"
            icon="pi pi-refresh"
            outlined
            :loading="loading"
            @click="refresh"
          />
        </div>

        <EmptyStateBlock
          v-if="!items.length"
          icon="pi pi-history"
          :title="t('recentItems.emptyTitle')"
          :description="t('recentItems.emptyDescription')"
        />

        <DataTable
          v-else
          :value="items"
          class="kw-table"
          paginator
          :rows="8"
          scrollable
          scroll-height="flex"
          size="small"
          responsive-layout="scroll"
          :table-style="{ minWidth: '720px' }"
        >
          <Column
            :header="t('common.type')"
            style="width: 9rem"
          >
            <template #body="slotProps">
              <CellText :text="slotProps.data.kind" />
            </template>
          </Column>
          <Column
            :header="t('common.title')"
            style="width: 18rem"
          >
            <template #body="slotProps">
              <CellText :text="slotProps.data.title" />
            </template>
          </Column>
          <Column
            :header="t('common.status')"
            style="width: 9rem"
          >
            <template #body="slotProps">
              <CellText :text="slotProps.data.status" />
            </template>
          </Column>
          <Column
            :header="t('common.updated')"
            style="width: 10rem"
          >
            <template #body="slotProps">
              <CellText
                :text="formatDateTime(slotProps.data.updatedAt)"
                :title="formatDateTime(slotProps.data.updatedAt)"
              />
            </template>
          </Column>
        </DataTable>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'

import { t } from '../i18n'
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import CellText from './common/CellText.vue'
import { formatDateTime } from '../utils/date'
import { useWorkspaceStore } from '../workspace-store'

type RecentItem = {
  kind: string
  title: string
  status: string
  updatedAt: string
}

const store = useWorkspaceStore()
const loading = computed(() => store.anyLoading.value)

const items = computed<RecentItem[]>(() => {
  const rows: RecentItem[] = []

  for (const entry of store.state.lists.knowledgeEntries.slice(0, 3)) {
    rows.push({
      kind: t('nav.knowledge'),
      title: entry.title || entry.problem || '-',
      status: entry.status || '-',
      updatedAt: entry.updated_at || entry.created_at || '',
    })
  }

  for (const entry of store.state.lists.logbookEntries.slice(0, 3)) {
    rows.push({
      kind: t('nav.logbook'),
      title: entry.title || entry.problem || '-',
      status: entry.status || '-',
      updatedAt: entry.updated_at || entry.created_at || '',
    })
  }

  for (const entry of store.state.lists.prompts.slice(0, 2)) {
    rows.push({
      kind: t('nav.prompts'),
      title: entry.title || '-',
      status: t('prompts.savedState'),
      updatedAt: entry.updated_at || entry.created_at || '',
    })
  }

  return rows
    .sort((left, right) => String(right.updatedAt || '').localeCompare(String(left.updatedAt || '')))
    .slice(0, 8)
})

async function refresh() {
  await store.refreshAll({ force: true })
}

onMounted(refresh)
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
  flex-wrap: wrap;
}
</style>
