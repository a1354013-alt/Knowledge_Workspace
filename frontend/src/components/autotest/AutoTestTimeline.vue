<template>
  <div class="result-box">
    <div class="timeline-header">
      <div>
        <h3>{{ t('autotest.timelineTitle') }}</h3>
        <p class="muted">
          {{ t('autotest.timelineSubtitle') }}
        </p>
      </div>
    </div>

    <div
      v-if="timelineItems.length"
      class="timeline"
    >
      <article
        v-for="item in timelineItems"
        :key="item.key"
        class="timeline-item"
      >
        <div
          class="timeline-marker"
          :class="`timeline-${item.status}`"
        >
          <span />
        </div>
        <div class="timeline-body">
          <div class="timeline-row">
            <strong>{{ item.label }}</strong>
            <AutoTestStatusBadge :status="item.status" />
          </div>
          <p
            v-if="item.finished_at || item.started_at"
            class="timeline-time"
          >
            {{ formatTimelineTimestamp(item.finished_at || item.started_at || '') }}
          </p>
          <p
            v-if="item.message"
            class="timeline-message"
          >
            {{ item.message }}
          </p>
          <p
            v-if="item.duration_ms !== null"
            class="timeline-time"
          >
            {{ item.duration_ms }} ms
          </p>
        </div>
      </article>
    </div>

    <div
      v-else
      class="timeline-empty"
    >
      {{ t('autotest.timelineEmpty') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { AutoTestRunResponse, AutoTestTimelineItemResponse } from '../../types'
import { t } from '../../i18n'
import AutoTestStatusBadge from './AutoTestStatusBadge.vue'

const props = defineProps<{
  run: AutoTestRunResponse | null
}>()

const allowedTimelineStatuses = new Set(['pending', 'running', 'success', 'failed', 'skipped'])
const fallbackTimelineKeys = [
  ['uploaded', 'autotest.timelineUploaded'],
  ['extracted', 'autotest.timelineExtracted'],
  ['detected_stack', 'autotest.timelineDetectedStack'],
  ['prepared_environment', 'autotest.timelinePreparedEnvironment'],
  ['ran_tests', 'autotest.timelineRanTests'],
  ['generated_report', 'autotest.timelineGeneratedReport'],
  ['failed_reason', 'autotest.failedReason'],
] as const

const timelineItems = computed<AutoTestTimelineItemResponse[]>(() => buildTimeline(props.run))

function formatTimelineTimestamp(value: string) {
  try {
    return new Date(value).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function normalizeTimelineItem(
  raw: Partial<AutoTestTimelineItemResponse> | null | undefined
): AutoTestTimelineItemResponse | null {
  const key = String(raw?.key || '').trim()
  const label = String(raw?.label || '').trim()
  const status = String(raw?.status || '').trim().toLowerCase()
  if (!key || !label || !allowedTimelineStatuses.has(status)) {
    return null
  }
  return {
    key,
    label,
    name: String(raw?.name || label).trim(),
    status: status as AutoTestTimelineItemResponse['status'],
    started_at: raw?.started_at ? String(raw.started_at) : null,
    finished_at: raw?.finished_at ? String(raw.finished_at) : null,
    duration_ms: typeof raw?.duration_ms === 'number' ? raw.duration_ms : null,
    message: raw?.message ? String(raw.message) : null,
  }
}

function buildTimeline(run: AutoTestRunResponse | null): AutoTestTimelineItemResponse[] {
  if (!run) {
    return []
  }

  const normalized = Array.isArray(run.timeline)
    ? run.timeline
        .map((item) => normalizeTimelineItem(item))
        .filter((item): item is AutoTestTimelineItemResponse => item !== null)
    : []
  if (normalized.length) {
    return normalized
  }

  const failedMessage = run.summary || run.suggestion || null
  return fallbackTimelineKeys.map(([key, labelKey]) => {
    const label = t(labelKey)
    return {
    key,
    label,
    name: label,
    status:
      key === 'uploaded'
        ? 'success'
        : key === 'failed_reason' && run.status === 'failed'
          ? 'failed'
          : key === 'generated_report' && (run.summary || run.prompt_output)
            ? 'success'
            : key === 'ran_tests' && run.status === 'running'
              ? 'running'
              : key === 'ran_tests' && (run.status === 'passed' || run.status === 'failed')
                ? run.status === 'failed'
                  ? 'failed'
                  : 'success'
                : 'pending',
    started_at: key === 'uploaded' ? run.created_at || null : null,
    finished_at: key === 'uploaded' ? run.created_at || null : null,
    duration_ms: key === 'uploaded' ? 0 : null,
    message:
      key === 'uploaded'
        ? run.source_ref || null
        : key === 'failed_reason' && run.status === 'failed'
          ? run.failed_reason || failedMessage
          : key === 'generated_report' && run.summary
            ? run.summary
            : null,
    }
  })
}
</script>

<style scoped>
.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f7fafc;
}

.muted {
  margin: 0;
  color: #51606f;
  font-size: 13px;
}

.timeline-header h3 {
  margin: 0 0 4px;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-top: 12px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 14px;
}

.timeline-item:not(:last-child) .timeline-marker::after {
  content: '';
  position: absolute;
  top: 22px;
  bottom: -12px;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  background: #d8e1e8;
}

.timeline-marker {
  position: relative;
  display: flex;
  justify-content: center;
}

.timeline-marker span {
  width: 14px;
  height: 14px;
  margin-top: 4px;
  border-radius: 999px;
  border: 2px solid transparent;
  background: #d8e1e8;
  box-shadow: 0 0 0 6px rgba(255, 255, 255, 0.9);
}

.timeline-success span,
.timeline-done span {
  background: #0f6b3a;
  border-color: #bfead0;
}

.timeline-running span {
  background: #1e4e8c;
  border-color: #cfe6ff;
}

.timeline-failed span {
  background: #a11919;
  border-color: #ffd0d0;
}

.timeline-pending span {
  background: #b0bcc8;
  border-color: #e5edf4;
}

.timeline-skipped span {
  background: #8a5a00;
  border-color: #ffe0a3;
}

.timeline-body {
  padding: 0 0 18px;
}

.timeline-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.timeline-time,
.timeline-message,
.timeline-empty {
  margin: 6px 0 0;
  color: #51606f;
  font-size: 13px;
}

.timeline-message {
  white-space: pre-wrap;
  line-height: 1.5;
}

.timeline-empty {
  margin-top: 12px;
  padding: 14px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px dashed #d8e1e8;
}
</style>
