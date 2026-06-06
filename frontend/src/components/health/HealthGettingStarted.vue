<template>
  <div class="guide-card">
    <div class="guide-header">
      <h3>{{ t('dashboard.gettingStarted.title') }}</h3>
      <p>{{ t('dashboard.gettingStarted.description') }}</p>
    </div>

    <ol class="guide-list">
      <li
        v-for="step in steps"
        :key="step.key"
        class="guide-step"
      >
        <div class="guide-step-copy">
          <strong>{{ step.title }}</strong>
          <p>{{ step.description }}</p>
        </div>
        <Button
          :label="step.action"
          text
          @click="navigate(step.target)"
        />
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'

import { useI18n } from '../../i18n'
import { useWorkspaceNavigation, type WorkspaceSectionKey } from '../../workspace-navigation'

const { t } = useI18n()
const { navigate } = useWorkspaceNavigation()

const steps = computed(() => [
  {
    action: t('dashboard.gettingStarted.steps.logbook.action'),
    description: t('dashboard.gettingStarted.steps.logbook.description'),
    key: 'logbook',
    target: 'logbook' as WorkspaceSectionKey,
    title: t('dashboard.gettingStarted.steps.logbook.title'),
  },
  {
    action: t('dashboard.gettingStarted.steps.documents.action'),
    description: t('dashboard.gettingStarted.steps.documents.description'),
    key: 'documents',
    target: 'docsPhotos' as WorkspaceSectionKey,
    title: t('dashboard.gettingStarted.steps.documents.title'),
  },
  {
    action: t('dashboard.gettingStarted.steps.prompts.action'),
    description: t('dashboard.gettingStarted.steps.prompts.description'),
    key: 'prompts',
    target: 'prompts' as WorkspaceSectionKey,
    title: t('dashboard.gettingStarted.steps.prompts.title'),
  },
  {
    action: t('dashboard.gettingStarted.steps.autotest.action'),
    description: t('dashboard.gettingStarted.steps.autotest.description'),
    key: 'autotest',
    target: 'autotest' as WorkspaceSectionKey,
    title: t('dashboard.gettingStarted.steps.autotest.title'),
  },
  {
    action: t('dashboard.gettingStarted.steps.generator.action'),
    description: t('dashboard.gettingStarted.steps.generator.description'),
    key: 'generator',
    target: 'generator' as WorkspaceSectionKey,
    title: t('dashboard.gettingStarted.steps.generator.title'),
  },
])
</script>

<style scoped>
.guide-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(19, 87, 163, 0.9), rgba(31, 167, 156, 0.88));
  color: #fff;
  min-height: 100%;
}

.guide-header h3,
.guide-header p {
  margin: 0;
}

.guide-header p {
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.55;
}

.guide-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
}

.guide-step {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
}

.guide-step-copy strong {
  display: block;
  margin-bottom: 6px;
}

.guide-step-copy p {
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.5;
}
</style>
