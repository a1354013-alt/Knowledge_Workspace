<template>
  <span :class="badgeClass">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { capitalizeStatus } from './useProjectHealth'

const props = defineProps<{
  status: string
}>()

const label = computed(() => capitalizeStatus(props.status))
const badgeClass = computed(() => `badge badge-${props.status}`)
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-passed {
  background: rgba(40, 167, 69, 0.15);
  color: #28a745;
}

.badge-failed {
  background: rgba(220, 53, 69, 0.15);
  color: #dc3545;
}

.badge-running {
  background: rgba(23, 162, 184, 0.15);
  color: #17a2b8;
}

.badge-queued {
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
}
</style>
