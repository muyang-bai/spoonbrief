<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import SmartSelect from '../../components/SmartSelect.vue'

const days = ref(30)
const data = ref({ daily: [], by_model: [], all_time: {}, feedback: {}, top_users: [], by_stage: [] })
const loading = ref(true)
const metric = ref('cost') // cost | calls | tokens
const hover = ref(null)
const quality = ref({ totals: {}, daily: [] })

const rangeOptions = [
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
  { value: 90, label: '近 90 天' },
  { value: 180, label: '近 180 天' },
]

const METRICS = [
  { key: 'cost', label: '消费金额' },
  { key: 'calls', label: '请求次数' },
  { key: 'tokens', label: 'Tokens' },
]

const rangeLabel = computed(() => (days.value === 7 ? '近 7 天' : days.value === 90 ? '近 90 天' : days.value === 180 ? '近 180 天' : '近 30 天'))
const all = computed(() => data.value.all_time || {})
const today = computed(() => {
  const list = data.value.daily || []
  return list.length ? list[list.length - 1] : { cost: 0, calls: 0, tokens: 0, date: '' }
})

const series = computed(() => data.value.daily || [])
const maxValue = computed(() => {
  const vals = series.value.map((d) => Number(d[metric.value]) || 0)
  const m = Math.max(...vals, 0)
  return m > 0 ? m : 1
})
const axisLabel = (v) => (metric.value === 'cost' ? '¥' + (v >= 1 ? v.toFixed(2) : v.toFixed(3)) : fmtNum(Math.round(v)))
const barHeight = (d) => Math.max(3, Math.round(((Number(d[metric.value]) || 0) / maxValue.value) * 100))
const metricLabel = computed(() => METRICS.find((m) => m.key === metric.value)?.label || '')

const totalTokens = computed(() => Number(data.value.total_tokens) || 0)
const totalCost = computed(() => Number(data.value.total_cost) || 0)
const totalCalls = computed(() => Number(data.value.calls) || 0)
const avgPerReport = computed(() => {
  const n = Number(data.value.sent_reports) || 0
  return n ? totalCost.value / n : null
})
const modelMax = computed(() => Math.max(1, ...(data.value.by_model || []).map((m) => m.tokens || 0)))

function fmtNum(n) {
  return Number(n || 0).toLocaleString('zh-CN')
}
function fmtMoney(n) {
  const v = Number(n || 0)
  return v >= 100 ? v.toFixed(2) : v.toFixed(4)
}

async function load() {
  loading.value = true
  try {
    const [stats, nov] = await Promise.all([
      api('/admin/token-stats', { params: { days: days.value } }),
      api('/admin/metrics/novelty', { params: { days: days.value } }),
    ])
    data.value = stats
    quality.value = nov
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function showTip(d, event) {
  const rect = event.currentTarget.getBoundingClientRect()
  hover.value = { ...d, x: rect.left + rect.width / 2, y: rect.top }
}
function hideTip() {
  hover.value = null
}

function exportCsv() {
  const rows = [['日期', '消费金额(元)', '请求次数', 'Tokens']]
  for (const d of series.value) rows.push([d.date, d.cost, d.calls, d.tokens])
  const csv = rows.map((r) => r.join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `用量统计_近${days.value}天.csv`
  a.click()
  URL.revokeObjectURL(a.href)
  t.ok('已导出 CSV')
}

watch(days, load)
onMounted(load)
</script>

<template>
  <div class="usage">
    <div class="usage-head">
      <h1>用量信息</h1>
      <p class="muted">所有日期按北京时间（GMT+8）显示；数据来自每次模型调用的实际记账。</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <template v-else>
      <div class="sum-grid">
        <div class="sum-card">
          <p class="sum-label">累计消费金额</p>
          <p class="sum-value">¥{{ fmtMoney(all.cost) }}<span class="sum-unit">CNY</span></p>
          <p class="sum-sub">累计 {{ fmtNum(all.tokens) }} tokens · {{ fmtNum(all.calls) }} 次调用</p>
        </div>
        <div class="sum-card">
          <p class="sum-label">今日消费金额</p>
          <p class="sum-value">¥{{ fmtMoney(today.cost) }}<span class="sum-unit">CNY</span></p>
          <p class="sum-sub">{{ rangeLabel }}合计 ¥{{ fmtMoney(totalCost) }} · 平均每份 ¥{{ avgPerReport === null ? '—' : fmtMoney(avgPerReport) }}</p>
        </div>
      </div>

      <div class="filter-bar">
        <label class="filter-item">
          <span>时间维度</span>
          <div class="range-select">
            <SmartSelect v-model="days" :options="rangeOptions" label="近 30 天" />
          </div>
        </label>
        <button class="btn btn-outline export" @click="exportCsv">导出 CSV</button>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <p class="kpi-label">消费金额</p>
          <p class="kpi-value">¥{{ fmtMoney(totalCost) }}<span class="kpi-unit">CNY</span></p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">API 请求次数</p>
          <p class="kpi-value">{{ fmtNum(totalCalls) }}<span class="kpi-unit">次</span></p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Tokens</p>
          <p class="kpi-value">{{ fmtNum(totalTokens) }}</p>
        </div>
      </div>

      <div class="card chart-card">
        <div class="chart-head">
          <div>
            <h3>{{ metricLabel }} · 每日趋势</h3>
            <p class="muted">{{ rangeLabel }} · {{ series.length }} 天有数据 · 悬停查看当日明细</p>
          </div>
          <div class="tabs">
            <button
              v-for="m in METRICS" :key="m.key" type="button"
              :class="['tab', { active: metric === m.key }]"
              @click="metric = m.key"
            >{{ m.label }}</button>
          </div>
        </div>

        <div class="chart">
          <div class="gridlines"><span v-for="n in 4" :key="n"></span></div>
          <div class="yaxis">
            <span>{{ axisLabel(maxValue) }}</span>
            <span>{{ axisLabel(maxValue / 2) }}</span>
            <span>0</span>
          </div>
          <div class="bars">
            <div
              v-for="d in series" :key="d.date" class="bar-slot"
              @mouseenter="showTip(d, $event)" @mouseleave="hideTip"
            >
              <div class="bar" :style="{ height: barHeight(d) + '%' }"></div>
            </div>
          </div>
          <div class="axis">
            <span>{{ series.length ? series[0].date : '' }}</span>
            <span>{{ series.length ? series[series.length - 1].date : '' }}</span>
          </div>
          <div v-if="hover" class="tip" :style="{ left: hover.x + 'px', top: (hover.y - 8) + 'px' }">
            <p class="tip-date">{{ hover.date }}</p>
            <p><span>消费</span><b>¥{{ fmtMoney(hover.cost) }}</b></p>
            <p><span>请求</span><b>{{ fmtNum(hover.calls) }} 次</b></p>
            <p><span>Tokens</span><b>{{ fmtNum(hover.tokens) }}</b></p>
          </div>
        </div>
      </div>


      <div class="card chart-card">
        <div class="chart-head">
          <div>
            <h3>内容质量 · 去重与进展</h3>
            <p class="muted">去重效率 = 重复事件占比；进展率 = 有实质进展的事件占非全新事件；零新增 = 因无新增触发跳过或汇总</p>
          </div>
        </div>
        <div class="kpi-grid" style="margin: 12px 0 0">
          <div class="kpi-card"><p class="kpi-label">去重效率</p><p class="kpi-value">{{ quality.totals.dedupe_rate ?? 0 }}<span class="kpi-unit">%</span></p></div>
          <div class="kpi-card"><p class="kpi-label">进展率</p><p class="kpi-value">{{ quality.totals.progress_rate ?? 0 }}<span class="kpi-unit">%</span></p></div>
          <div class="kpi-card"><p class="kpi-label">零新增次数</p><p class="kpi-value">{{ quality.totals.zero_update ?? 0 }}<span class="kpi-unit">次</span></p></div>
        </div>
        <div class="bars" style="height: 110px; margin-top: 14px">
          <div v-for="d in quality.daily" :key="'q' + d.date" class="bar-slot" :title="`${d.date}｜去重 ${d.dedupe_rate}%｜进展 ${d.progress_rate}%｜新 ${d.fresh}`">
            <div class="bar" :style="{ height: Math.max(4, d.dedupe_rate) + '%' }"></div>
          </div>
        </div>
        <div class="axis"><span>{{ quality.daily.length ? quality.daily[0].date : '' }}</span><span>{{ quality.daily.length ? quality.daily[quality.daily.length - 1].date : '' }}</span></div>
      </div>

      <div class="two-grid">
        <div class="card">
          <h3>模型分布</h3>
          <p class="muted" style="margin-bottom: 12px">按 token 消耗排序</p>
          <div v-for="m in data.by_model" :key="m.model" class="model-row">
            <div class="model-top">
              <b>{{ m.model }}</b>
              <span class="faint">{{ fmtNum(m.calls) }} 次 · ¥{{ fmtMoney(m.cost) }}</span>
            </div>
            <div class="model-track"><i :style="{ width: Math.max(3, (m.tokens / modelMax) * 100) + '%' }"></i></div>
            <p class="faint">{{ fmtNum(m.tokens) }} tokens</p>
          </div>
          <p v-if="!data.by_model.length" class="muted">本期还没有调用记录。</p>
        </div>

        <div class="card">
          <h3>消耗与反馈</h3>
          <div class="mini-stats">
            <div><p class="faint">今日消费</p><b>¥{{ fmtMoney(today.cost) }}</b></div>
            <div><p class="faint">有用反馈</p><b>{{ fmtNum(data.feedback?.up) }}</b></div>
            <div><p class="faint">没用反馈</p><b>{{ fmtNum(data.feedback?.down) }}</b></div>
            <div><p class="faint">有用率</p><b>{{ data.feedback?.useful_rate === null || data.feedback?.useful_rate === undefined ? '—' : data.feedback.useful_rate + '%' }}</b></div>
          </div>
          <p class="faint" style="margin-top: 14px">消耗最多的用户</p>
          <ul class="top-list">
            <li v-for="u in data.top_users" :key="u.user_id">
              <span>{{ u.email || '（已注销）' }}</span>
              <span class="faint">{{ fmtNum(u.tokens) }} tokens · ¥{{ fmtMoney(u.cost) }}</span>
            </li>
            <li v-if="!data.top_users.length" class="muted">暂无数据</li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.usage { max-width: 1180px; }
.usage-head { margin-bottom: 18px; }
.usage-head h1 { font-size: 24px; margin: 0 0 6px; color: var(--text); }
.sum-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 18px; }
.sum-card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 18px 20px; box-shadow: var(--shadow); }
.sum-label { margin: 0; font-size: 14px; color: var(--text-muted); }
.sum-value { margin: 8px 0 4px; font-size: 30px; font-weight: 750; color: var(--text); font-variant-numeric: tabular-nums; }
.sum-unit { margin-left: 6px; font-size: 13px; font-weight: 500; color: var(--text-faint); }
.sum-sub { margin: 0; font-size: 13px; color: var(--text-faint); }

.filter-bar { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-item { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--text-muted); }
.range-select { width: 132px; }
.export { margin-left: auto; }

.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }
.kpi-card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow); }
.kpi-label { margin: 0 0 10px; font-size: 13px; color: var(--text-muted); }
.kpi-value { margin: 0; font-size: 26px; font-weight: 750; color: var(--text); font-variant-numeric: tabular-nums; }
.kpi-unit { margin-left: 6px; font-size: 12px; color: var(--text-faint); font-weight: 500; }

.chart-card { padding: 18px 20px 14px; margin-bottom: 18px; }
.chart-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.chart-head h3 { margin: 0 0 4px; font-size: 16px; color: var(--text); }
.tabs { display: inline-flex; background: var(--primary-light); border: 1px solid var(--primary-border); border-radius: 999px; padding: 3px; }
.tab { border: 0; background: transparent; color: var(--text-muted); font-size: 13px; padding: 6px 14px; border-radius: 999px; cursor: pointer; }
.tab.active { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(91, 124, 255, .35); }

.chart { position: relative; margin-top: 16px; padding: 10px 0 0; }
.gridlines { position: absolute; inset: 10px 0 26px; display: flex; flex-direction: column; justify-content: space-between; pointer-events: none; }
.gridlines span { border-top: 1px dashed var(--border); }
.yaxis { position: absolute; left: 0; top: 10px; bottom: 26px; display: flex; flex-direction: column; justify-content: space-between; font-size: 11px; color: var(--text-faint); pointer-events: none; }
.bars { position: relative; display: flex; align-items: flex-end; gap: 4px; height: 190px; padding-bottom: 2px; padding-left: 44px; }
.bar-slot { flex: 1; height: 100%; display: flex; align-items: flex-end; cursor: pointer; }
.bar { width: 100%; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg, #7d95ff, #4d6bfe); transition: filter .15s; min-height: 2px; }
.bar-slot:hover .bar { filter: brightness(1.12); }
.axis { padding-left: 44px; display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: var(--text-faint); }

.tip { position: fixed; transform: translate(-50%, -100%); z-index: 60; background: #1f2937; color: #fff; border-radius: 10px; padding: 10px 12px; font-size: 12px; line-height: 1.7; box-shadow: 0 12px 30px rgba(0, 0, 0, .28); pointer-events: none; }
.tip-date { margin: 0 0 4px; font-weight: 700; }
.tip p { margin: 0; display: flex; gap: 12px; justify-content: space-between; }
.tip span { color: #cbd5e1; }

.two-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.two-grid h3 { margin: 0 0 4px; font-size: 16px; color: var(--text); }
.model-row { margin-bottom: 12px; }
.model-top { display: flex; justify-content: space-between; font-size: 14px; color: var(--text); margin-bottom: 6px; }
.model-track { height: 8px; background: var(--primary-light); border-radius: 999px; overflow: hidden; }
.model-track i { display: block; height: 8px; border-radius: 999px; background: var(--gradient); }
.model-row .faint { margin: 4px 0 0; font-size: 12px; }

.mini-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 8px; }
.mini-stats p { margin: 0 0 4px; }
.mini-stats b { font-size: 18px; color: var(--text); }
.top-list { list-style: none; margin: 6px 0 0; padding: 0; }
.top-list li { display: flex; justify-content: space-between; font-size: 13px; padding: 6px 0; border-top: 1px solid var(--border); }

@media (max-width: 860px) {
  .sum-grid, .kpi-grid, .two-grid { grid-template-columns: 1fr; }
  .bars { height: 140px; }
}
</style>
