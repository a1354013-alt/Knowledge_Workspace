<template>
  <span :class="badgeClass">{{ normalizedStatus }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
}>()

const normalizedStatus = computed(() => String(props.status || 'pending').toLowerCase())

const badgeClass = computed(() => {
  const value = normalizedStatus.value
  if (value === 'passed' || value === 'done' || value === 'success') return 'badge badge-ok'
  if (value === 'failed') return 'badge badge-bad'
  if (value === 'skipped') return 'badge badge-skip'
  if (value === 'unavailable') return 'badge badge-unavail'
  if (value === 'running') return 'badge badge-run'
  return 'badge badge-neutral'
})
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.2px;
  border: 1px solid transparent;
  text-transform: lowercase;
}

.badge-neutral {
  background: #f0f4f8;
  color: #3a4755;
  border-color: #d8e1e8;
}

.badge-run {
  background: #eef6ff;
  color: #1e4e8c;
  border-color: #cfe6ff;
}

.badge-ok {
  background: #e8fbf1;
  color: #0f6b3a;
  border-color: #bfead0;
}

.badge-bad {
  background: #fff0f0;
  color: #a11919;
  border-color: #ffd0d0;
}

.badge-skip {
  background: #fff7e6;
  color: #8a5a00;
  border-color: #ffe0a3;
}

.badge-unavail {
  background: #f6f0ff;
  color: #5a2ea6;
  border-color: #e2d3ff;
}
</style>
