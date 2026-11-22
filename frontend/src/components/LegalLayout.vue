<script setup>
import SiteFooter from './SiteFooter.vue'
defineProps({ title: { type: String, required: true }, updated: { type: String, default: '' } })
</script>

<template>
  <div class="legal-page">
    <header class="legal-nav">
      <a href="/" class="legal-brand">一勺热点 <span>SpoonBrief</span></a>
      <router-link to="/login" class="legal-nav-link">登录</router-link>
    </header>
    <main class="legal-main">
      <article class="legal-card">
        <h1>{{ title }}</h1>
        <p v-if="updated" class="legal-updated">更新日期：{{ updated }}</p>
        <slot />
      </article>
    </main>
    <SiteFooter />
  </div>
</template>

<style scoped>
.legal-page { min-height: 100vh; background: var(--page, #fcfdff); display: flex; flex-direction: column; }
.legal-nav { display: flex; align-items: center; justify-content: space-between; max-width: 820px; width: 100%; margin: 0 auto; padding: 18px 20px; }
.legal-brand { font-weight: 650; color: var(--ink, #18304a); font-size: 16px; letter-spacing: .03em; }
.legal-brand span { color: var(--text-faint); font-weight: 600; margin-left: 4px; }
.legal-nav-link { font-size: 14px; font-weight: 600; }
.legal-main { flex: 1; padding: 0 16px; }
.legal-card { max-width: 820px; margin: 0 auto; background: rgba(255, 255, 255, .94); border: 1px solid rgba(255, 255, 255, .9); border-radius: 16px; padding: 32px 32px 28px; box-shadow: var(--shadow); }
.legal-card :deep(h1) { font-size: 26px; line-height: 1.3; }
.legal-updated { margin-top: 6px; color: var(--text-faint); font-size: 13px; }
.legal-card :deep(h2) { font-size: 18px; margin: 28px 0 10px; padding-left: 10px; border-left: 3px solid var(--primary); }
.legal-card :deep(p), .legal-card :deep(li) { color: var(--ink, #18304a); font-size: 15px; line-height: 1.85; }
.legal-card :deep(ul), .legal-card :deep(ol) { padding-left: 22px; margin: 6px 0; }
.legal-card :deep(li) { margin: 4px 0; }
.legal-card :deep(.legal-note) { margin-top: 14px; background: var(--primary-light); border-radius: 12px; padding: 12px 14px; font-size: 14px; color: var(--muted, #60748a); }
.legal-card :deep(table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 14px; }
.legal-card :deep(th), .legal-card :deep(td) { border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; line-height: 1.7; }
.legal-card :deep(th) { background: var(--ice, #eef5ff); font-weight: 700; white-space: nowrap; }
@media (max-width: 640px) {
  .legal-card { padding: 22px 18px; border-radius: 16px; }
  .legal-card :deep(h1) { font-size: 22px; }
  .legal-card :deep(table), .legal-card :deep(thead), .legal-card :deep(tbody), .legal-card :deep(tr), .legal-card :deep(th), .legal-card :deep(td) { display: block; }
  .legal-card :deep(thead) { display: none; }
  .legal-card :deep(tr) { border: 1px solid var(--border); border-radius: 10px; margin-bottom: 10px; padding: 6px 0; }
  .legal-card :deep(td) { border: none; padding: 4px 12px; }
  .legal-card :deep(td:first-child) { font-weight: 700; }
}
</style>
