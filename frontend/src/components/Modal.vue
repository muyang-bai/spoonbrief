<script setup>
defineProps({
  title: { type: String, default: '' },
  show: { type: Boolean, default: false },
  width: { type: String, default: '520px' },
})
defineEmits(['close'])
</script>

<template>
  <div v-if="show" class="modal-mask" @click.self="$emit('close')">
    <div class="modal" :style="{ maxWidth: width }">
      <h3 v-if="title">{{ title }}</h3>
      <slot />
    </div>
  </div>
</template>
