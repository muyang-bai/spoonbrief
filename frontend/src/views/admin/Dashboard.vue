<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'

const data = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    data.value = await api('/admin/dashboard')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function maxKeyword() {
  if (!data.value?.keyword_top20?.length) return 1
  return Math.max(...data.value.keyword_top20.map((k) => k.count || 0), 1)
}

function kwPct(count) {
  return Math.round(((count || 0) / maxKeyword()) * 100)
}

function maxTopic() {
  if (!data.value?.subscription_topics?.length) return 1
  return Math.max(...data.value.subscription_topics.map((k) => k.count || 0), 1)
}

function topicPct(count) {
  return Math.round(((count || 0) / maxTopic()) * 100)
}

function maxGrowth() {
  if (!data.value?.user_growth?.length) return 1
  return Math.max(...data.value.user_growth.map((g) => g.count || 0), 1)
}

function barH(count) {
  if (!count) return 0
  return Math.max((count / maxGrowth()) * 100, 4)
}

function money(v) {
  return '¥' + Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">数据面板 · 与 AiLifeOS 统一后台使用同一套口径</p>
      <button class="btn btn-outline btn-sm" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner spinner-dark"></span> 刷新
      </button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <template v-else-if="data">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-bottom: 18px">
        <div class="card stat-card">
          <div class="num">{{ data.total_users ?? 0 }}</div>
          <div class="label">用户总数</div>
          <div class="muted" style="margin-top: 8px; font-size: 12px">活跃 {{ data.active_users ?? 0 }} · 已关联 AiLifeOS {{ data.linked_users ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_subscriptions ?? 0 }}</div>
          <div class="label">订阅总数</div>
          <div class="muted" style="margin-top: 8px; font-size: 12px">活跃 {{ data.active_subscriptions ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_reports ?? 0 }}</div>
          <div class="label">简报总数</div>
          <div class="muted" style="margin-top: 8px; font-size: 12px">今日 {{ data.today_reports ?? 0 }} · 近 24 小时失败 {{ data.failed_24h ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_emails_sent ?? 0 }}</div>
          <div class="label">已发送邮件</div>
          <div class="muted" style="margin-top: 8px; font-size: 12px">送达率 {{ data.email_delivery_rate ?? 0 }}%</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ (data.tokens_24h ?? 0).toLocaleString('zh-CN') }}</div>
          <div class="label">近 24 小时 Token</div>
          <div class="muted" style="margin-top: 8px; font-size: 12px">成本 {{ money(data.cost_yuan_24h) }} · 模型 {{ data.token_model_24h || '—' }}</div>
        </div>
      </div>

      <div class="grid-2" style="margin-bottom: 18px">
        <div class="card">
          <h3>订阅主题热度</h3>
          <p class="muted" style="margin: 0 0 12px; font-size: 12px">按当前订阅名称计数，不是历史检索词。</p>
          <div v-if="!data.subscription_topics?.length" class="empty" style="padding: 28px">暂无订阅主题</div>
          <div v-else>
            <div v-for="(tp, i) in data.subscription_topics" :key="tp.name"
              style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px">
              <span class="muted" style="width: 22px; text-align: right; flex-shrink: 0">{{ i + 1 }}</span>
              <span :title="tp.name"
                style="width: 110px; flex-shrink: 0; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ tp.name }}</span>
              <div style="flex: 1; height: 8px; background: #f3f4f6; border-radius: 999px; overflow: hidden">
                <div :style="{ width: topicPct(tp.count) + '%', height: '100%', background: 'var(--gradient)' }"></div>
              </div>
              <span class="faint" style="width: 40px; text-align: right; flex-shrink: 0">{{ tp.count }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <h3>热门关键词（检索次数）</h3>
          <p class="muted" style="margin: 0 0 12px; font-size: 12px">来自历史检索统计，不等于当前订阅人数。</p>
          <div v-if="!data.keyword_top20?.length" class="empty" style="padding: 28px">暂无检索数据</div>
          <div v-else>
            <div v-for="(kw, i) in data.keyword_top20" :key="kw.keyword"
              style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px">
              <span class="muted" style="width: 22px; text-align: right; flex-shrink: 0">{{ i + 1 }}</span>
              <span :title="kw.keyword"
                style="width: 110px; flex-shrink: 0; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ kw.keyword }}</span>
              <div style="flex: 1; height: 8px; background: #f3f4f6; border-radius: 999px; overflow: hidden">
                <div :style="{ width: kwPct(kw.count) + '%', height: '100%', background: 'var(--gradient)' }"></div>
              </div>
              <span class="faint" style="width: 40px; text-align: right; flex-shrink: 0">{{ kw.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>用户增长（近30天）</h3>
        <div v-if="!data.user_growth?.length" class="empty" style="padding: 28px">暂无数据</div>
        <div v-else style="display: flex; align-items: flex-end; gap: 3px; height: 190px; padding-top: 8px">
          <div v-for="g in data.user_growth" :key="g.date" :title="`${g.date}：${g.count}`"
            style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 5px; height: 100%; min-width: 0">
            <div :style="{ width: '100%', maxWidth: '20px', height: barH(g.count) + '%', background: 'var(--gradient)', borderRadius: '4px 4px 0 0' }"></div>
            <span class="faint" style="font-size: 10px; white-space: nowrap">{{ g.date.slice(5) }}</span>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card empty">
      <div class="big">📊</div>
      <p>暂无数据</p>
    </div>
  </div>
</template>
