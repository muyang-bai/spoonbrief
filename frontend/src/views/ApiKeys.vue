<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'

const usage = ref({ total: 0, used: 0, remaining: 0, percent: 0, reset_at: null })
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    usage.value = await api('/auth/me/usage')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '按自然月重置'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">平台统一提供 AI 能力，你无需配置接口；这里与「我的画像」读取同一账户积分余额。每份成功投递的邮件消耗 1 积分，每次成功的 AI 补全建议消耗 2 积分；失败不扣。</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else class="card" style="max-width: 720px">
      <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px">
        <strong style="font-size: 28px">{{ usage.used }}</strong>
        <span class="muted">/ {{ usage.total }} 积分已用</span>
        <span class="muted" style="margin-left: auto">剩余 {{ usage.remaining }} 积分</span>
      </div>
      <div style="height: 10px; background: #eef1f8; border-radius: 6px; overflow: hidden; margin: 12px 0 18px">
        <div :style="{ width: Math.min(usage.percent, 100) + '%', height: '100%', background: 'var(--gradient)' }"></div>
      </div>
      <p class="muted">处理中暂留 {{ usage.reserved ?? 0 }} 积分（成功结算，失败释放）。本期已用及暂留 {{ usage.percent }}% · 重置时间：{{ fmtTime(usage.reset_at) }}</p>
      <p class="muted" style="margin-top: 12px">积分由平台统一分配；用完后可以联系管理员调整。</p>
    </div>
  </div>
</template>
