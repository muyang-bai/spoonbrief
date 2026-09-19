<script setup>
import { toasts } from './toast'
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
  <div class="toasts">
    <div v-for="tst in toasts" :key="tst.id" class="toast" :class="`toast-${tst.type}`">
      {{ tst.message }}
    </div>
  </div>
</template>
