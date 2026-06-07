<template>
  <Card>
    <template #title>
      {{ t('search.title') }}
    </template>
    <template #subtitle>
      {{ t('search.subtitle') }}
    </template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <InputText
            v-model="query"
            :placeholder="t('search.keyword')"
            class="grow"
            @keyup.enter="runSearch"
          />
          <Button
            :label="t('search.search')"
            icon="pi pi-search"
            :loading="loading"
            @click="runSearch"
          />
          <Button
            :label="t('search.clear')"
            outlined
            severity="secondary"
            :disabled="loading"
            @click="reset"
          />
        </div>

        <div class="row">
          <MultiSelect
            v-model="selectedTypes"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('search.types')"
            display="chip"
            class="types"
          />
          <Dropdown
            v-model="statusFilter"
            :options="statusOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('common.status')"
            class="status"
          />
          <InputText
            v-model="tag"
            :placeholder="t('search.tagContains')"
            class="tag"
          />
        </div>

        <div class="row">
          <InputText
            v-model="dateFrom"
            :placeholder="t('search.dateFrom')"
            class="date"
          />
          <InputText
            v-model="dateTo"
            :placeholder="t('search.dateTo')"
            class="date"
          />
          <Dropdown
            v-model="limit"
            :options="limitOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('search.limit')"
            class="limit"
          />
        </div>

        <DataTable
          :value="results"
          :loading="loading"
          data-key="item_id"
          size="small"
          responsive-layout="scroll"
        >
          <Column
            field="item_type"
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
            field="updated_at"
            :header="t('common.updated')"
          />
          <Column :header="t('common.item')">
            <template #body="slotProps">
              <code>{{ slotProps.data.item_id }}</code>
            </template>
          </Column>
          <Column :header="t('common.actions')">
            <template #body="slotProps">
              <div class="actions-inline">
                <Button
                  icon="pi pi-sitemap"
                  text
                  severity="secondary"
                  @click="selectRelated(slotProps.data)"
                />
                <Button
                  icon="pi pi-copy"
                  text
                  severity="secondary"
                  @click="copyId(slotProps.data)"
                />
              </div>
            </template>
          </Column>
          <template #empty>
            <EmptyStateBlock
              icon="pi pi-search"
              :title="query ? t('search.emptyTitle') : t('search.idleTitle')"
              :description="query ? t('search.emptyDescription') : t('search.idleDescription')"
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
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'

import { get } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import { useWorkspaceNavigation } from '../workspace-navigation'
import EmptyStateBlock from './common/EmptyStateBlock.vue'
import RelatedItemsPanel from './RelatedItemsPanel.vue'
import type { ItemSummary, ResolveItemsResponse } from '../types'

const toast = useToast()
const { clearSearchDraft, searchDraft } = useWorkspaceNavigation()

const loading = ref(false)
const results = ref<ItemSummary[]>([])
const selectedItemId = ref('')

const query = ref('')
const selectedTypes = ref<string[]>([])
const statusFilter = ref('')
const tag = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const limit = ref(200)

const typeOptions = computed(() => [
  { label: t('search.knowledge'), value: 'knowledge' },
  { label: t('search.logbook'), value: 'logbook' },
  { label: t('search.documents'), value: 'document' },
  { label: t('search.photos'), value: 'photo' },
  { label: t('workspace.prompts'), value: 'prompt' },
  { label: t('search.autotestRuns'), value: 'autotest_run' },
])

const statusOptions = computed(() => [
  { label: t('search.any'), value: '' },
  { label: t('common.draft'), value: 'draft' },
  { label: t('common.reviewed'), value: 'reviewed' },
  { label: t('common.verified'), value: 'verified' },
  { label: t('common.archivedStatus'), value: 'archived' },
  { label: t('common.queued'), value: 'queued' },
  { label: t('common.running'), value: 'running' },
  { label: t('common.passed'), value: 'passed' },
  { label: t('common.failed'), value: 'failed' },
])

const limitOptions = [
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: '200', value: 200 },
  { label: '500', value: 500 },
]

function reset() {
  query.value = ''
  selectedTypes.value = []
  statusFilter.value = ''
  tag.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  limit.value = 200
  results.value = []
  selectedItemId.value = ''
  clearSearchDraft()
}

function selectRelated(item: ItemSummary) {
  if (!item?.item_id) {
    return
  }
  selectedItemId.value = item.item_id
}

function copyId(item: ItemSummary) {
  const value = String(item?.item_id || '').trim()
  if (!value) {
    return
  }
  navigator.clipboard?.writeText(value)
  toast.add({ severity: 'success', summary: t('common.copied'), detail: value, life: 1500 })
}

async function runSearch() {
  loading.value = true
  selectedItemId.value = ''
  try {
    const params = {
      q: String(query.value || '').trim(),
      types: (selectedTypes.value || []).join(','),
      status_filter: String(statusFilter.value || ''),
      tag: String(tag.value || '').trim(),
      date_from: String(dateFrom.value || '').trim(),
      date_to: String(dateTo.value || '').trim(),
      limit: Number(limit.value || 200),
    }
    const response = await get<ResolveItemsResponse>(apiPaths.search.resolve, { params })
    results.value = response.items || []
  } catch (error: unknown) {
    results.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('search.searchFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  } finally {
    loading.value = false
  }
}

async function consumePendingSearchQuery() {
  const nextQuery = String(searchDraft.value || '').trim()
  if (!nextQuery) {
    return
  }
  query.value = nextQuery
  clearSearchDraft()
  await runSearch()
}

watch(searchDraft, () => {
  void consumePendingSearchQuery()
})

onMounted(() => {
  void consumePendingSearchQuery()
})
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

.grow {
  flex: 1;
  min-width: min(320px, 100%);
}

.types {
  min-width: min(520px, 100%);
}

.status {
  min-width: 200px;
}

.tag {
  min-width: min(280px, 100%);
}

.date {
  min-width: 220px;
}

.limit {
  min-width: 140px;
}

.actions-inline {
  display: flex;
  gap: 6px;
}
</style>
