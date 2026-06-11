<template>
  <div class="grid">
    <Card>
      <template #title>
        {{ t('activity.title') }}
      </template>
      <template #subtitle>
        {{ t('activity.subtitle') }}
      </template>
      <template #content>
        <div class="stack-md">
          <div class="row">
            <Button
              :label="t('common.refresh')"
              outlined
              icon="pi pi-refresh"
              :loading="loading"
              @click="load"
            />
            <InputText
              v-model="filterText"
              :placeholder="t('activity.filterPlaceholder')"
              class="filter"
            />
          </div>

          <DataTable
            :value="filtered"
            :loading="loading"
            class="kw-table"
            data-key="item_id"
            paginator
            :rows="10"
            scrollable
            scroll-height="flex"
            size="small"
            responsive-layout="scroll"
            :table-style="{ minWidth: '920px' }"
            @row-click="onRowClick"
          >
            <Column
              :header="t('common.type')"
              style="width: 8rem"
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
              style="width: 8rem"
            >
              <template #body="slotProps">
                <CellText :text="slotProps.data.status" />
              </template>
            </Column>
            <Column
              :header="t('common.source')"
              style="width: 8rem"
            >
              <template #body="slotProps">
                <CellText :text="slotProps.data.source" />
              </template>
            </Column>
            <Column
              :header="t('common.when')"
              style="width: 10rem"
            >
              <template #body="slotProps">
                <CellText
                  :text="formatDateTime(slotProps.data.when)"
                  :title="formatDateTime(slotProps.data.when)"
                />
              </template>
            </Column>
            <Column
              :header="t('common.item')"
              style="width: 14rem"
            >
              <template #body="slotProps">
                <CellText :text="slotProps.data.item_id" />
              </template>
            </Column>
            <template #empty>
              <EmptyStateBlock
                icon="pi pi-history"
                :title="t('activity.emptyTitle')"
                :description="t('activity.emptyDescription')"
              />
            </template>
          </DataTable>

          <RelatedItemsPanel
            v-if="selectedItemId"
            :item-id="selectedItemId"
          />
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'

import RelatedItemsPanel from './RelatedItemsPanel.vue'
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import CellText from './common/CellText.vue'
import { t } from '../i18n'
import { formatDateTime } from '../utils/date'
import { useWorkspaceStore } from '../workspace-store'

const store = useWorkspaceStore()
const loading = computed(() => store.anyLoading.value)
const filterText = ref('')

type ActivityRow = {
  kind: string
  title: string
  status: string
  source: string
  when: string
  item_id: string
}

const items = ref<ActivityRow[]>([])
const selectedItemId = ref('')

const filtered = computed(() => {
  const query = String(filterText.value || '').trim().toLowerCase()
  if (!query) {
    return items.value
  }
  return items.value.filter((item) => {
    const haystack = `${item.kind} ${item.title} ${item.status} ${item.source} ${item.item_id}`.toLowerCase()
    return haystack.includes(query)
  })
})

function normalizeWhen(value: string) {
  return String(value || '')
}

function byWhenDesc(a: ActivityRow, b: ActivityRow) {
  return String(b.when || '').localeCompare(String(a.when || ''))
}

async function load() {
  await store.refreshAll({ force: true })
  const { knowledgeEntries, logbookEntries, documents, photos, autotestRuns, prompts } = store.state.lists

  const mapped: ActivityRow[] = []

  for (const entry of knowledgeEntries || []) {
    mapped.push({
      kind: t('activity.knowledge'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('activity.knowledgeEntry'),
      status: entry.status || '',
      source: `${entry.source_type || ''}`.trim(),
      when: normalizeWhen(entry.updated_at || entry.created_at),
      item_id: `knowledge:${entry.id}`,
    })
  }
  for (const entry of logbookEntries || []) {
    mapped.push({
      kind: t('activity.logbook'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('activity.logbookEntry'),
      status: entry.status || '',
      source: `${entry.source_type || ''}`.trim(),
      when: normalizeWhen(entry.updated_at || entry.created_at),
      item_id: `logbook:${entry.id}`,
    })
  }
  for (const doc of documents || []) {
    mapped.push({
      kind: t('activity.document'),
      title: doc.filename || t('activity.document'),
      status: doc.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(doc.updated_at || doc.uploaded_at),
      item_id: `document:${doc.id}`,
    })
  }
  for (const photo of photos || []) {
    mapped.push({
      kind: t('activity.photo'),
      title: photo.filename || t('activity.photo'),
      status: photo.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(photo.updated_at || photo.created_at),
      item_id: `photo:${photo.id}`,
    })
  }
  for (const run of autotestRuns || []) {
    mapped.push({
      kind: t('activity.autotest'),
      title: run.project_name || run.id,
      status: run.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(run.created_at),
      item_id: `autotest_run:${run.id}`,
    })
  }
  for (const prompt of prompts || []) {
    mapped.push({
      kind: t('activity.prompt'),
      title: prompt.title || t('activity.prompt'),
      status: t('activity.saved'),
      source: t('activity.manual'),
      when: normalizeWhen(prompt.updated_at || prompt.created_at),
      item_id: `prompt:${prompt.id}`,
    })
  }

  items.value = mapped.sort(byWhenDesc)
}

function onRowClick(event: unknown) {
  const item = (event as { data?: ActivityRow } | null)?.data
  if (!item?.item_id) {
    return
  }
  selectedItemId.value = item.item_id
}

onMounted(load)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr;
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

.filter {
  min-width: min(520px, 100%);
}
</style>
