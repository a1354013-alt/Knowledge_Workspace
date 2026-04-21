<template>
  <Card>
    <template #title>
      Related items
    </template>
    <template
      v-if="itemId"
      #subtitle
    >
      Trace relationships for <code>{{ itemId }}</code>
    </template>
    <template #content>
      <div class="stack-md">
        <div class="row">
          <Button
            label="Refresh"
            outlined
            icon="pi pi-refresh"
            :loading="loading"
            :disabled="!itemId"
            @click="load"
          />
          <span
            v-if="!itemId"
            class="muted"
          >Select an item to view relationships.</span>
        </div>

        <DataTable
          v-if="itemId"
          :value="links"
          :loading="loading"
          data-key="link_id"
          size="small"
          responsive-layout="scroll"
        >
          <Column
            field="created_at"
            header="When"
          />
          <Column
            field="link_type"
            header="Type"
          />
          <Column header="Related item">
            <template #body="slotProps">
              <div class="stack-xs">
                <strong>{{ slotProps.data?.other_item?.title || displayOtherId(slotProps.data) }}</strong>
                <div class="muted">
                  <span>{{ slotProps.data?.other_item?.item_type || 'unknown' }}</span>
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
          <Column header="Actions">
            <template #body="slotProps">
              <div class="actions-inline">
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
import { downloadBlob, openBlobInNewTab } from '../utils/blob'
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
    const response = await get<ItemLinksResponse>('/api/item-links', { params: { item_id: normalizedItemId.value } })
    links.value = response.links || []
  } catch (error: unknown) {
    links.value = []
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Load failed', detail: apiError?.message || 'Request failed.', life: 3500 })
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
  toast.add({ severity: 'success', summary: 'Copied', detail: value, life: 1500 })
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
  const [prefix, rawId] = itemId.split(':', 2)
  try {
    if (prefix === 'document') {
      const blob = await get<Blob>(`/api/docs/${rawId}/download`, { responseType: 'blob' })
      downloadBlob(blob, `document-${rawId}`)
    } else if (prefix === 'photo') {
      const blob = await get<Blob>(`/api/photos/${rawId}/download`, { responseType: 'blob' })
      downloadBlob(blob, `photo-${rawId}`)
    }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Download failed', detail: apiError?.message || 'Request failed.', life: 4000 })
  }
}

async function previewRelated(itemId: string) {
  if (!isPreviewable(itemId)) {
    return
  }
  const [prefix, rawId] = itemId.split(':', 2)
  try {
    if (prefix === 'document') {
      const blob = await get<Blob>(`/api/docs/${rawId}/download`, { params: { inline: 1 }, responseType: 'blob' })
      openBlobInNewTab(blob)
    } else if (prefix === 'photo') {
      const blob = await get<Blob>(`/api/photos/${rawId}/download`, { params: { inline: 1 }, responseType: 'blob' })
      openBlobInNewTab(blob)
    }
  } catch (error: unknown) {
    const apiError = error as { message?: string }
    toast.add({ severity: 'error', summary: 'Preview failed', detail: apiError?.message || 'Request failed.', life: 4000 })
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

.actions-inline {
  display: flex;
  gap: 6px;
}
</style>
