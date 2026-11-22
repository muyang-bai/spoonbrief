<script setup>
import { ICP_RECORD, ICP_URL } from '../compliance'
defineProps({ compact: { type: Boolean, default: false } })
</script>

<template>
  <footer class="site-footer" :class="{ compact }">
    <nav class="site-footer-links" aria-label="合规信息">
      <router-link to="/privacy">隐私政策</router-link>
      <span aria-hidden="true">·</span>
      <router-link to="/unsubscribe-help">退订说明</router-link>
      <span aria-hidden="true">·</span>
      <a :href="ICP_URL" target="_blank" rel="noopener">{{ ICP_RECORD }}</a>
      <span aria-hidden="true">·</span>
      <a href="https://ailifeos.muyang-bai.chat/" target="_blank" rel="noopener noreferrer">思忆 AiLifeOS</a>
    </nav>
    <p v-if="!compact" class="site-footer-brand">一勺热点 SpoonBrief · 也可了解思忆 AiLifeOS</p>
  </footer>
</template>

<style scoped>
.site-footer { text-align: center; padding: 20px 16px 28px; font-size: 12.5px; color: var(--text-faint); }
.site-footer.compact { padding: 16px 0 0; }
.site-footer-links { display: flex; justify-content: center; flex-wrap: wrap; gap: 6px 8px; }
.site-footer-links a { color: var(--text-muted); }
.site-footer-links a:hover { color: var(--primary); }
.site-footer-brand { margin-top: 6px; }
</style>
