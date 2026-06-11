<template>
  <span
    class="kw-cell-text"
    :class="{ 'kw-cell-text-muted': muted }"
    :title="titleText"
  >
    {{ displayText }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  muted?: boolean
  text: string | number | null | undefined
  title?: string
}>(), {
  muted: false,
  title: '',
})

const displayText = computed(() => {
  const value = props.text
  if (value === null || value === undefined || String(value).trim() === '') {
    return '-'
  }
  return String(value)
})

const titleText = computed(() => props.title || displayText.value)
</script>
