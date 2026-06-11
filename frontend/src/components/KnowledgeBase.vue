<template>
  <div class="page-panel">
    <div class="panel-toolbar surface-card">
      <div>
        <h2>{{ t('nav.knowledge') }}</h2>
        <p>{{ t('knowledge.quickAddSubtitle') }}</p>
      </div>
      <Button
        :label="t('knowledge.quickAddTitle')"
        icon="pi pi-plus"
        @click="createVisible = true"
      />
    </div>

    <div class="knowledge-tabs surface-card">
      <button
        type="button"
        class="knowledge-tab"
        :class="{ 'knowledge-tab-active': activePanel === 'ask' }"
        @click="activePanel = 'ask'"
      >
        {{ t('knowledge.askTitle') }}
      </button>
      <button
        type="button"
        class="knowledge-tab"
        :class="{ 'knowledge-tab-active': activePanel === 'recent' }"
        @click="activePanel = 'recent'"
      >
        {{ t('knowledge.recentNotes') }}
      </button>
    </div>

    <div class="grid">
      <KnowledgeSearchBar
        v-model:question="question"
        class="knowledge-panel"
        :class="{ 'knowledge-panel-hidden': activePanel !== 'ask' }"
        :answer="answer"
        :asking="asking"
        :sources="sources"
        @submit="submitQA"
        @clear="clearResult"
      />

      <KnowledgeEntryList
        class="knowledge-panel"
        :class="{ 'knowledge-panel-hidden': activePanel !== 'recent' }"
        :filter-text="recentFilterText"
        :items="filteredRecent"
        :load-message="loadRecentMessage"
        :loading-recent="loadingRecent"
        :selected-related-item-id="selectedRelatedItemId"
        :show-reload-warning="showLoadRecentWarning"
        @update:filter-text="updateRecentFilterText"
        @refresh="loadRecent"
        @edit="openEditor"
        @select-related="selectForRelated"
        @archive="archiveEntry"
      />
    </div>
  </div>

  <KnowledgeEntryCreateDialog
    :visible="createVisible"
    :entry="entry"
    :saving="saving"
    :source-types="sourceTypes"
    :status-options="statusOptions"
    @update:entry="updateEntry"
    @update:visible="updateCreateVisible"
    @save="saveCreateEntry"
    @reset="resetEntry"
  />

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
import Button from 'primevue/button'
import { ref } from 'vue'
import { t } from '../i18n'
import KnowledgeEntryCreateDialog from './knowledge/KnowledgeEntryCreateDialog.vue'
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
  loadRecentMessage,
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
  showLoadRecentWarning,
} = useKnowledgeEntries()

const createVisible = ref(false)
const activePanel = ref<'ask' | 'recent'>('ask')

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

function updateCreateVisible(value: boolean) {
  createVisible.value = value
}

async function saveCreateEntry() {
  if (await saveEntry()) {
    createVisible.value = false
  }
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
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
}

.knowledge-tabs {
  display: none;
  padding: 6px;
  gap: 6px;
}

.knowledge-tab {
  flex: 1 1 0;
  border: 0;
  border-radius: 8px;
  padding: 9px 12px;
  background: transparent;
  color: #33536d;
  font-weight: 700;
  cursor: pointer;
}

.knowledge-tab-active {
  background: #fff;
  color: #1b4d8e;
  box-shadow: 0 6px 12px rgba(31, 76, 132, 0.12);
}

.panel-toolbar h2,
.panel-toolbar p {
  margin: 0;
}

.panel-toolbar h2 {
  font-size: 1rem;
}

.panel-toolbar p {
  margin-top: 4px;
  color: #51606f;
  font-size: 0.9rem;
}

@media (max-width: 1080px) {
  .knowledge-tabs {
    display: flex;
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .knowledge-panel-hidden {
    display: none;
  }
}
</style>
