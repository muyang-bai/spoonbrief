<script setup>
/**
 * 红绿灯窗框：给"预览类"内容一个 macOS 风格的窗口外壳
 * 用法：<WindowFrame title="简报预览 · 一勺热点" flush>...</WindowFrame>
 */
defineProps({
  title: { type: String, default: '' },
  tone: { type: String, default: 'warm' }, // warm | plain
  flush: { type: Boolean, default: false },
})
</script>

<template>
  <section class="wf" :class="[`wf-${tone}`, { 'wf-flush': flush }]">
    <header class="wf-bar">
      <span class="wf-dots" aria-hidden="true">
        <i class="wf-dot wf-r"></i>
        <i class="wf-dot wf-y"></i>
        <i class="wf-dot wf-g"></i>
      </span>
      <span v-if="title" class="wf-title">{{ title }}</span>
      <span class="wf-actions"><slot name="bar" /></span>
    </header>
    <div class="wf-body"><slot /></div>
  </section>
</template>

<style scoped>
.wf {
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  box-shadow: var(--shadow);
}
.wf-warm {
  border-color: #D0D8FF;
  box-shadow: 0 12px 32px rgba(91, 124, 255, 0.10);
}
.wf-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: linear-gradient(180deg, #FCFCFD, #F0F3FF);
  border-bottom: 1px solid #E4EAFF;
}
.wf-dots { display: inline-flex; gap: 6px; }
.wf-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06);
}
.wf-r { background: #ff5f57; }
.wf-y { background: #febc2e; }
.wf-g { background: #28c840; }
.wf-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}
.wf-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.wf-body { padding: 16px; }
.wf-flush .wf-body { padding: 0; }

@media (max-width: 560px) {
  .wf-bar { padding: 8px 10px; }
  .wf-body { padding: 12px; }
}
</style>
