<template>
  <div class="grid">
    <KnowledgeSearchBar
      v-model:question="question"
      :answer="answer"
      :asking="asking"
      :sources="sources"
      @submit="submitQA"
      @clear="clearResult"
    />

    <KnowledgeEntryDetail
      :entry="entry"
      :saving="saving"
      :source-types="sourceTypes"
      :status-options="statusOptions"
      @update:entry="updateEntry"
      @save="saveEntry"
      @reset="resetEntry"
    />

    <KnowledgeEntryList
      :filter-text="recentFilterText"
      :items="filteredRecent"
      :loading-recent="loadingRecent"
      :selected-related-item-id="selectedRelatedItemId"
      @update:filter-text="updateRecentFilterText"
      @refresh="loadRecent"
      @edit="openEditor"
      @select-related="selectForRelated"
      @archive="archiveEntry"
    />
  </div>

  <KnowledgeEntryEditorDialog
    :visible="editorVisible"
    :picker-selected="pickerSelected"
    :editor="editor"
    :editor-saving="editorSaving"
    :picker-options="pickerOptions"
    :source-types="sourceTypes"
    :status-options="statusOptions"
    @update:editor="updateEditor"
    @update:picker-selected="updatePickerSelected"
    @update:visible="updateEditorVisible"
    @add-related="addPickedRelated"
    @save="saveEditor"
  />
</template>

<script setup lang="ts">
import type { KnowledgeEntryCreateRequest } from '../types'
import KnowledgeEntryDetail from './knowledge/KnowledgeEntryDetail.vue'
import KnowledgeEntryEditorDialog from './knowledge/KnowledgeEntryEditorDialog.vue'
import KnowledgeEntryList from './knowledge/KnowledgeEntryList.vue'
import KnowledgeSearchBar from './knowledge/KnowledgeSearchBar.vue'
import { useKnowledgeEntries } from './knowledge/useKnowledgeEntries'

const {
  addPickedRelated,
  answer,
  archiveEntry,
  asking,
  clearResult,
  editor,
  editorSaving,
  editorVisible,
  entry,
  filteredRecent,
  loadRecent,
  loadingRecent,
  openEditor,
  pickerOptions,
  pickerSelected,
  question,
  recentFilterText,
  resetEntry,
  saveEditor,
  saveEntry,
  saving,
  selectForRelated,
  selectedRelatedItemId,
  sourceTypes,
  sources,
  statusOptions,
  submitQA,
} = useKnowledgeEntries()

function updateEntry(value: KnowledgeEntryCreateRequest) {
  entry.value = value
}

function updateEditor(value: KnowledgeEntryCreateRequest & { id: string }) {
  editor.value = value
}

function updatePickerSelected(value: string) {
  pickerSelected.value = value
}

function updateEditorVisible(value: boolean) {
  editorVisible.value = value
}

function updateRecentFilterText(value: string) {
  recentFilterText.value = value
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
