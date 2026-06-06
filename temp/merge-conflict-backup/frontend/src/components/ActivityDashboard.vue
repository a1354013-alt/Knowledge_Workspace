<template>
  <div class="page-panel">
    <div class="page-heading">
      <h2>{{ t('activity.title') }}</h2>
      <p>{{ t('activity.subtitle') }}</p>
    </div>
    <Card>
<<<<<<< HEAD
=======
      <template #title>
        {{ t('activity.title') }}
      </template>
      <template #subtitle>
        {{ t('activity.subtitle') }}
      </template>
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
            data-key="item_id"
            size="small"
            responsive-layout="scroll"
            @row-click="onRowClick"
          >
            <Column
              field="kind"
<<<<<<< HEAD
              :header="t('activity.headers.type')"
            />
            <Column
              field="title"
              :header="t('activity.headers.title')"
            />
            <Column
              field="status"
              :header="t('activity.headers.status')"
            />
            <Column
              field="source"
              :header="t('activity.headers.source')"
            />
            <Column
              field="when"
              :header="t('activity.headers.when')"
            />
            <Column :header="t('activity.headers.item')">
=======
              :header="t('common.type')"
            />
            <Column
              field="title"
              :header="t('common.title')"
            />
            <Column
              field="status"
              :header="t('common.status')"
            />
            <Column
              field="source"
              :header="t('common.source')"
            />
            <Column
              field="when"
              :header="t('common.when')"
            />
            <Column :header="t('common.item')">
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
              <template #body="slotProps">
                <code>{{ slotProps.data.item_id }}</code>
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
<<<<<<< HEAD
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import { useI18n } from '../i18n'
=======
import { t } from '../i18n'
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
import { useWorkspaceStore } from '../workspace-store'

const store = useWorkspaceStore()
const { t } = useI18n()
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
  return String(value || '').replace('T', ' ').replace('Z', '')
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
<<<<<<< HEAD
      kind: t('activity.itemKinds.knowledge'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('nav.knowledge'),
=======
      kind: t('activity.knowledge'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('activity.knowledgeEntry'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
      status: entry.status || '',
      source: `${entry.source_type || ''}`.trim(),
      when: normalizeWhen(entry.updated_at || entry.created_at),
      item_id: `knowledge:${entry.id}`,
    })
  }
  for (const entry of logbookEntries || []) {
    mapped.push({
<<<<<<< HEAD
      kind: t('activity.itemKinds.logbook'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('nav.logbook'),
=======
      kind: t('activity.logbook'),
      title: entry.title || entry.problem?.slice?.(0, 80) || t('activity.logbookEntry'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
      status: entry.status || '',
      source: `${entry.source_type || ''}`.trim(),
      when: normalizeWhen(entry.updated_at || entry.created_at),
      item_id: `logbook:${entry.id}`,
    })
  }
  for (const doc of documents || []) {
    mapped.push({
<<<<<<< HEAD
      kind: t('activity.itemKinds.document'),
      title: doc.filename || t('docsPhotos.docsTitle'),
=======
      kind: t('activity.document'),
      title: doc.filename || t('activity.document'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
      status: doc.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(doc.updated_at || doc.uploaded_at),
      item_id: `document:${doc.id}`,
    })
  }
  for (const photo of photos || []) {
    mapped.push({
<<<<<<< HEAD
      kind: t('activity.itemKinds.photo'),
      title: photo.filename || t('docsPhotos.photosTitle'),
=======
      kind: t('activity.photo'),
      title: photo.filename || t('activity.photo'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
      status: photo.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(photo.updated_at || photo.created_at),
      item_id: `photo:${photo.id}`,
    })
  }
  for (const run of autotestRuns || []) {
    mapped.push({
<<<<<<< HEAD
      kind: t('activity.itemKinds.autotest'),
=======
      kind: t('activity.autotest'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
      title: run.project_name || run.id,
      status: run.status || '',
      source: t('activity.upload'),
      when: normalizeWhen(run.created_at),
      item_id: `autotest_run:${run.id}`,
    })
  }
  for (const prompt of prompts || []) {
    mapped.push({
<<<<<<< HEAD
      kind: t('activity.itemKinds.prompt'),
      title: prompt.title || t('nav.prompts'),
      status: 'saved',
      source: 'manual',
=======
      kind: t('activity.prompt'),
      title: prompt.title || t('activity.prompt'),
      status: t('activity.saved'),
      source: t('activity.manual'),
>>>>>>> 73c504053f9be15621bf36814ae5746e8fbe0f71
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
