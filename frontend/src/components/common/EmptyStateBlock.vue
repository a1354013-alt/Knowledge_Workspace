<template>
  <div class="empty-state">
    <div
      v-if="icon"
      class="empty-icon"
      :class="icon"
      aria-hidden="true"
    />
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <div
      v-if="$slots.actions"
      class="empty-actions"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  description: string
  icon?: string
  title: string
}>()
</script>

<style scoped>
.empty-state {
  padding: 20px;
  border-radius: 18px;
  border: 1px dashed rgba(93, 118, 153, 0.28);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(241, 249, 255, 0.9));
  text-align: left;
}

.empty-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 14px;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
  background: rgba(84, 128, 255, 0.12);
  color: #2f5ea8;
  font-size: 1.15rem;
}

.empty-icon::before {
  font-family: 'primeicons';
}

.empty-state h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  color: #17324d;
}

.empty-state p {
  margin: 0;
  color: #526579;
  line-height: 1.6;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}
</style>

