<script setup>
import { confirmState, settleConfirm } from '../confirm'
</script>

<template>
  <div v-if="confirmState.show" class="modal-mask" @click.self="settleConfirm(false)">
    <div class="modal" style="max-width: 440px">
      <h3>{{ confirmState.title }}</h3>
      <p style="margin: 0 0 18px; line-height: 1.8; color: var(--text-muted)">{{ confirmState.text }}</p>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="settleConfirm(false)">取消</button>
        <button class="btn" :style="confirmState.danger ? 'background: var(--danger); color: #fff' : ''" @click="settleConfirm(true)">
          {{ confirmState.okText }}
        </button>
      </div>
    </div>
  </div>
</template>
