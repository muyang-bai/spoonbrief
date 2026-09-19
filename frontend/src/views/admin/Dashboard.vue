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

function maxGrowth() {
  if (!data.value?.user_growth?.length) return 1
  return Math.max(...data.value.user_growth.map((g) => g.count || 0), 1)
}

function barH(count) {
  if (!count) return 0
  return Math.max((count / maxGrowth()) * 100, 4)
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">管理仪表盘 · 平台运营数据总览</p>
      <button class="btn btn-outline btn-sm" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner spinner-dark"></span> 刷新
      </button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <template v-else-if="data">
      <!-- 顶部统计卡 -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-bottom: 18px">
        <div class="card stat-card">
          <div class="num">{{ data.total_users ?? 0 }}</div>
          <div class="label">用户总数 · 活跃 {{ data.active_users ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_subscriptions ?? 0 }}</div>
          <div class="label">订阅总数 · 活跃 {{ data.active_subscriptions ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_reports ?? 0 }}</div>
          <div class="label">报告总数 · 今日 {{ data.today_reports ?? 0 }}</div>
        </div>
        <div class="card stat-card">
          <div class="num">{{ data.total_emails_sent ?? 0 }}</div>
          <div class="label">已发送邮件 · 送达率 {{ data.email_delivery_rate ?? 0 }}%</div>
        </div>
      </div>

      <!-- 中部双栏：热门关键词 / 类别分布 -->
      <div class="grid-2" style="margin-bottom: 18px">
        <div class="card">
          <h3>热门关键词 Top 20</h3>
          <div v-if="!data.keyword_top20?.length" class="empty" style="padding: 28px">暂无数据</div>
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

        <div class="card">
          <h3>类别分布</h3>
          <div v-if="!data.category_distribution?.length" class="empty" style="padding: 28px">暂无数据</div>
          <div v-else>
            <div v-for="c in data.category_distribution" :key="c.name"
              style="display: flex; justify-content: space-between; align-items: center; padding: 10px 2px; border-bottom: 1px solid var(--border)">
              <span style="font-size: 14px">{{ c.name }}</span>
              <span class="badge badge-teal">{{ c.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部：用户增长柱状图（纯 CSS） -->
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
