<template>
  <Card>
    <template #title>
      {{ t('related.title') }}
    </template>
    <template
      v-if="itemId"
      #subtitle
    >
      {{ t('related.subtitle', { itemId }) }}
    </template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <Button
            :label="t('common.refresh')"
            outlined
            icon="pi pi-refresh"
            :loading="loading"
            :disabled="!itemId"
            @click="load"
          />
          <span
            v-if="!itemId"
            class="muted"
          >{{ t('related.emptyPrompt') }}</span>
        </div>

        <DataTable
          v-if="itemId"
          :value="links"
          :loading="loading"
          class="kw-table"
          data-key="link_id"
          paginator
          :rows="8"
          scrollable
          scroll-height="flex"
          size="small"
          responsive-layout="scroll"
          :table-style="{ minWidth: '760px' }"
        >
          <Column
            field="created_at"
            :header="t('common.when')"
            style="width: 10rem"
          >
            <template #body="slotProps">
              <CellText
                :text="formatDateTime(slotProps.data.created_at)"
                :title="formatDateTime(slotProps.data.created_at)"
              />
            </template>
          </Column>
          <Column
            field="link_type"
            :header="t('common.type')"
            style="width: 10rem"
          >
            <template #body="slotProps">
              <CellText :text="slotProps.data.link_type" />
            </template>
          </Column>
          <Column
            :header="t('related.relatedItem')"
            style="width: 24rem"
          >
            <template #body="slotProps">
              <div class="stack-xs">
                <strong>{{ slotProps.data?.other_item?.title || displayOtherId(slotProps.data) }}</strong>
                <div class="muted">
                  <span>{{ slotProps.data?.other_item?.item_type || t('common.unknown') }}</span>
                  <span class="sep">·</span>
                  <code>{{ displayOtherId(slotProps.data) }}</code>
                  <span
                    v-if="slotProps.data?.other_item?.status"
                    class="sep"
                  >·</span>
                  <span v-if="slotProps.data?.other_item?.status">{{ slotProps.data.other_item.status }}</span>
                </div>
              </div>
            </template>
          </Column>
          <Column
            :header="t('common.actions')"
            style="width: 6rem"
          >
            <template #body="slotProps">
              <div class="kw-actions-inline">
                <Button
                  icon="pi pi-copy"
                  text
                  severity="secondary"
                  @click="copyOtherId(slotProps.data)"
                />
                <Button
                  v-if="isDownloadable(slotProps.data?.other_item?.item_id)"
                  icon="pi pi-download"
                  text
                  severity="secondary"
                  @click="downloadRelated(slotProps.data.other_item.item_id)"
                />
                <Button
                  v-if="isPreviewable(slotProps.data?.other_item?.item_id)"
                  icon="pi pi-eye"
                  text
                  severity="secondary"
                  @click="previewRelated(slotProps.data.other_item.item_id)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'

import { get } from '../api'
import { apiPaths } from '../api/endpoints'
import { t } from '../i18n'
import { downloadRelatedItem, previewRelatedItem } from '../services/downloads'
import { formatDateTime } from '../utils/date'
import CellText from './common/CellText.vue'
import type { ItemLinkResolved, ItemLinksResponse } from '../types'

const props = defineProps({
  itemId: { type: String, default: '' },
})

const toast = useToast()

const loading = ref(false)
const links = ref<ItemLinkResolved[]>([])

const normalizedItemId = computed(() => String(props.itemId || '').trim())

function displayOtherId(link: ItemLinkResolved | null) {
  if (!link) {
    return ''
  }
  if (link.from_item_id === normalizedItemId.value) {
    return link.to_item_id || ''
  }
  return link.from_item_id || ''
}

async function load() {
  if (!normalizedItemId.value) {
    return
  }
  loading.value = true
  try {
    const response = await get<ItemLinksResponse>(apiPaths.search.itemLinks, { params: { item_id: normalizedItemId.value } })
    links.value = response.links || []
  } catch (error: unknown) {
    links.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.loadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 3500 })
  } finally {
    loading.value = false
  }
}

function copyOtherId(link: ItemLinkResolved) {
  const value = displayOtherId(link)
  if (!value) {
    return
  }
  navigator.clipboard?.writeText(value)
  toast.add({ severity: 'success', summary: t('common.copied'), detail: value, life: 1500 })
}

function isDownloadable(itemId: string | undefined) {
  return typeof itemId === 'string' && (itemId.startsWith('document:') || itemId.startsWith('photo:'))
}

function isPreviewable(itemId: string | undefined) {
  return typeof itemId === 'string' && (itemId.startsWith('document:') || itemId.startsWith('photo:'))
}

async function downloadRelated(itemId: string) {
  if (!isDownloadable(itemId)) {
    return
  }
  try {
    await downloadRelatedItem(itemId)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.downloadFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

async function previewRelated(itemId: string) {
  if (!isPreviewable(itemId)) {
    return
  }
  try {
    await previewRelatedItem(itemId)
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: t('common.previewFailed'), detail: apiError?.message || t('common.requestFailed'), life: 4000 })
  }
}

watch(
  () => normalizedItemId.value,
  async (next, prev) => {
    if (next && next !== prev) {
      await load()
    }
    if (!next) {
      links.value = []
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.stack-md {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stack-xs {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.stack-xs strong,
.stack-xs .muted {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.muted {
  color: #51606f;
  font-size: 12px;
}

.sep {
  margin: 0 6px;
}

</style>
