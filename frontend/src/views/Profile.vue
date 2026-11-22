<script setup>
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import TagEditor from '../components/TagEditor.vue'
import { api, getUser } from '../api'
import { t } from '../toast'

const profile = ref(null)
const quota = ref(null)
const loading = ref(true)
const saving = ref(false)
const meta = ref(null)
const preview = ref(null)
const suggesting = ref(false)
const suggestResult = ref(null)
const loadError = ref('')
const previewError = ref('')
const editing = ref({})
const dirty = ref(false)
const subscriptions = ref([])
const keywordSaving = ref(null)
let hydrated = false
const suggestionStatus = ref({})

const form = ref(blankForm())

function blankForm() {
  return {
    identities: [],
    field: '',
    role_title: '',
    goals: [],
    domains: [],
    content_prefs: [],
    outputs: [],
    avoid: [],
    perspective: '',
    horizon: '',
    risk: '',
    reading_length: '',
    tone: '',
    pain_point: '',
    self_description: '',
    extra_notes: '',
    student: { major: '', target_school: '' },
    entrepreneur: { industry: '', stage: '' },
  }
}

const PRESETS = [
  {
    name: '学生考研',
    data: {
      identities: ['学生'], goals: ['升学考研'],
      domains: ['AI 与大模型', '教育政策', '算力与芯片'],
      content_prefs: ['政策与文件', '技术进展'],
      outputs: ['行动清单', '机会与风险'],
      reading_length: '3 分钟读完', tone: '通俗科普', horizon: '1-3 个月内',
    },
  },
  {
    name: '投资研究',
    data: {
      identities: ['投资者'], goals: ['投资决策'],
      domains: ['宏观与黄金', '半导体产业链', '新能源与储能'],
      content_prefs: ['资本动向', '数据与报告'],
      outputs: ['可引用数据', '机会与风险'],
      risk: '平衡型', horizon: '1-3 个月内', perspective: '个人决策',
    },
  },
  {
    name: '创业者',
    data: {
      identities: ['创业者'], goals: ['创业选赛道'],
      domains: ['AI 与大模型', '消费与出海', '数字经济与就业'],
      content_prefs: ['产品发布', '资本动向'],
      outputs: ['竞品动态', '选题灵感'],
      horizon: '1-3 个月内',
    },
  },
  {
    name: '企业行业监测',
    data: {
      identities: ['职场人'], goals: ['企业情报监测'], perspective: '机构/企业决策',
      domains: ['半导体产业链', 'AI 与大模型', '新能源与储能'],
      content_prefs: ['政策与文件', '资本动向'],
      outputs: ['竞品动态', '可引用数据', '行动清单'],
      horizon: '1-3 个月内', reading_length: '3 分钟读完', tone: '中性客观',
    },
  },
]

const quotaPct = computed(() => {
  if (!quota.value || !quota.value.quota_total) return 0
  return Math.min(100, Math.round((quota.value.quota_used / quota.value.quota_total) * 100))
})

const score = computed(() => preview.value?.completeness?.score ?? 0)

function applyPersona(raw) {
  let persona = {}
  if (raw) {
    try { persona = JSON.parse(raw) || {} } catch { persona = {} }
  }
  const f = blankForm()
  const arr = (v) => (Array.isArray(v) ? v.slice() : typeof v === 'string' && v ? v.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [])
  f.identities = arr(persona.identities)
  f.field = persona.field || (persona.student?.major ?? '') || ''
  f.role_title = persona.role_title || ''
  f.goals = arr(persona.goals)
  f.domains = arr(persona.domains || persona.interests)
  f.content_prefs = arr(persona.content_prefs)
  f.outputs = arr(persona.outputs)
  f.avoid = arr(persona.avoid)
  f.perspective = persona.perspective || ''
  f.horizon = persona.horizon || ''
  f.risk = persona.risk || (persona.investor?.risk_preference ?? '') || ''
  f.reading_length = persona.reading_length || ''
  f.tone = persona.tone || ''
  f.pain_point = persona.pain_point || ''
  f.self_description = persona.self_description || ''
  f.extra_notes = persona.extra_notes || ''
  f.student = { ...persona.student, major: persona.student?.major || '', target_school: persona.student?.target_school || '' }
  f.entrepreneur = { ...persona.entrepreneur, industry: persona.entrepreneur?.industry || '', stage: persona.entrepreneur?.stage || '' }
  hydrated = false
  form.value = f
  dirty.value = false
  queueMicrotask(() => { hydrated = true })
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [p, q, m] = await Promise.all([api('/profile/'), api('/profile/quota'), api('/profile/persona-meta')])
    profile.value = p
    quota.value = q
    meta.value = m
    applyPersona(p.persona_json)
    await Promise.all([loadPreview(), loadSubscriptions()])
  } catch (e) {
    loadError.value = e.message
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function loadPreview() {
  previewError.value = ''
  try { preview.value = await api('/profile/persona-preview') } catch (e) { previewError.value = e.message; preview.value = null }
}

function applyPreset(p) {
  form.value = { ...blankForm(), ...form.value, ...p.data }
  t.ok(`已套用「${p.name}」预设，可继续微调`)
}

function adoptSuggest(key, value) {
  if (!Array.isArray(form.value[key]) || !value) return
  if (!form.value[key].includes(value)) form.value[key].push(value)
  suggestionStatus.value[`${key  }:${  value}`] = '已采纳到草稿'
  t.ok('已采纳到草稿，点「保存画像」后生效')
}

async function suggest() {
  suggesting.value = true
  suggestResult.value = null
  const storageKey = `ai-suggest-request:${getUser()?.id || 'current'}`
  let requestKey = sessionStorage.getItem(storageKey)
  if (!requestKey) { requestKey = crypto.randomUUID(); sessionStorage.setItem(storageKey, requestKey) }
  try {
    suggestResult.value = await api('/profile/persona-suggest', { method: 'POST', timeout: 180000, headers: { 'Idempotency-Key': requestKey } })
    sessionStorage.removeItem(storageKey)
    quota.value = await api('/profile/quota')
    suggestionStatus.value = {}
    t.ok('AI 已给出补全建议')
  } catch (e) {
    if (e.status && e.status !== 409) sessionStorage.removeItem(storageKey)
    if (e.status === 409 && e.message.includes('已结束')) sessionStorage.removeItem(storageKey)
    t.err(e.message)
  } finally {
    suggesting.value = false
  }
}

async function save() {
  if (saving.value) return
  saving.value = true
  try {
    const body = { ...form.value }
    // Keep legacy dictionary-form interests intact; v2 domains is the editable list.
    let original = {}
    try { original = JSON.parse(profile.value?.persona_json || '{}') } catch { /* empty profile */ }
    if (!original.interests || Array.isArray(original.interests)) body.interests = form.value.domains.slice()
    const res = await api('/profile/persona', { method: 'PUT', body })
    t.ok(`画像已保存（完成度 ${res.completeness?.score ?? 0}%）`)
    profile.value.persona_json = JSON.stringify(res.persona)
    applyPersona(profile.value.persona_json)
    await loadPreview()
    editing.value = {}
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

function fmtTime(s) { return s ? new Date(s).toLocaleString('zh-CN') : '—' }

onMounted(load)

const groups = [
  { id: 'identity', title: '身份与处境', icon: '01', tone: 'blue', fields: [
    { key: 'identities', label: '身份角色', kind: 'tags' },
    { key: 'field', label: '所在领域 / 专业', kind: 'text' },
    { key: 'role_title', label: '角色 / 职级', kind: 'text' },
    { key: 'self_description', label: '一句话自我介绍', kind: 'long' },
    { key: 'pain_point', label: '最近想解决的事', kind: 'long' },
  ] },
  { id: 'focus', title: '关注方向', icon: '02', tone: 'amber', fields: [
    { key: 'domains', label: '长期关注方向', kind: 'tags' },
  ] },
  { id: 'goals', title: '目标与产出', icon: '03', tone: 'green', fields: [
    { key: 'goals', label: '我最想解决的问题', kind: 'tags' },
    { key: 'outputs', label: '希望简报给出的东西', kind: 'tags' },
  ] },
  { id: 'style', title: '决策风格', icon: '04', tone: 'deep', fields: [
    { key: 'perspective', label: '决策视角', kind: 'single' },
    { key: 'horizon', label: '时间尺度', kind: 'single' },
    { key: 'risk', label: '风险偏好', kind: 'single' },
  ] },
  { id: 'reading', title: '阅读偏好', icon: '05', tone: 'slate', fields: [
    { key: 'content_prefs', label: '内容类型', kind: 'tags' },
    { key: 'reading_length', label: '阅读篇幅', kind: 'single' },
    { key: 'tone', label: '表达语气', kind: 'single' },
    { key: 'avoid', label: '不想看的内容', kind: 'tags' },
  ] },
]
const hasValue = value => Array.isArray(value) ? value.length > 0 : !!String(value || '').trim()
const dimensions = computed(() => groups.map(g => {
  const filled = g.fields.filter(f => hasValue(form.value[f.key])).length
  const first = g.fields.map(f => form.value[f.key]).find(hasValue)
  return { ...g, filled, pct: Math.round(filled / g.fields.length * 100), keyTag: (Array.isArray(first) ? first[0] : first) || '尚未填写' }
}))
const filledCount = computed(() => groups.flatMap(g => g.fields).filter(f => hasValue(form.value[f.key])).length)
const summary = computed(() => form.value.self_description || [form.value.role_title, form.value.identities.join('、'), form.value.field].filter(Boolean).join(' · ') || '还没有一句话画像，从下面的五个维度开始认识你。')
const suggestions = computed(() => Object.entries(suggestResult.value?.suggest || {}).filter(([k, v]) => ['domains','goals','content_prefs','outputs','avoid'].includes(k) && Array.isArray(v)).flatMap(([key, vals]) => vals.filter(v => typeof v === 'string' && v.trim()).map(value => ({ key, value, label: groups.flatMap(g => g.fields).find(f => f.key === key)?.label || key }))))
function jump(id) {
  const el = document.getElementById(`dim-${  id}`)
  el?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
  el?.focus({ preventScroll: true })
}
const subscriptionError = ref('')
async function loadSubscriptions() {
  subscriptionError.value = ''
  try { subscriptions.value = (await api('/subscriptions/')).map(s => ({ ...s, keywordTags: (s.keywords || '').split(/[,，、]/).map(v => v.trim()).filter(Boolean) })) }
  catch (e) { subscriptionError.value = e.message }
}
async function saveKeywords(sub) {
  if (keywordSaving.value !== null) return
  keywordSaving.value = sub.id
  try {
    await api(`/subscriptions/${  sub.id}`, { method: 'PUT', body: { keywords: sub.keywordTags.join('，') } })
    t.ok('订阅关键词已保存')
    await loadPreview()
  } catch (e) { t.err(e.message) }
  finally { keywordSaving.value = null }
}
watch(form, () => { if (hydrated) dirty.value = true }, { deep: true, flush: 'sync' })
function beforeUnload(e) { if (dirty.value) { e.preventDefault(); e.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
</script>
<template>
  <div class="persona-page">
    <div v-if="loading" class="loading-center" role="status">正在读取你的画像…</div>
    <div v-else-if="loadError" class="card empty" role="alert"><strong>画像暂时没有加载成功</strong><p>{{ loadError }}</p><button class="btn btn-outline" @click="load">重新加载</button></div>
    <template v-else>
      <div class="account-grid">
        <section class="card dim"><h2>账号信息</h2><p class="muted">邮箱</p><p class="field-value">{{ profile?.email || '—' }}</p><p class="muted">昵称 / 角色</p><p class="field-value">{{ profile?.nickname || '—' }} · {{ profile?.role?.toLowerCase() === 'admin' ? '管理员' : '普通用户' }}</p><p class="faint">上次登录 {{ fmtTime(profile?.last_login_at) }}</p></section>
        <section class="card dim"><h2>积分</h2><p class="kpi">{{ quota?.quota_remaining ?? '—' }}</p><p class="muted">本月剩余积分</p><div class="bar"><i :style="{ width: quotaPct + '%' }"></i></div><p class="muted">已使用 {{ quota?.quota_used ?? '—' }} / {{ quota?.quota_total ?? '—' }} 积分</p><p class="faint">处理中暂留 {{ quota?.quota_reserved ?? 0 }} 积分（成功结算，失败释放）</p><p class="faint">重置时间 {{ fmtTime(quota?.quota_reset_at) }}</p></section>
      </div>
      <p class="section-title">系统观察 <span class="faint">近 30 天真实记录，不作为画像自动写入</span></p>
      <p v-if="previewError" class="muted" role="status">系统观察暂不可用，未展示示例数据。</p>
      <div v-else class="observe-grid">
        <section class="card obs"><p class="kicker">简报与读后反馈</p><strong class="kpi">{{ preview?.observations?.reports ?? '—' }}<small>份</small></strong><p class="kpi-sub">有用 {{ preview?.observations?.feedback?.up ?? '—' }} / 没用 {{ preview?.observations?.feedback?.down ?? '—' }}</p><p class="src-label">来自简报记录与用户反馈</p></section>
        <section class="card obs"><h3>订阅方向</h3><p v-for="d in preview?.observations?.directions || []" :key="d.name" class="field-value">{{ d.name }} · {{ d.keywords?.join('、') }}</p><p v-if="!preview?.observations?.directions?.length" class="muted">暂无订阅方向记录</p><p class="src-label">来自当前订阅</p></section>
        <section class="card obs"><h3>常出现的信源</h3><p v-for="source in preview?.observations?.top_sources || []" :key="source.name" class="field-value">{{ source.name }} <span class="faint">{{ source.count }} 次</span></p><p v-if="!preview?.observations?.top_sources?.length" class="muted">还没有足够的简报记录</p><p class="src-label">来自近 30 天简报素材统计</p></section>
      </div>
      <p class="section-title">我的画像</p>
      <header class="profile-heading">
        <div><p class="kicker">SPOONBRIEF · 个人档案</p><h2>我的画像</h2><p class="muted">点按概览跳转。标签可添加、移除；修改后保存才会用于下一份简报。</p></div>
      </header>
      <section class="card summary">
        <div class="summary-body">
          <div class="summary-main">
            <div class="kicker">一句话画像</div><p class="persona-line">{{ summary }}</p>
            <div class="gap"></div><div class="kicker">最该补的 1–2 项</div>
            <p v-if="previewError" class="muted">完成度暂不可用：{{ previewError }}</p>
            <div v-else-if="preview?.completeness?.missing?.length" class="need-list">
              <button v-for="item in preview.completeness.missing.slice(0, 2)" :key="item.label" type="button" class="need-chip" :title="item.hint" @click="jump(item.label.includes('关注') ? 'focus' : item.label.includes('偏好') || item.label.includes('习惯') || item.label.includes('规避') ? 'reading' : item.label.includes('问题') || item.label.includes('输出') ? 'goals' : 'identity')">{{ item.label }}待补充</button>
            </div>
            <p v-else class="muted">{{ preview ? '主要信息已填写，可随时按近况调整。' : '暂无完成度数据' }}</p>
          </div>
          <div class="ring-wrap">
            <div class="ring" role="img" :aria-label="preview ? '已保存画像完成度' + score + '%' : '完成度暂无数据'">
              <svg viewBox="0 0 132 132" aria-hidden="true"><defs><linearGradient id="personaRingGrad"><stop offset="0%" stop-color="#2868ed" /><stop offset="100%" stop-color="#1859dc" /></linearGradient></defs><circle class="track" cx="66" cy="66" r="54" /><circle class="bar" cx="66" cy="66" r="54" :style="{ strokeDashoffset: 339.3 * (1 - score / 100) }" /></svg>
              <div class="ring-num"><strong>{{ preview ? score : '—' }}</strong><span>已保存完成度</span></div>
            </div>
            <div class="ring-meta">当前已填 {{ filledCount }} / 15 项<br />下方为各维度字段填写进度</div>
          </div>
        </div>
      </section>
      <nav class="mini-grid" aria-label="五个画像维度">
        <button v-for="g in dimensions" :key="g.id" type="button" class="card mini" @click="jump(g.id)">
          <div class="mini-top"><span class="ico" :class="g.tone">{{ g.icon }}</span><h3>{{ g.title }}</h3></div>
          <p class="filled">已填 {{ g.filled }} / {{ g.fields.length }} 项</p><span class="key-tag">{{ g.keyTag }}</span>
          <div class="bar-row"><div class="bar"><i :style="{ width: g.pct + '%' }"></i></div><span class="pct">{{ g.pct }}%</span></div>
        </button>
      </nav>
      <div class="profile-tools"><p class="section-title">维度详情</p><details><summary>一键预设</summary><div class="toolbar"><button v-for="p in PRESETS" :key="p.name" type="button" class="btn btn-outline btn-sm" @click="applyPreset(p)">{{ p.name }}</button></div><p class="faint">仅填入草稿，确认保存后生效。</p></details></div>
      <section v-for="g in dimensions" :id="'dim-' + g.id" :key="g.id" class="card dim" tabindex="-1">
        <div class="dim-head"><div class="dim-title"><span class="ico" :class="g.tone">{{ g.icon }}</span><div><h2>{{ g.title }}</h2><p class="hint">自定义标签支持回车添加；选中标签的 × 可移除。</p></div></div><button type="button" class="btn btn-ghost" :aria-expanded="!!editing[g.id]" @click="editing[g.id] = !editing[g.id]">{{ editing[g.id] ? '收起修改' : '修改' }}</button></div>
        <div v-for="field in g.fields" :key="field.key" class="group">
          <label v-if="field.kind === 'text' || field.kind === 'long'" :for="'profile-' + field.key" class="label">{{ field.label }}</label>
          <div v-else class="label">{{ field.label }}</div>
          <TagEditor v-if="field.kind === 'tags' || field.kind === 'single'" v-model="form[field.key]" :single="field.kind === 'single'" :label="field.label" :options="meta?.[field.key] || []" />
          <template v-else>
            <textarea v-if="editing[g.id] && field.kind === 'long'" :id="'profile-' + field.key" v-model="form[field.key]" class="textarea" :placeholder="'填写' + field.label"></textarea>
            <input v-else-if="editing[g.id]" :id="'profile-' + field.key" v-model="form[field.key]" class="input" :placeholder="'填写' + field.label" />
            <p v-else class="field-value">{{ form[field.key] || '尚未填写' }}</p>
          </template>
        </div>
        <template v-if="g.id === 'identity'">
          <div v-if="form.identities.includes('学生') || form.student.major || form.student.target_school" class="legacy-fields">
            <label class="field"><span>学生 · 专业</span><input v-model="form.student.major" class="input" /></label><label class="field"><span>目标院校</span><input v-model="form.student.target_school" class="input" /></label>
          </div>
          <div v-if="form.identities.includes('创业者') || form.entrepreneur.industry || form.entrepreneur.stage" class="legacy-fields">
            <label class="field"><span>创业行业</span><input v-model="form.entrepreneur.industry" class="input" /></label><label class="field"><span>创业阶段</span><input v-model="form.entrepreneur.stage" class="input" /></label>
          </div>
        </template>
        <div v-if="g.id === 'focus'" class="group subscription-keywords">
          <p class="label">订阅关键词</p>
          <p class="faint">来自真实订阅，单独保存，不会只写进画像。</p>
          <p v-if="subscriptionError" class="muted" role="status">暂时无法读取订阅：{{ subscriptionError }}</p>
          <p v-else-if="!subscriptions.length" class="muted">还没有订阅。<router-link to="/dashboard/subscriptions">去创建订阅</router-link></p>
          <div v-for="sub in subscriptions" :key="sub.id" class="keyword-sub">
            <p class="keyword-title">{{ sub.name || '未命名订阅' }}</p><TagEditor v-model="sub.keywordTags" :label="sub.name + '关键词'" />
            <button type="button" class="btn btn-outline btn-sm" :disabled="keywordSaving !== null" @click="saveKeywords(sub)">{{ keywordSaving === sub.id ? '保存中…' : '保存此订阅关键词' }}</button>
          </div>
        </div>
        <div class="edit-actions"><button type="button" class="btn btn-action" :disabled="saving || !dirty" @click="save">{{ saving ? '保存中…' : '保存画像' }}</button></div>
      </section>
      <section class="card dim">
        <h2>其他想让 AI 知道的</h2><label class="field"><span>任意补充（保留原有功能）</span><textarea v-model="form.extra_notes" class="textarea" placeholder="例如：不要推荐需要大额投入的方案"></textarea></label>
        <div class="edit-actions"><span v-if="dirty" class="faint" role="status">有未保存的画像修改</span><button type="button" class="btn btn-action" :disabled="saving || !dirty" @click="save">保存画像</button></div>
      </section>
      <div class="profile-tools"><p class="section-title">AI 补全建议</p><button type="button" class="btn btn-action" :disabled="suggesting" @click="suggest">{{ suggesting ? '分析中…' : '生成补全建议' }}</button></div>
      <section class="card suggest">
        <p v-if="!suggestResult" class="muted">还没有生成建议。成功生成消耗 2 积分，失败不扣；点「采纳」才放入草稿，保存后才会写入画像。</p>
        <template v-else><p class="muted">{{ suggestResult.reason }}</p><p v-if="suggestResult.persona_text" class="ai-line">{{ suggestResult.persona_text }}</p>
          <div v-for="item in suggestions" :key="item.key + ':' + item.value" class="sug-item"><div class="sug-body"><p class="sug-dim">{{ item.label }}</p><p class="sug-text">{{ item.value }}</p></div><span v-if="suggestionStatus[item.key + ':' + item.value]" class="status-pill ok">{{ suggestionStatus[item.key + ':' + item.value] }}</span><button v-else type="button" class="btn btn-action" @click="adoptSuggest(item.key, item.value)">采纳</button></div>
          <p v-if="!suggestions.length" class="muted">本次没有可采纳的字段建议。</p>
        </template>
      </section>
      <details class="card dim"><summary>AI 实际看到的画像（已保存）</summary><p class="field-value">{{ preview?.persona_text || '暂无已保存画像文本' }}</p></details>

    </template>
  </div>
</template>

<style scoped>
.persona-page { --fill:#2868ed;--deep:#1859dc;--soft:#eef5ff;--ink:#18304a;--secondary:#60748a;--muted:#72849b;--line:#dde8f5;--light:#fcfdff;--warning:#FAF1E5;--success-bg:#eef5ff;--token-green:#2868ed;--amber:#C97F26;--amber-bg:#FAF1E5;--action:#2868ed;--action-hover:#1859dc;--radius-card:16px;--radius-chip:12px;--shadow-card:0 18px 40px rgba(40,104,237,.06);--mono:ui-monospace,monospace;max-width:1120px;margin:0 auto; }
.profile-heading { display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px;flex-wrap:wrap; }
.profile-heading h2 { font-size:24px; }.field-toggle { display:flex;align-items:center;gap:8px;color:#596578;font-size:13px; }
.profile-tools { display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin:16px 0 12px; }.profile-tools .section-title { margin:0; }
.field-value { white-space:pre-wrap;overflow-wrap:anywhere;color:#596578;font-size:14px;line-height:1.8;margin:6px 0 14px; }
.legacy-fields,.account-grid { display:grid;grid-template-columns:1fr 1fr;gap:12px; }
.keyword-sub { border-top:1px solid #E7EBF1;padding-top:16px;margin-top:16px; }.keyword-title { font-size:14px;font-weight:600;margin-bottom:8px; }.keyword-sub > .btn { margin-top:8px; }
.persona-page .card h3::before { display:none; }.persona-page .mini h3 { margin:0;font-size:14px; }.persona-page .mini { padding:16px;text-align:left;font:inherit;min-width:0; }.persona-page .dim { padding:20px; }.persona-page .summary { padding:24px; }.persona-page .obs { padding:20px; }.persona-page .suggest { padding:20px;margin-bottom:24px; }.persona-page h2 { font-size:20px;margin-bottom:8px; }.persona-page h3 { margin:0 0 12px; }.persona-page .ring .bar { overflow:visible;background:none; }.ring svg { overflow:visible; }
.persona-page .dim:focus { outline:2px solid #2868ed;outline-offset:2px; }.persona-page .btn-ghost { border:1px solid #E7EBF1; }
.persona-page details > summary { cursor:pointer;font-weight:600;color:#596578; }.persona-page details[open] > summary { margin-bottom:12px; }
  .persona-page .card {
    background: rgba(255,255,255,.94);
    border: 1px solid #fff;
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-card);
  }
  .summary { padding: 24px; margin-bottom: 12px; }
  .summary-body { display: flex; gap: 32px; align-items: center; }
  .summary-main { flex: 1; min-width: 0; }
  .kicker { font-size: 12px; color: var(--muted); font-weight: 600; letter-spacing: .06em; margin-bottom: 8px; }
  .persona-line { font-size: 20px; font-weight: 650; line-height: 1.45; letter-spacing: -.01em; }
  .gap { height: 20px; }
  .need-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .need-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--warning);
    color: #8A5A28;
    border-radius: var(--radius-chip);
    padding: 6px 10px;
    font-size: 13px; font-weight: 600;
    text-decoration: none;
    border: 1px solid #E9D5BE;
  }
  .need-chip:hover { background: #F7E6D3; }
  .need-chip .fld { font-weight: 500; font-family: var(--mono); font-size: 11px; color: #A07A4A; }
  .persona-page:not(.show-fields) .fld { display: none; }

  .ring-wrap { flex: 0 0 148px; text-align: center; }
  .ring { position: relative; width: 132px; height: 132px; margin: 0 auto; }
  .ring svg { width: 132px; height: 132px; transform: rotate(-90deg); }
  .ring .track { fill: none; stroke: var(--line); stroke-width: 10; }
  .ring .bar {
    fill: none; stroke: url(#personaRingGrad); stroke-width: 10; stroke-linecap: round;
    stroke-dasharray: 339.3; stroke-dashoffset: 339.3; /* 76% of 2π·54 */
  }
  .ring-num {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  .ring-num strong {
    font-size: 34px; font-weight: 700; letter-spacing: -.03em;
    font-variant-numeric: tabular-nums; line-height: 1;
  }
  .ring-num span { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .ring-meta { margin-top: 8px; font-size: 12px; color: var(--secondary); }
  .ring-meta b { color: var(--ink); font-weight: 650; font-variant-numeric: tabular-nums; }

  .mini-grid {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 12px; margin-bottom: 24px;
  }
  .mini {
    display: block; text-decoration: none; color: inherit;
    padding: 16px; cursor: pointer;
    transition: transform .2s, box-shadow .2s;
  }
  .mini:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(47,74,134,.16); }
  .mini-top { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
  .ico {
    width: 28px; height: 28px; border-radius: 8px;
    display: grid; place-items: center; flex: 0 0 28px;
  }
  .ico svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
  .ico.blue { background: var(--soft); color: var(--blue); }
  .ico.amber { background: var(--amber-bg); color: var(--amber); }
  .ico.green { background: var(--success-bg); color: var(--token-green); }
  .ico.deep { background: #E8ECF8; color: var(--deep); }
  .ico.slate { background: var(--light); color: var(--secondary); }
  .mini h3 { font-size: 14px; font-weight: 650; line-height: 1.3; }
  .filled { font-size: 12px; color: var(--muted); margin-bottom: 8px; font-variant-numeric: tabular-nums; }
  .key-tag {
    display: inline-block; max-width: 100%;
    font-size: 12px; font-weight: 600; color: var(--blue);
    background: var(--soft); border-radius: 10px;
    padding: 3px 8px; margin-bottom: 12px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .bar { height: 6px; background: var(--line); border-radius: 99px; overflow: hidden; }
  .bar > i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--fill), var(--deep)); }
  .bar-row { display: flex; align-items: center; gap: 8px; }
  .bar-row .bar { flex: 1; }
  .pct { font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; width: 28px; text-align: right; }

  .section-title {
    font-size: 13px; font-weight: 650; color: var(--secondary);
    margin: 8px 0 12px; letter-spacing: .04em;
  }
  .dim { padding: 20px; margin-bottom: 12px; scroll-margin-top: 64px; }
  .dim.is-flash { outline: 2px solid var(--blue); outline-offset: 2px; }
  .dim-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
  .dim-title { display: flex; align-items: center; gap: 10px; }
  .dim-title h2 { font-size: 20px; font-weight: 700; letter-spacing: -.02em; }
  .dim-title .hint { font-size: 12px; color: var(--muted); font-weight: 400; margin-top: 2px; }
  .btn {
    border: 0; cursor: pointer; border-radius: var(--radius-chip);
    font-size: 13px; font-weight: 600; padding: 7px 12px;
    transition: background .15s, color .15s, box-shadow .15s;
  }
  .btn:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
  .btn-ghost { background: var(--light); color: var(--secondary); }
  .btn-ghost:hover { background: var(--soft); color: var(--blue); }
  .btn-action { background: var(--action); color: #fff; }
  .btn-action:hover { background: var(--action-hover); }
  .btn-outline {
    background: #fff; color: var(--secondary);
    box-shadow: inset 0 0 0 1px var(--line);
  }
  .btn-outline:hover { color: var(--ink); box-shadow: inset 0 0 0 1px #C9D1DE; }
  .ai-line {
    background: var(--soft); border-radius: 12px; padding: 12px 14px;
    font-size: 15px; color: var(--ink); line-height: 1.65; margin-bottom: 14px;
  }
  .ai-line em { font-style: normal; font-weight: 650; color: var(--deep); margin-right: 6px; }
  .group { margin-bottom: 14px; }
  .group:last-child { margin-bottom: 0; }
  .label {
    font-size: 12px; color: var(--muted); margin-bottom: 8px;
    display: flex; align-items: baseline; gap: 8px;
  }
  .fld, .label .fld { font-family: var(--mono); font-size: 11px; color: #9AA3B2; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag {
    display: inline-flex; align-items: center; gap: 4px;
    border: 1px solid var(--line); background: #fff;
    color: var(--secondary); border-radius: 999px;
    padding: 5px 11px; font-size: 13px; cursor: pointer; user-select: none;
    transition: background .15s, color .15s, border-color .15s;
  }
  .tag:hover { border-color: #C9D1DE; }
  .tag.on { background: var(--soft); color: var(--blue); border-color: #D0D8FF; font-weight: 600; }
  .tag.empty {
    display: inline-flex;
    width: max-content;
    max-width: 100%;
    border-style: dashed;
    background: transparent;
    color: var(--muted);
    cursor: default;
  }
  textarea, .text-input {
    width: 100%; border: 1px solid var(--line); border-radius: 12px;
    padding: 10px 12px; font-size: 14px; color: var(--ink); background: #fff;
    resize: vertical; min-height: 72px; outline: none;
  }
  .text-input { min-height: 0; }
  textarea:focus, .text-input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(77,107,254,.15); }
  .edit-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
  .add-row { display: flex; gap: 8px; margin-top: 8px; }
  .add-row .text-input { flex: 1; }

  .observe-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 24px;
  }
  .obs { padding: 18px 20px; min-height: 168px; display: flex; flex-direction: column; }
  .obs h3 { font-size: 15px; font-weight: 650; margin: 8px 0 12px; }
  .src-label {
    font-size: 11px; color: var(--muted); letter-spacing: .02em;
    margin-top: auto; padding-top: 12px;
  }
  .kpi { font-size: 34px; font-weight: 700; letter-spacing: -.03em; font-variant-numeric: tabular-nums; line-height: 1; }
  .kpi small { font-size: 14px; font-weight: 600; color: var(--muted); margin-left: 2px; }
  .kpi-sub { font-size: 12px; color: var(--secondary); margin: 8px 0 12px; }
  .empty {
    flex: 1; display: flex; flex-direction: column; align-items: flex-start; justify-content: center;
    border: 1px dashed var(--line); border-radius: 12px; padding: 16px;
    background: var(--light); color: var(--secondary); font-size: 14px;
  }
  .empty strong { display: block; font-size: 14px; color: var(--ink); margin-bottom: 4px; font-weight: 650; }
  .empty span { font-size: 12px; color: var(--muted); }

  .suggest { padding: 8px 8px 8px 20px; margin-bottom: 12px; }
  .sug-item {
    display: flex; align-items: center; gap: 16px;
    padding: 14px 12px 14px 0;
    border-bottom: 1px solid var(--line);
  }
  .sug-item:last-child { border-bottom: 0; }
  .sug-item.gone { opacity: .45; }
  .sug-body { flex: 1; min-width: 0; }
  .sug-dim { font-size: 12px; color: var(--muted); margin-bottom: 2px; }
  .sug-text { font-size: 15px; }
  .sug-text b { font-weight: 650; }
  .sug-actions { display: flex; gap: 8px; flex-shrink: 0; }
  .status-pill {
    font-size: 12px; font-weight: 650; border-radius: 999px; padding: 5px 10px;
  }
  .status-pill.ok { background: var(--success-bg); color: var(--token-green); }
  .status-pill.no { background: var(--light); color: var(--muted); }

  footer.note { text-align: center; font-size: 12px; color: var(--muted); margin-top: 28px; }


@media(max-width:1000px) { .mini-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }.observe-grid { grid-template-columns:1fr; } }
@media(max-width:600px) { .mini-grid { grid-template-columns:1fr; }.summary-body { flex-direction:column;align-items:stretch;gap:20px; }.ring-wrap { flex:none; }.persona-line { font-size:18px; }.sug-item { flex-wrap:wrap; }.legacy-fields,.account-grid { grid-template-columns:1fr; }.persona-page .card { padding:16px; }.dim-head { gap:8px; }.dim-title h2 { font-size:18px; } }

</style>
