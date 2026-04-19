<template>
  <Card>
    <template #title>Global search</template>
    <template #subtitle>Keyword + filters across knowledge, logbook, documents, photos, prompts, and AutoTest runs.</template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <InputText v-model="query" placeholder="Keyword..." class="grow" @keyup.enter="runSearch" />
          <Button label="Search" icon="pi pi-search" :loading="loading" @click="runSearch" />
          <Button label="Clear" outlined severity="secondary" :disabled="loading" @click="reset" />
        </div>

        <div class="row">
          <MultiSelect
            v-model="selectedTypes"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            placeholder="Types"
            display="chip"
            class="types"
          />
          <Dropdown v-model="statusFilter" :options="statusOptions" option-label="label" option-value="value" placeholder="Status" class="status" />
          <InputText v-model="tag" placeholder="Tag contains..." class="tag" />
        </div>

        <div class="row">
          <InputText v-model="dateFrom" placeholder="Date from (YYYY-MM-DD)" class="date" />
          <InputText v-model="dateTo" placeholder="Date to (YYYY-MM-DD)" class="date" />
          <Dropdown v-model="limit" :options="limitOptions" option-label="label" option-value="value" placeholder="Limit" class="limit" />
        </div>

        <DataTable :value="results" :loading="loading" data-key="item_id" size="small" responsive-layout="scroll">
          <Column field="item_type" header="Type" />
          <Column field="title" header="Title" />
          <Column field="status" header="Status" />
          <Column field="updated_at" header="Updated" />
          <Column header="Item">
            <template #body="slotProps">
              <code>{{ slotProps.data.item_id }}</code>
            </template>
          </Column>
          <Column header="Actions">
            <template #body="slotProps">
              <div class="actions-inline">
                <Button icon="pi pi-sitemap" text severity="secondary" @click="selectRelated(slotProps.data)" />
                <Button icon="pi pi-copy" text severity="secondary" @click="copyId(slotProps.data)" />
              </div>
            </template>
          </Column>
        </DataTable>

        <RelatedItemsPanel v-if="selectedItemId" :item-id="selectedItemId" />
      </div>
    </template>
  </Card>
</template>

<script setup>
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'

import { apiClient } from '../api'
import RelatedItemsPanel from './RelatedItemsPanel.vue'

const toast = useToast()

const loading = ref(false)
const results = ref([])
const selectedItemId = ref('')

const query = ref('')
const selectedTypes = ref([])
const statusFilter = ref('')
const tag = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const limit = ref(200)

const typeOptions = [
  { label: 'Knowledge', value: 'knowledge' },
  { label: 'Logbook', value: 'logbook' },
  { label: 'Documents', value: 'document' },
  { label: 'Photos', value: 'photo' },
  { label: 'Prompts', value: 'prompt' },
  { label: 'AutoTest runs', value: 'autotest_run' },
]

const statusOptions = [
  { label: 'Any', value: '' },
  { label: 'Draft', value: 'draft' },
  { label: 'Reviewed', value: 'reviewed' },
  { label: 'Verified', value: 'verified' },
  { label: 'Archived', value: 'archived' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Passed', value: 'passed' },
  { label: 'Failed', value: 'failed' },
]

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
}

function selectRelated(item) {
  if (!item?.item_id) {
    return
  }
  selectedItemId.value = item.item_id
}

function copyId(item) {
  const value = String(item?.item_id || '').trim()
  if (!value) {
    return
  }
  navigator.clipboard?.writeText(value)
  toast.add({ severity: 'success', summary: 'Copied', detail: value, life: 1500 })
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
    const response = await apiClient.get('/api/search', { params })
    results.value = response.items || []
  } catch (error) {
    results.value = []
    toast.add({ severity: 'error', summary: 'Search failed', detail: error.message, life: 4000 })
  } finally {
    loading.value = false
  }
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

