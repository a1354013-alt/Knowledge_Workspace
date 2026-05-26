<template>
  <Dialog
    :visible="confirmState.visible"
    modal
    :header="confirmState.options.header"
    :style="{ width: 'min(420px, 92vw)' }"
    @update:visible="onVisibilityChange"
  >
    <div class="stack-sm">
      <p class="confirm-message">
        {{ confirmState.options.message }}
      </p>
      <div class="actions-row">
        <Button
          :label="confirmState.options.rejectLabel || 'Cancel'"
          severity="secondary"
          outlined
          @click="rejectConfirm"
        />
        <Button
          :label="confirmState.options.acceptLabel || 'Confirm'"
          severity="danger"
          @click="acceptConfirm"
        />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

import { acceptConfirm, rejectConfirm, useConfirmState } from '../services/confirm'

const confirmState = useConfirmState()

function onVisibilityChange(visible: boolean) {
  if (!visible) {
    rejectConfirm()
  }
}
</script>

<style scoped>
.stack-sm {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.confirm-message {
  margin: 0;
  color: #1f2f46;
  line-height: 1.5;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
