<script setup>
import SmartSelect from '../components/SmartSelect.vue'
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import { confirmDialog } from '../confirm'
import Modal from '../components/Modal.vue'
import WheelColumn from '../components/WheelColumn.vue'

const subs = ref([])
const loading = ref(true)
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const triggering = ref(null)

const categories = ['综合', '科技', '财经', '国际', '时政', '社会', '娱乐', '体育', '自定义']
const windows = [
  { v: 'today', label: '今日' }, { v: '3d', label: '近 3 天' }, { v: '7d', label: '近 7 天' },
  { v: '10d', label: '近 10 天' }, { v: '15d', label: '近 15 天' }, { v: '20d', label: '近 20 天' },
  { v: '25d', label: '近 25 天' }, { v: '30d', label: '近 30 天' },
]
const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

// ── 发送时间（北京时间，24 小时制，时/分下拉选择；秒固定为 0）──
const freq = ref('daily')        // daily | weekly | monthly
const dow = ref(1)               // 每周几（0=周日）
const dom = ref(1)               // 每月几号
const th = ref(9)                // 时 0-23
const tm = ref(0)                // 分 0-59
const hours = Array.from({ length: 24 }, (_, i) => i)
const minutes = Array.from({ length: 60 }, (_, i) => i)
const monthDays = Array.from({ length: 28 }, (_, i) => i + 1)

const timeText = computed(() =>
  `${String(th.value).padStart(2, '0')}:${String(tm.value).padStart(2, '0')}`
)
const freqText = computed(() => {
  if (freq.value === 'daily') return '每天'
  if (freq.value === 'weekly') return `每周${weekdays[dow.value]}`
  return `每月 ${dom.value} 日`
})
const scheduleText = computed(() => `${freqText.value} ${timeText.value}（北京时间）`)

function buildCron() {
  // croniter 6 段格式：分 时 日 月 周 秒（秒在最后，固定 0）
  const m = tm.value, h = th.value
  if (freq.value === 'daily') return `${m} ${h} * * * 0`
  if (freq.value === 'weekly') return `${m} ${h} * * ${dow.value} 0`
  return `${m} ${h} ${dom.value} * * 0`
}

function parseCron(expr) {
  // 兼容 5 段(分 时 日 月 周)与 6 段(分 时 日 月 周 秒)；解析失败回退默认
  try {
    const parts = String(expr || '').trim().split(/\s+/)
    let m = 0, h = 9, d = '*', w = '*'
    if (parts.length === 5) { [m, h, d, , w] = parts }
    else if (parts.length === 6) { [m, h, d, , w] = parts }
    else return
    const toNum = (x) => (!x || x === '*') ? null : Number(x)
    if (/^\d+$/.test(String(w)) && Number(w) >= 0 && Number(w) <= 6) {
      freq.value = 'weekly'; dow.value = Number(w); th.value = toNum(h) ?? 9
      tm.value = toNum(m) ?? 0
    } else if (/^\d+$/.test(String(d)) && Number(d) >= 1 && Number(d) <= 31) {
      freq.value = 'monthly'; dom.value = Number(d); th.value = toNum(h) ?? 9
      tm.value = toNum(m) ?? 0
    } else {
      freq.value = 'daily'; th.value = toNum(h) ?? 9; tm.value = toNum(m) ?? 0
    }
  } catch { /* 保持默认 */ }
}

function cronToText(expr) {
  try {
    const parts = String(expr || '').trim().split(/\s+/)
    let m = 0, h = 9, d = '*', w = '*'
    if (parts.length === 5) { [m, h, d, w] = parts }   // 5段: 分 时 日 月 周
    else if (parts.length === 6) { [m, h, d, , w] = parts }  // 6段: 分 时 日 月 周 秒
    else return expr
    const pad = (x) => String(x ?? 0).padStart(2, '0')
    const time = `${pad(h === '*' ? 9 : h)}:${pad(m === '*' ? 0 : m)}`
    if (/^\d+$/.test(String(w)) && w >= 0 && w <= 6) return `每周${weekdays[Number(w)]} ${time}`
    if (/^\d+$/.test(String(d)) && d >= 1) return `每月 ${d} 日 ${time}`
    return `每天 ${time}`
  } catch { return expr }
}

function blankForm() {
  return { name: '', category_id: '综合', keywords: '', time_window: '7d', ai_analysis: true, prompt_template_id: null, api_key_id: null, monthly_quota: null, novelty_policy: 'digest', digest_window_days: 3 }
}
const form = ref(blankForm())

// ── 积分信息（透明化展示）──
const quota = ref(null)
async function loadQuota() {
  try {
    quota.value = await api('/profile/quota')
  } catch { /* 忽略 */ }
}
const monthCost = computed(() => (freq.value === 'daily' ? 30 : freq.value === 'weekly' ? 4 : 1))

// ── 分析模板与 API Key 选项 ──
const promptOptions = ref([])
const keyOptions = ref([])

async function loadOptions() {
  try {
    const p = await api('/prompts/')
    // 按 id 去重合并（官方开源模板会同时出现在 platform 与 open_source 两个列表）
    const seen = new Set()
    const opts = []
    const push = (list, labelFn) => {
      for (const x of list || []) {
        if (seen.has(x.id)) continue
        seen.add(x.id)
        opts.push({ id: x.id, label: labelFn(x) })
      }
    }
    push(p.platform, (x) => `${x.name}（官方）`)
    push(p.open_source, (x) => x.name)
    push(p.my, (x) => `${x.name}（我的）`)
    promptOptions.value = opts
    const k = await api('/api-keys/')
    keyOptions.value = (k || []).map((x) => ({ id: x.id, label: x.label || x.provider || `Key #${x.id}` }))
  } catch {
    /* 选项加载失败不阻塞表单 */
  }
}

async function load() {
  loading.value = true
  try {
    subs.value = await api('/subscriptions/')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
  loadOptions()
  loadQuota()
}

// ── 草稿保留：误关弹窗后，编辑内容不丢失 ──
const draftKey = ref(null)
const draft = ref(null)

function captureDraft() {
  draftKey.value = editing.value ? 'edit:' + editing.value.id : 'create'
  draft.value = JSON.parse(JSON.stringify({
    form: form.value, freq: freq.value, dow: dow.value, dom: dom.value,
    th: th.value, tm: tm.value,
  }))
}

function clearDraft() {
  draftKey.value = null
  draft.value = null
}

function onCloseModal() {
  captureDraft()
  showModal.value = false
}

function openCreate() {
  editing.value = null
  if (draftKey.value === 'create' && draft.value) {
    form.value = draft.value.form
    freq.value = draft.value.freq; dow.value = draft.value.dow; dom.value = draft.value.dom
    th.value = draft.value.th; tm.value = draft.value.tm
  } else {
    form.value = blankForm()
    freq.value = 'daily'; dow.value = 1; dom.value = 1
    th.value = 9; tm.value = 0
  }
  showModal.value = true
}

function openEdit(sub) {
  editing.value = sub
  if (draftKey.value === 'edit:' + sub.id && draft.value) {
    form.value = draft.value.form
    freq.value = draft.value.freq; dow.value = draft.value.dow; dom.value = draft.value.dom
    th.value = draft.value.th; tm.value = draft.value.tm
  } else {
    form.value = {
      name: sub.name,
      category_id: sub.category_id || '综合',
      keywords: sub.keywords || '',
      time_window: sub.time_window,
      ai_analysis: sub.ai_analysis,
      prompt_template_id: sub.prompt_template_id || null,
      api_key_id: sub.api_key_id || null,
      monthly_quota: sub.monthly_quota ?? null,
      novelty_policy: sub.novelty_policy || 'digest',
      digest_window_days: sub.digest_window_days || 3,
    }
    parseCron(sub.cron_expr)
  }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return t.err('请填写订阅名称')
  saving.value = true
  try {
    const payload = { ...form.value, cron_expr: buildCron(), timezone: 'Asia/Shanghai' }
    if (editing.value) {
      await api(`/subscriptions/${editing.value.id}`, { method: 'PUT', body: payload })
      t.ok('订阅已更新')
    } else {
      await api('/subscriptions/', { method: 'POST', body: payload })
      t.ok('订阅创建成功，系统将按计划自动推送')
    }
    clearDraft()
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(sub) {
  if (!(await confirmDialog({ text: `确定删除订阅「${sub.name}」吗？` }))) return
  try {
    await api(`/subscriptions/${sub.id}`, { method: 'DELETE' })
    t.ok('订阅已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

async function toggleActive(sub) {
  const next = !sub.is_active   // 取反：勾选框 change 时 sub.is_active 仍是旧值
  try {
    await api(`/subscriptions/${sub.id}`, { method: 'PUT', body: { is_active: next } })
    sub.is_active = next
    t.ok(next ? '订阅已启用' : '订阅已停用')
  } catch (e) {
    t.err(e.message)
  }
}

async function trigger(sub) {
  triggering.value = sub.id
  try {
    const res = await api(`/subscriptions/${sub.id}/trigger`, { method: 'POST', timeout: 240000 })
    if (res.status === 'failed') t.err(res.error || res.message || '推送失败')
    else if (res.status === 'skipped') t.info(res.message)
    else t.ok(res.message || '简报已推送，请查收邮箱')
  } catch (e) {
    t.err(e.message)
  } finally {
    triggering.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">最多 3 个订阅 · 创建订阅后，系统将按计划自动推送简报</p>
      <button class="btn btn-primary" :disabled="subs.length >= 3" @click="openCreate">＋ 创建订阅</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="subs.length === 0" class="card empty">
      <div class="big">📬</div>
      <p>还没有订阅</p>
      <p class="muted" style="margin: 8px 0 16px">创建你的第一个订阅，开始接收 AI 驱动的情报简报</p>
      <button class="btn btn-primary" @click="openCreate">创建第一个订阅</button>
    </div>

    <div v-else class="grid-2">
      <div v-for="sub in subs" :key="sub.id" class="card" style="position: relative">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px">
          <div>
            <h3 style="margin-bottom: 4px">{{ sub.name }}</h3>
            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px">
              <span class="badge">{{ sub.category_id || '未分类' }}</span>
              <span class="badge badge-teal">{{ sub.time_window }}</span>
              <span v-if="sub.is_active" class="badge badge-green">运行中</span>
              <span v-else class="badge badge-gray">已暂停</span>
              <span v-if="sub.ai_analysis" class="badge badge-blue">AI 分析</span>
            </div>
          </div>
          <label class="chip" style="cursor: pointer">
            <input type="checkbox" :checked="sub.is_active" style="accent-color: var(--primary)" @change="toggleActive(sub)" />
            {{ sub.is_active ? '已启用' : '已停用' }}
          </label>
        </div>

        <p v-if="sub.keywords" class="muted" style="margin-bottom: 8px">
          关键词：<span v-for="k in sub.keywords.split(',')" :key="k" class="chip" style="margin-right: 4px">{{ k }}</span>
        </p>
        <p class="faint">发送计划：{{ cronToText(sub.cron_expr) }}（北京时间）</p>
        <p class="faint" v-if="sub.next_sent_at">下次发送：{{ new Date(sub.next_sent_at).toLocaleString('zh-CN') }}</p>
        <p class="faint" v-if="sub.last_sent_at">上次发送：{{ new Date(sub.last_sent_at).toLocaleString('zh-CN') }}</p>

        <div style="display: flex; gap: 8px; margin-top: 14px">
          <button class="btn btn-outline btn-sm" @click="openEdit(sub)">编辑</button>
          <button class="btn btn-push btn-sm" :disabled="triggering === sub.id" :aria-busy="triggering === sub.id" @click="trigger(sub)">
            <span v-if="triggering === sub.id" class="spinner"></span> {{ triggering === sub.id ? '推送中…' : '立即推送' }}
          </button>
          <button class="btn btn-sm" style="color: var(--danger)" @click="remove(sub)">删除</button>
        </div>
      </div>
    </div>

    <Modal :show="showModal" :title="editing ? '编辑订阅' : '创建订阅'" @close="onCloseModal">
      <label class="field">
        <span>订阅名称</span>
        <input v-model="form.name" class="input" placeholder="例如：AI 前沿动态" />
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>信息类别</span>
          <SmartSelect v-model="form.category_id" :options="categories.map(c => ({value:c,label:c}))" label="分类" />
        </label>
        <label class="field">
          <span>时间范围</span>
          <SmartSelect v-model="form.time_window" :options="windows.map(w => ({value:w.v,label:w.label}))" label="时间范围" />
        </label>
      </div>
      <label class="field">
        <span>关键词（中英文逗号/空格分隔均可）</span>
        <input v-model="form.keywords" class="input" placeholder="试试输入：半导体，芯片，国产替代" />
      </label>

      <!-- 发送时间（北京时间） -->
      <div class="schedule-box">
        <div class="schedule-head">
          <span class="field-label">发送时间（北京时间）</span>
          <span class="schedule-preview">{{ scheduleText }}</span>
        </div>

        <div class="segmented">
          <button type="button" :class="['seg-btn', { active: freq === 'daily' }]" @click="freq = 'daily'">每天</button>
          <button type="button" :class="['seg-btn', { active: freq === 'weekly' }]" @click="freq = 'weekly'">每周</button>
          <button type="button" :class="['seg-btn', { active: freq === 'monthly' }]" @click="freq = 'monthly'">每月</button>
        </div>

        <div class="wheel-group">
          <div class="wheel-unit">
            <span class="wheel-label">时</span>
            <WheelColumn v-model="th" :items="hours" />
          </div>
          <div class="wheel-unit">
            <span class="wheel-label">分</span>
            <WheelColumn v-model="tm" :items="minutes" />
          </div>
          <div v-if="freq === 'weekly'" class="wheel-unit">
            <span class="wheel-label">星期</span>
            <WheelColumn v-model="dow" :items="[0, 1, 2, 3, 4, 5, 6]" :format="(v) => weekdays[v]" />
          </div>
          <div v-else-if="freq === 'monthly'" class="wheel-unit">
            <span class="wheel-label">日期</span>
            <WheelColumn v-model="dom" :items="monthDays" :format="(v) => v + ' 日'" />
          </div>
          <div v-else class="wheel-unit">
            <span class="wheel-label"></span>
            <p class="faint" style="font-size: 13px; line-height: 120px; width: 110px; text-align: center; margin: 0">每天定时推送</p>
          </div>
        </div>
        <div class="time-clock">{{ scheduleText }}</div>
      </div>

      <!-- 积分说明（透明化） -->
      <div style="background: var(--primary-light); border: 1px solid #c7d2fe; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px">
        <p class="muted" style="margin: 0 0 4px">
          每份成功投递的邮件消耗：<b>1 积分</b>（同一账户余额；失败不扣）
        </p>
        <p class="muted" style="margin: 0">
          按单收件人、当前频率估算每月消耗：<b>{{ monthCost }} 积分</b>
          · 账户剩余：<b style="color: var(--primary)">{{ quota?.quota_remaining ?? '—' }}</b> 积分
          <span v-if="quota?.quota_reset_at" class="faint">（每月重置）</span>
        </p>
      </div>
      <label class="field">
        <span>每月最多推送（可选，预算上限）</span>
        <div class="field">
          <label class="label">没有重要更新时</label>
          <SmartSelect v-model="form.novelty_policy" :options="[
            {value:'digest', label:'改为周期汇总（默认）'},
            {value:'skip', label:'跳过本次，不发邮件'},
            {value:'always', label:'照常推送（可能重复）'}
          ]" />
          <p class="hint">同一事件只有出现新来源或新事实才会再次推送；纯转载不重复。</p>
        </div>
        <div class="field" v-if="form.novelty_policy === 'digest'">
          <label class="label">汇总间隔（天）</label>
          <input v-model.number="form.digest_window_days" type="number" min="1" max="7" class="input" placeholder="默认 3 天" />
        </div>

        <input v-model.number="form.monthly_quota" type="number" min="1" class="input" placeholder="留空不限。例如填 30：本月推送满 30 份后自动暂停并邮件通知你" />
      </label>

      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>分析模板（AI 角色）</span>
          <SmartSelect v-model="form.prompt_template_id" :options="[{value:null,label:'平台默认（自动选择）'}, ...promptOptions.map(p => ({value:p.id,label:p.label}))]" label="分析模板" />
        </label>
        <label class="field">
          <span>使用 API Key</span>
          <SmartSelect v-model="form.api_key_id" :options="[{value:null,label:'平台默认（自动选择）'}, ...keyOptions.map(k => ({value:k.id,label:k.label}))]" label="接口配置" />
        </label>
      </div>
      <label class="field" style="display: flex; align-items: center; gap: 8px; margin-top: 14px">
        <input v-model="form.ai_analysis" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">启用 AI 全局分析（关闭则仅推送原始热点）</span>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="onCloseModal">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> {{ editing ? '保存修改' : '创建订阅' }}
        </button>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
/* ── 闹钟式滚轮时间选择器 ── */
.wheel-group {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 14px;
  margin: 4px 0 2px;
}
.wheel-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.wheel-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}
@media (max-width: 480px) {
  .wheel-group { gap: 6px; }
}
</style>
