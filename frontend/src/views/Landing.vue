<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import Modal from '../components/Modal.vue'
import WindowFrame from '../components/WindowFrame.vue'
import { ICP_RECORD, ICP_URL, effectiveText } from '../compliance'

const compliance = ref({ icp_record: ICP_RECORD, privacy_policy: '', disclaimer: '' })

/* ── 合规文本：页脚链接 + 弹窗结构化展示 ── */
const policyModal = ref(null)   // 'privacy' | 'disclaimer' | null

function openPolicy(k) { policyModal.value = k }

const policyTitle = computed(() => (policyModal.value === 'privacy' ? '隐私政策' : '免责声明'))

const POLICY_KEYS = { privacy: 'privacy_policy', disclaimer: 'disclaimer' }

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function linkify(text) {
  let s = escapeHtml(text)
  s = s.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '<a href="mailto:$1">$1</a>')
  s = s.replace(/(https?:\/\/[^\s<>"']+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
  return s
}

const policyHtml = computed(() => {
  const raw = compliance.value[POLICY_KEYS[policyModal.value]] || ''
  const lines = raw.split('\n')
  if (lines[0] && lines[0].trim() === policyTitle.value) lines.shift()
  return linkify(lines.join('\n'))
})

/* ── 打字机：轮播关注方向 ── */
const examples = ['半导体 国产替代', 'AI 大模型 应用落地', '黄金 原油 美联储', '考研 政策 招生', '新能源 出海 电池', '人形机器人 量产']
const typedText = ref('')
let typeTimer = null
let exIdx = 0
let charIdx = 0
let deleting = false

function tickTyping() {
  const target = examples[exIdx]
  if (!deleting) {
    charIdx += 1
    typedText.value = target.slice(0, charIdx)
    if (charIdx >= target.length) {
      deleting = true
      typeTimer = setTimeout(tickTyping, 1500)
      return
    }
    typeTimer = setTimeout(tickTyping, 80)
  } else {
    charIdx -= 1
    typedText.value = target.slice(0, charIdx)
    if (charIdx <= 0) {
      deleting = false
      exIdx = (exIdx + 1) % examples.length
    }
    typeTimer = setTimeout(tickTyping, 40)
  }
}

/* ── 滚动渐显 ── */
let observer = null
function setupReveal() {
  observer = new IntersectionObserver(
    (entries) => entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('visible')
        observer.unobserve(e.target)
      }
    }),
    { threshold: 0.12 }
  )
  document.querySelectorAll('.reveal').forEach((el) => observer.observe(el))
}

/* ── 热点词滚动条：点击直达演示台并选中方向 ── */
const hotWords = ['半导体', 'AI 大模型', '新能源车', '黄金', '考研政策', '人形机器人', '低空经济', '美联储', '算力', '出海']

function useHotWord(w) {
  if (!selectedTags.value.includes(w)) selectedTags.value.push(w)
  document.querySelector('#demo-stage')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

/* ══════════ 交互演示台：亲手生成一份简报 ══════════ */
const reducedMotion = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const DEMO_TAGS = {
  '半导体': {
    insight: '示例：可关注国产算力与产业链的细分需求，结合自己的专业背景核对相关机会。',
    news: [
      { t: '示例 · 国产算力与芯片研发方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 半导体设备与产业链方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  'AI 大模型': {
    insight: '示例：可关注 AI 应用的实际需求与使用边界，先核对场景，再评估机会与风险。',
    news: [
      { t: '示例 · AI 应用与开源工具方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · AI 学习与使用边界方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '新能源车': {
    insight: '示例：可关注电池回收、补能与出海合规等细分方向，具体机会仍需核对原始报道。',
    news: [
      { t: '示例 · 动力电池与回收方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 新能源车与出海方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '黄金': {
    insight: '示例：可关注影响黄金的公开信息，同时留意价格波动风险；示例不构成投资建议。',
    news: [
      { t: '示例 · 黄金与避险需求方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 货币政策与市场预期方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '考研政策': {
    insight: '示例：可对照目标院校的公开简章，整理招生与专业设置的变化，具体要求以官方文件为准。',
    news: [
      { t: '示例 · 招生简章与专业设置方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 考研政策与院校信息方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '人形机器人': {
    insight: '示例：可关注零部件与应用场景，区分技术进展和市场预期，避免只看概念。',
    news: [
      { t: '示例 · 机器人零部件方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 机器人应用与研发方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '低空经济': {
    insight: '示例：可关注基础设施与适航政策，进一步核对公开文件中的适用条件。',
    news: [
      { t: '示例 · 低空经济与基础设施方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 适航政策与应用场景方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '美联储': {
    insight: '示例：可关注货币政策相关公开报道，区分政策事实与市场预期。',
    news: [
      { t: '示例 · 货币政策与公开讲话方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 市场预期与资产风险方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '算力': {
    insight: '示例：可关注算力设施与能源协同等交叉方向，结合实际需求评估相关机会。',
    news: [
      { t: '示例 · 算力设施与芯片方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 算力与能源协同方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
  '出海': {
    insight: '示例：可关注本地化与合规要求，留意目标市场政策变化，避免只看增长叙事。',
    news: [
      { t: '示例 · 出海合规与本地化方向', src: '公开报道 A（格式示意）', cross: true },
      { t: '示例 · 品牌与市场需求方向', src: '公开报道 B（格式示意）', cross: false },
    ],
  },
}

const ALL_TAGS = Object.keys(DEMO_TAGS)
const selectedTags = ref([])
const phase = ref('idle')        // idle | ready | collect | analyze | deliver | done
const statusLine = ref('')
const demoBrief = ref(null)      // { insight, news }
const tracedIdx = ref(-1)

// 演示台步骤条：把「订阅 → 收到订阅信息」的完整旅程可视化
const demoSteps = ['订阅方向', 'AI 分析', '定时送达', '收到简报']
const phaseStep = { ready: 0, collect: 0, analyze: 1, deliver: 2, done: 3 }

// 溯源卖点区：证据链展开
const proofOpen = ref(false)

/* ── 本地新增：身份快选（合并进演示台） ── */
const IDENTITIES = [
  { k: '学生', icon: '🎓', tags: ['考研政策', 'AI 大模型'] },
  { k: '职场人', icon: '💻', tags: ['AI 大模型', '算力'] },
  { k: '投资者', icon: '📈', tags: ['黄金', '美联储', '半导体'] },
  { k: '创业者', icon: '🚀', tags: ['出海', '低空经济'] },
  { k: '创作者', icon: '📣', tags: ['新能源车', '人形机器人'] },
]
const identity = ref('')
function pickIdentity(it) {
  if (['collect', 'analyze', 'deliver'].includes(phase.value)) return
  identity.value = it.k
  selectedTags.value = it.tags.filter((t) => ALL_TAGS.includes(t)).slice(0, 3)
  phase.value = 'ready'; demoBrief.value = null
}

/* ── 本地新增：价格 ── */
const PLANS = [
  { name: '体验', price: 1, note: '新用户体验额度，体验规则以后台为准' },
  { name: 'VIP', price: 39, days: 30 },
  { name: 'SVIP', price: 59, days: 30, hot: true },
  { name: 'SSVIP', price: 79, days: 30 },
  { name: 'SSSVIP', price: 99, days: 30 },
]

const timelineNodes = [
  { time: '订阅就绪', text: '订阅与画像就绪后，任务进入待命' },
  { time: '送达前', text: '按画像检索相关公开报道' },
  { time: '整理简报', text: 'AI 整理成简报并标注出处' },
  { time: '示例 09:00', text: '你设定的时间，简报发到邮箱' },
]

const features = [
  { title: '按画像整理', text: '根据你填写的身份与兴趣，检索相关机会与热点并整理成简报，而不是再扔给你一堆链接。' },
  { title: '结论可溯源', text: '每条新闻都附「读原文」链接，并标注信源可信度分级（这是信源权威分级，不是内容真伪判定）。' },
  { title: '定时发送', text: '用北京时间设定发送节奏，默认每天 09:00，也可改成其他时间；支持多个收件邮箱。' },
  { title: '你的视角', text: '画像里可以选多个身份，AI 会结合你填写的身份与兴趣来写，同样一条新闻会带上对你而言的角度。' },
]

const FLY_HEADLINES = ['半导体与国产算力', 'AI 应用与开源工具', '黄金与市场预期', '低空经济与基础设施', '考研政策与招生方向', '机器人与零部件', '新能源车与电池回收', '货币政策与风险', '出海合规与本地化', '算力与能源协同']

function toggleTag(t) {
  const i = selectedTags.value.indexOf(t)
  if (i >= 0) selectedTags.value.splice(i, 1)
  else if (selectedTags.value.length < 3) selectedTags.value.push(t)
  if (selectedTags.value.length && phase.value === 'idle') phase.value = 'ready'
  if (!selectedTags.value.length && phase.value === 'ready') phase.value = 'idle'
  tracedIdx.value = -1
}

const sleep = (ms) => new Promise((r) => setTimeout(r, reducedMotion ? Math.min(ms, 120) : ms))

async function generate() {
  if (!selectedTags.value.length || phase.value === 'collect' || phase.value === 'analyze' || phase.value === 'deliver') return
  tracedIdx.value = -1
  demoBrief.value = null

  const tags = selectedTags.value
  const primary = DEMO_TAGS[tags[0]]
  const mergedNews = []
  const seen = new Set()
  tags.forEach((t) => (DEMO_TAGS[t].news || []).forEach((n) => {
    if (!seen.has(n.t)) { seen.add(n.t); mergedNews.push(n) }
  }))
  const insight = tags.length > 1
    ? `你同时关注「${tags.join('、')}」——以下示例展示按多个方向整理的格式。` + primary.insight
    : primary.insight

  phase.value = 'collect'
  await sleep(1400)
  phase.value = 'analyze'
  const lines = [
    `正在读取你选择的方向：${tags.join('、')}…`,
    '正在整理示例要点…',
    '正在展示溯源格式…',
    '正在呈现简报示例…',
  ]
  for (const line of lines) {
    statusLine.value = line
    await sleep(reducedMotion ? 120 : 620)
  }
  phase.value = 'deliver'
  await sleep(reducedMotion ? 120 : 1100)
  demoBrief.value = { insight, news: mergedNews.slice(0, 4) }
  phase.value = 'done'
}

function trace(i) {
  tracedIdx.value = tracedIdx.value === i ? -1 : i
}

function resetDemo() {
  phase.value = 'idle'
  demoBrief.value = null
  tracedIdx.value = -1
}

onMounted(async () => {
  if (reducedMotion) typedText.value = examples[0]
  else tickTyping()
  setupReveal()
  try {
    const raw = await api('/public/icp')
    compliance.value = Object.fromEntries(
      Object.keys(compliance.value).map((key) => {
        return [key, effectiveText(raw?.[key], key === 'icp_record' ? ICP_RECORD : '')]
      })
    )
  } catch { /* 忽略 */ }
})

onBeforeUnmount(() => {
  clearTimeout(typeTimer)
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="lp-root">
    <!-- ═══ 顶部导航 ═══ -->
    <header class="land-nav">
      <div class="navbar">
        <router-link to="/" class="brand">
          <img src="/favicon.svg" alt="一勺热点" />
          一勺热点
        </router-link>
        <nav class="nav-links">
          <a href="#duo" class="nav-anchor">思忆</a>
          <a href="#pricing" class="nav-anchor">价格</a>
          <template v-if="auth.isLoggedIn">
            <router-link to="/dashboard/subscriptions"><button class="btn btn-outline btn-sm">进入控制台</button></router-link>
          </template>
          <template v-else>
            <router-link to="/login"><button class="btn btn-outline btn-sm">登录</button></router-link>
            <router-link to="/register"><button class="btn btn-primary btn-sm">免费注册</button></router-link>
          </template>
        </nav>
      </div>
    </header>

    <!-- ═══ Hero ═══ -->
    <section class="hero lp-hero">
      <div class="hero-orb" style="width: 260px; height: 260px; top: -60px; left: -60px"></div>
      <div class="hero-orb" style="width: 150px; height: 150px; top: 46px; right: 8%; animation-delay: 1.4s"></div>
      <div class="hero-orb" style="width: 90px; height: 90px; bottom: 26px; left: 12%; animation-delay: 2.6s"></div>

      <!-- 漂浮新闻卡片（左右分布，从加载起持续晃动） -->
      <div class="float-card fc-1"><p><i class="hot-tag">热</i>半导体 · 产业链方向</p><span>关注方向</span></div>
      <div class="float-card fc-2"><p><i class="hot-tag">热</i>黄金 · 市场预期</p><span>关注方向</span></div>
      <div class="float-card fc-3"><p><i class="hot-tag">热</i>AI · 学习与应用</p><span>关注方向</span></div>
      <div class="float-card fc-4"><p><i class="hot-tag">热</i>低空经济 · 基建方向</p><span>关注方向</span></div>
      <div class="float-card fc-5"><p><i class="hot-tag">热</i>考研 · 招生政策</p><span>关注方向</span></div>
      <div class="float-card fc-6"><p><i class="hot-tag">热</i>出海 · 合规方向</p><span>关注方向</span></div>
      <div class="float-card fc-7"><p><i class="hot-tag">热</i>机器人 · 零部件</p><span>关注方向</span></div>
      <div class="float-card fc-8"><p><i class="hot-tag">热</i>黄金 · 风险关注</p><span>关注方向</span></div>
      <div class="float-card fc-9"><p><i class="hot-tag">热</i>大模型 · 应用场景</p><span>关注方向</span></div>
      <div class="float-card fc-10"><p><i class="hot-tag">热</i>算力 · 能源协同</p><span>关注方向</span></div>

      <h1 class="hero-title">按你的画像，把热点和机会<br /><em>喂到你嘴边</em></h1>
      <p class="sub">根据你的个人画像，AI 定时检索网上的机会与热点，<br class="pc-only" />整理成简报，按你设定的时间发到邮箱。</p>

      <div class="hero-actions">
        <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-solid btn-lg">进入控制台，管理你的订阅</button></router-link>
        <router-link v-else to="/register"><button class="btn btn-solid btn-lg">免费注册，创建订阅后按时收简报</button></router-link>
        <button class="btn btn-soft btn-lg" @click="useHotWord('AI 大模型')">先体验：看一份简报长什么样</button>
      </div>

      <!-- 卖点信任条 -->
      <div class="hero-trust">
        <span class="trust-item">结论可指向原报道</span>
        <span class="trust-dot"></span>
        <span class="trust-item">每条新闻附原文链接</span>
        <span class="trust-dot"></span>
        <span class="trust-item">按你设定的时间发送</span>
        <span class="trust-dot"></span>
        <span class="trust-item">会员与开通说明</span>
      </div>

      <p class="typing-line">关注方向示例：<span class="typed">{{ typedText }}</span><span class="typing-caret"></span></p>

      <!-- 热点词滚动条（多组铺满屏幕，无缝循环） -->
      <div class="ticker-wrap">
        <div class="ticker">
          <div v-for="n in 5" :key="n" class="ticker-group">
            <button v-for="w in hotWords" :key="w + n" type="button" class="hot-chip" @click="useHotWord(w)">{{ w }}</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 痛点：信息瀑布 vs 一页简报 ═══ -->
    <section class="section pain-section">
      <h2 class="reveal">信息很多，真正跟你有关的很少</h2>
      <p class="lead reveal">与其在信息流里自己捡，不如让一封简报先帮你筛一遍</p>
      <div class="pain-grid">
        <div class="pain-side reveal">
          <p class="pain-label pain-label-bad">没有 一勺热点 的早晨</p>
          <div class="waterfall">
            <div class="wf-col">
              <p v-for="(t, i) in FLY_HEADLINES.slice(0, 10)" :key="'a' + i">{{ t }}</p>
              <p v-for="(t, i) in FLY_HEADLINES.slice(0, 10)" :key="'a2' + i">{{ t }}</p>
            </div>
          </div>
          <p class="pain-caption">刷完信息流，记住的往往只剩焦虑</p>
        </div>
        <div class="pain-vs reveal">→</div>
        <div class="pain-side reveal">
          <p class="pain-label pain-label-good">有了 一勺热点 的早晨</p>
          <div class="brief-mini">
            <div class="brief-mini-head">一勺热点 · 简报示例</div>
            <div class="brief-mini-body">
              <p class="b-h">你的机会</p>
              <p class="b-t">示例：关注国产算力方向，结合专业背景核对细分需求</p>
              <p class="b-h">你的风险</p>
              <p class="b-t">示例：使用 AI 工具时，留意信息核对与独立判断</p>
              <p class="b-h">溯源</p>
              <p class="b-t">示例：原报道出处 · 信源分级</p>
            </div>
          </div>
          <p class="pain-caption">打开邮箱，先读一封按你的画像整理的简报</p>
        </div>
      </div>
    </section>

    <!-- ═══ 交互演示台 ═══ -->
    <section id="demo-stage" class="section demo-section">
      <h2 class="reveal">别听我讲，先看一份简报长什么样</h2>
      <p class="lead reveal">选 1-3 个方向查看演示。这是示例，不是此刻检索生成的真实简报。<br />实际信息源以国内公开报道为主，国外源较少。</p>

      <div class="demo-wrap reveal">
        <!-- 步骤条：订阅 → 收到订阅信息 -->
        <div class="demo-steps">
          <div
            v-for="(s, i) in demoSteps"
            :key="s"
            class="dstep"
            :class="{ on: (phaseStep[phase] ?? -1) >= i, active: (phaseStep[phase] ?? -1) === i }"
          >
            <span class="dstep-dot">{{ i + 1 }}</span>{{ s }}
          </div>
        </div>

        <!-- 本地新增：选个身份（一键预选方向） -->
        <div class="id-picker">
          <span class="id-label">选个身份</span>
          <button v-for="it in IDENTITIES" :key="it.k" type="button" class="id-chip"
            :class="{ active: identity === it.k }" @click="pickIdentity(it)">{{ it.icon }} {{ it.k }}</button>
        </div>
        <!-- 方向选择 -->
        <div class="demo-picker">
          <button
            v-for="t in ALL_TAGS"
            :key="t"
            type="button"
            class="tag-chip"
            :class="{ active: selectedTags.includes(t) }"
            @click="toggleTag(t)"
          >{{ t }}</button>
          <button class="btn btn-primary" :disabled="!selectedTags.length || ['collect','analyze','deliver'].includes(phase)" @click="generate">
            <span v-if="['collect','analyze','deliver'].includes(phase)" class="spinner"></span>
            {{ ['collect','analyze','deliver'].includes(phase) ? '生成中…' : '生成简报示例' }}
          </button>
        </div>

        <!-- 舞台（外层类用 phase-* 命名空间，避免与内部 stage-* 内容类冲突） -->
        <WindowFrame class="demo-window" title="简报预览 · 演示示例" flush>
        <div class="demo-stage" :class="'phase-' + phase">
          <!-- 待机 -->
          <div v-if="phase === 'idle' || phase === 'ready'" class="stage-idle">
            <div class="idle-spoon"></div>
            <p v-if="phase === 'ready'">方向已选好：{{ selectedTags.join('、') }}，点上方「生成简报示例」开始</p>
            <p v-else>选择方向，查看「信息喂到嘴边」的演示示例</p>
          </div>

          <!-- 收集：新闻飞入 -->
          <div v-if="phase === 'collect'" class="stage-collect">
            <span v-for="(h, i) in FLY_HEADLINES.slice(0, 9)" :key="'fly' + i" class="fly-chip" :style="{ '--i': i }">{{ h }}</span>
          </div>

          <!-- 分析：AI 核心 -->
          <div v-if="phase === 'analyze'" class="stage-analyze">
            <div class="core-wrap">
              <div class="core-ring ring-a"></div>
              <div class="core-ring ring-b"></div>
              <div class="core-ball"></div>
            </div>
            <p class="status-line">{{ statusLine }}</p>
          </div>

          <!-- 送达：信封飞向邮箱 -->
          <div v-if="phase === 'deliver'" class="stage-deliver">
            <svg class="env" viewBox="0 0 64 44" width="56" height="40">
              <rect x="1" y="1" width="62" height="42" rx="6" fill="#fff" stroke="#5B7CFF" stroke-width="2.5" />
              <path d="M2 4 L32 26 L62 4" fill="none" stroke="#5B7CFF" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            <div class="mailbox">
              <div class="mb-flag"></div>
              <div class="mb-clock">09:00</div>
            </div>
          </div>

          <!-- 完成：展开简报（可溯源） -->
          <div v-if="phase === 'done' && demoBrief" class="stage-brief">
            <div class="brief-head">
              <div class="brief-stamp">示例</div>
              <p class="brief-sub">简报示例 · 结合你的兴趣「{{ selectedTags.join('、') }}」</p>
            </div>
            <div class="brief-body">
              <p class="brief-h">按画像整理 · 示例</p>
              <p class="brief-p">{{ demoBrief.insight }}</p>
              <p class="brief-h">报道格式示例 · 点击任意一条查看溯源格式</p>
              <div
                v-for="(n, i) in demoBrief.news"
                :key="i"
                class="trace-item"
                :class="{ open: tracedIdx === i }"
                @click="trace(i)"
              >
                <p class="trace-t">{{ i + 1 }}. {{ n.t }}</p>
                <p class="trace-meta">示例出处：{{ n.src }} · 信源分级</p>
                <div v-if="tracedIdx === i" class="trace-detail">
                  <div class="trace-line"></div>
                  <p class="trace-src">溯源格式示例：{{ n.src }}</p>
                  <p class="trace-note">此处仅展示格式，不是真实报道。信源分级供你参考。</p>
                </div>
              </div>
            </div>
            <div class="brief-actions">
              <span class="subscribed-chip">发送时间示例 · 默认北京时间 09:00</span>
              <div class="brief-btns">
                <button class="btn btn-outline btn-sm" @click="resetDemo">换一批方向，再来一次</button>
                <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-primary btn-sm">进入控制台，创建订阅</button></router-link>
                <router-link v-else to="/register"><button class="btn btn-primary btn-sm">注册，创建你的订阅</button></router-link>
              </div>
            </div>
          </div>
        </div>
        </WindowFrame>
      </div>
    </section>

    <!-- ═══ 定时送达时间轴 ═══ -->
    <section class="section">
      <h2 class="reveal">你睡觉时，它在工作</h2>
      <p class="lead reveal">你设定北京时间的送达时刻；系统会在此之前检索、整理并发出。下面以默认早上 9 点为例。</p>
      <div class="timeline reveal">
        <div class="tl-node" v-for="(node, i) in timelineNodes" :key="node.time" :style="{ '--d': i }">
          <div class="tl-dot"></div>
          <p class="tl-time">{{ node.time }}</p>
          <p class="tl-text">{{ node.text }}</p>
        </div>
      </div>
    </section>

    <!-- ═══ 四大能力 ═══ -->
    <section class="section" style="padding-top: 0">
      <h2 class="reveal">四件事，它替你做完</h2>
      <p class="lead reveal">帮你整理信息，判断仍由你自己做</p>
      <div class="features">
        <div class="feature reveal" v-for="f in features" :key="f.title">
          <div class="feature-bar"></div>
          <h4>{{ f.title }}</h4>
          <p>{{ f.text }}</p>
        </div>
      </div>
    </section>

    <!-- ═══ 卖点凸显：溯源可信 ═══ -->
    <section class="section proof-section">
      <h2 class="reveal">AI 可能说错，所以每条都要能查到来源</h2>
      <p class="lead reveal">简报里的要点会指向原始公开报道。下面是交互示意，不是一条实时结论。</p>
      <div class="proof-card reveal">
        <div class="proof-conclusion" :class="{ open: proofOpen }" @click="proofOpen = !proofOpen">
          <span class="proof-tag">AI 结论 · 示例</span>
          <p>「示例：关注国产算力相关公开报道，结合专业背景核对细分需求」</p>
          <span class="proof-hint">{{ proofOpen ? '收起证据链' : '点击查看证据链' }}</span>
        </div>
        <div v-if="proofOpen" class="proof-chain">
          <div class="proof-line"></div>
          <div class="proof-evid">
            <p class="pe-title">出处示例 A · 国产算力与研发方向公开报道</p>
            <p class="pe-meta">格式示意：原报道链接 · 信源权威分级</p>
          </div>
          <div class="proof-evid">
            <p class="pe-title">出处示例 B · 产业链与设备方向公开报道</p>
            <p class="pe-meta">格式示意：每条新闻附信源分级和原文链接</p>
          </div>
          <p class="proof-note">AI 的句子会标注出处；它说错了，你能查到原始报道。判断权在你手里。</p>
        </div>
      </div>
    </section>

    <!-- ═══ 产品事实：不依赖营销数字或计数动画 ═══ -->
    <section class="section stats-band">
      <div class="stat reveal"><p class="stat-fact">要点可指向原报道</p><p class="stat-label">对应简报中的溯源能力</p></div>
      <div class="stat reveal"><p class="stat-fact">每条附原文链接</p><p class="stat-label">信源按权威度分级，不代表内容真伪</p></div>
      <div class="stat reveal"><p class="stat-fact">按你设定的时间发送</p><p class="stat-label">用北京时间设定发送节奏</p></div>
      <div class="stat reveal"><p class="stat-fact">默认北京时间 09:00</p><p class="stat-label">可按你的需要调整时间</p></div>
    </section>

    <!-- ═══ 双产品：网页简报与 App 私人助理 ═══ -->
    <section id="duo" class="section duo-section">
      <h2 class="reveal">网页帮你看清机会，App 帮你把事情跟下去</h2>
      <p class="lead reveal">一勺热点和 AiLifeOS 是相关产品。一个把简报发到邮箱，一个在手机里处理日常事务。本页不把登录关系写成已经完成合并。</p>
      <div class="duo-grid">
        <article class="duo-card reveal">
          <span class="duo-label">网页简报</span>
          <h3>一勺热点 · 网页</h3>
          <p>根据你的个人画像，AI 定时检索网上的机会与热点，整理成简报，按你设定的时间发到邮箱。要点可指向原始公开报道。</p>
        </article>
        <article class="duo-card duo-app reveal">
          <span class="duo-label">App 私人助理</span>
          <h3>AiLifeOS · 思忆</h3>
          <p class="duo-position">记得住你、会主动替你跟进的 AI 生活管家。</p>
          <p>你在对话里说的事，可以变成任务、提醒和记忆。思忆会记住你的偏好与安排，并持续朝私人助理这个方向演进。</p>
          <div class="duo-coming">
            <span class="coming-tag">即将到来</span>
            <p>手机操控，以及你不用打开 App 时更主动的跟进，即将到来。</p>
          </div>
          <details class="duo-more">
            <summary>了解 AiLifeOS</summary>
            <p>思忆是 AiLifeOS App 里的 AI 生活管家。本页介绍产品定位与当前能力，后续能力以实际发布为准。</p>
            <p><a href="https://ailifeos.muyang-bai.chat/" target="_blank" rel="noopener noreferrer">打开 AiLifeOS 宣传页</a></p>
          </details>
        </article>
      </div>
      <p class="duo-shared reveal">你可以分别使用这两款产品。会员与额度请以各产品内的说明为准。</p>
    </section>

    <!-- ═══ 本地新增：价格 ═══ -->
    <section id="pricing" class="section pricing">
      <h2 class="reveal">会员与开通说明</h2>
      <p class="lead reveal">网页不提供付费入口。若要查看或申请会员与额度，请以 AiLifeOS 应用内「会员与额度」页面为准。本页不把两端账号写成已经统一。</p>
      <div class="plans">
        <div v-for="p in PLANS" :key="p.name" class="plan reveal" :class="{ featured: p.hot }">
          <span v-if="p.hot" class="plan-badge">推荐</span>
          <p class="plan-name">{{ p.name }}</p>
          <p class="plan-price">¥<b>{{ p.price }}</b><small v-if="p.days"> / {{ p.days }} 天</small><small v-else> 元</small></p>
          <p v-if="p.note" class="plan-note">{{ p.note }}</p>
        </div>
      </div>
      <p class="lead reveal" style="margin-top: 22px">想开通或升级，请安装并打开 App，在「会员与额度」里提交申请。安装包由运营发放，App 内可检查更新。</p>
    </section>

    <!-- ═══ CTA ═══ -->
    <section class="section cta-band">
      <div class="cta-card reveal">
        <h2 v-if="auth.isLoggedIn">回到控制台，继续订阅</h2>
        <h2 v-else>明天早上，信息喂到嘴边</h2>
        <p v-if="auth.isLoggedIn">管理你的订阅与画像，让简报持续为你工作。</p>
        <p v-else>注册并创建订阅后，简报会按你设定的时间发到邮箱。</p>
        <div class="cta-actions">
          <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-solid btn-lg">进入控制台</button></router-link>
          <template v-else>
            <router-link to="/register"><button class="btn btn-solid btn-lg">免费注册</button></router-link>
            <router-link to="/login"><button class="btn btn-soft btn-lg">已有账号，直接登录</button></router-link>
          </template>
        </div>
      </div>
    </section>

    <!-- ═══ 页脚：合规文本按链接划分 ═══ -->
    <footer class="land-footer">
      <div class="footer-links">
        <router-link to="/privacy">隐私政策</router-link>
        <router-link to="/unsubscribe-help">退订说明</router-link>
        <a :href="ICP_URL" target="_blank" rel="noopener">{{ compliance.icp_record || ICP_RECORD }}</a>
        <button v-if="compliance.disclaimer" class="footer-link-btn" type="button" @click="openPolicy('disclaimer')">免责声明</button>
      </div>
      <p style="margin-top: 10px">一勺热点 SpoonBrief · AI 驱动的热点情报邮件 · 随时退订 · <a href="https://ailifeos.muyang-bai.chat/" target="_blank" rel="noopener noreferrer">思忆 AiLifeOS</a></p>
      <p class="faint" style="margin-top: 6px; font-size: 12px">AI 分析由 DeepSeek 生成 · 简报内容仅供参考，不构成投资建议</p>
    </footer>

    <!-- 合规文本弹窗（结构化 + 链接化展示） -->
    <Modal :show="policyModal !== null" :title="policyTitle" width="680px" @close="policyModal = null">
      <div v-if="policyModal" class="policy-body" v-html="policyHtml"></div>
    </Modal>
  </div>
</template>

<style scoped>
/* ── 导航 ── */
.land-nav {
  background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 60;
}

/* ── Hero ── */
.hero-title { font-size: 46px; line-height: 1.22; font-weight: 800; max-width: 780px; margin: 0 auto 18px; letter-spacing: .01em; }
.hero-title em {
  font-style: normal;
  background: linear-gradient(90deg, #fff, #D0D8FF);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  position: relative;
}
.hero-title em::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: 4px; height: 3px;
  background: rgba(255,255,255,.55); border-radius: 2px;
}
.btn-lg { padding: 13px 26px; font-size: 15px; border-radius: 12px; }
.typing-line { font-size: 14.5px; opacity: .92; margin-top: 24px; font-weight: 600; letter-spacing: .02em; }
.typed { font-weight: 700; }
.typing-caret::after { color: var(--hot); content: "▍"; margin-left: 2px; animation: caret-blink 1s steps(1) infinite; }
@keyframes caret-blink { 50% { opacity: 0; } }
.pc-only { display: inline; }

/* 漂浮新闻卡片（左右分布，加大晃动幅度，负延迟=加载即晃动） */
.float-card {
  position: absolute; z-index: 2; background: rgba(255,255,255,.95); color: var(--text);
  border-radius: 12px; padding: 10px 14px; box-shadow: 0 10px 30px rgba(0,0,0,.16);
  font-size: 13px; font-weight: 700; animation: float-drift 7s ease-in-out infinite;
  display: flex; flex-direction: column; gap: 2px; pointer-events: none;
}
.float-card span { font-size: 11px; color: var(--text-faint); font-weight: 500; }
@keyframes float-drift {
  0%   { transform: translate(0, 0) rotate(0deg); }
  25%  { transform: translate(9px, -32px) rotate(4.5deg); }
  50%  { transform: translate(-7px, -16px) rotate(-3.5deg); }
  75%  { transform: translate(5px, -30px) rotate(2.5deg); }
  100% { transform: translate(0, 0) rotate(0deg); }
}
.fc-1  { left: 3%;  top: 24px;  animation-delay: -0.8s; }
.fc-5  { left: 15%; top: 96px;  animation-delay: -4.3s; animation-duration: 8.8s; }
.fc-10 { left: 4%;  top: 176px; animation-delay: -3.9s; animation-duration: 7.6s; }
.fc-3  { left: 14%; top: 250px; animation-delay: -5.1s; animation-duration: 6.4s; }
.fc-8  { left: 3%;  top: 330px; animation-delay: -5.8s; animation-duration: 8.4s; }
.fc-6  { right: 15%; top: 30px;  animation-delay: -6.2s; animation-duration: 7.2s; }
.fc-2  { right: 3%;  top: 104px; animation-delay: -3.2s; animation-duration: 8s; }
.fc-9  { right: 14%; top: 180px; animation-delay: -0.4s; animation-duration: 9s; }
.fc-4  { right: 3%;  top: 256px; animation-delay: -1.9s; animation-duration: 7.8s; }
.fc-7  { right: 14%; top: 334px; animation-delay: -2.7s; animation-duration: 6.8s; }
/* 安全区：中间标题/按钮/信任标签/滚动条区域不放卡片；窄屏只留外侧一列 */
@media (max-width: 1279px) and (min-width: 961px) { .fc-5, .fc-3, .fc-6, .fc-9, .fc-7 { display: none; } }

/* 卖点信任条 */
.hero-trust {
  margin-top: 26px; display: flex; align-items: center; justify-content: center;
  gap: 12px; flex-wrap: wrap;
}
.trust-item {
  font-size: 13px; font-weight: 700; letter-spacing: .04em;
  background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35);
  padding: 6px 14px; border-radius: 999px;
}
.trust-dot { width: 5px; height: 5px; border-radius: 50%; background: rgba(255,255,255,.6); }

/* 热点词滚动条（5 组等宽，位移一组宽度，任意屏宽下无缝循环） */
.ticker { display: flex; gap: 0; width: max-content; animation: ticker-loop 40s linear infinite; }
.ticker:hover { animation-play-state: paused; }
.ticker-group { display: flex; gap: 12px; padding-right: 12px; }
@keyframes ticker-loop { from { transform: translateX(0); } to { transform: translateX(-20%); } }

/* ── 痛点瀑布 ── */
.pain-grid { display: grid; grid-template-columns: 1fr 40px 1fr; gap: 16px; align-items: stretch; margin-top: 8px; }
.pain-side { display: flex; flex-direction: column; }
.pain-label { font-size: 13px; font-weight: 700; margin-bottom: 10px; text-align: center; padding: 6px 10px; border-radius: 999px; }
.pain-label-bad { background: var(--cmp-bad-soft); color: var(--cmp-bad); }
.pain-label-good { background: var(--cmp-good-soft); color: var(--cmp-good); }
.pain-vs { display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800; color: var(--primary); }
.waterfall {
  flex: 1; overflow: hidden; border-radius: 12px; border: 1px solid var(--cmp-bad-border); background: #fff;
  position: relative; min-height: 300px;
}
.wf-col { position: absolute; inset: 0; animation: wf-fall 26s linear infinite; }
.wf-col p {
  margin: 0 0 10px; padding: 9px 12px; background: var(--cmp-bad-soft); border: 1px solid var(--cmp-bad-border);
  border-radius: 8px; font-size: 12.5px; color: var(--text-muted); line-height: 1.5;
}
@keyframes wf-fall { from { transform: translateY(0); } to { transform: translateY(-50%); } }
.pain-caption { margin-top: 10px; text-align: center; font-size: 13px; color: var(--text-muted); font-weight: 600; }
.brief-mini {
  flex: 1; background: #fff; border-radius: 12px; border: 1px solid var(--cmp-good-border);
  box-shadow: var(--shadow-lg); overflow: hidden; display: flex; flex-direction: column; min-height: 300px;
}
.brief-mini-head { background: var(--gradient); color: #fff; font-weight: 800; font-size: 14px; padding: 12px 16px; }
.brief-mini-body { padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.b-h { font-size: 12px; font-weight: 800; color: var(--primary); margin-top: 6px; letter-spacing: .05em; }
.b-t { font-size: 13.5px; color: var(--text-muted); line-height: 1.65; }

/* ── 演示台 ── */
.demo-section { scroll-margin-top: 70px; }
.demo-wrap { max-width: 860px; margin: 0 auto; }
.demo-steps {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  max-width: 560px; margin: 0 auto 18px;
}
.dstep {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-size: 12.5px; font-weight: 600; color: var(--text-faint);
  padding: 7px 4px; border-radius: 10px; border: 1px solid var(--border); background: #fff;
  transition: all .3s ease;
}
.dstep-dot {
  width: 18px; height: 18px; border-radius: 50%; background: #f3f4f6; color: var(--text-faint);
  font-size: 11px; font-weight: 800; display: inline-flex; align-items: center; justify-content: center;
  transition: all .3s ease;
}
.dstep.on { color: var(--primary); border-color: #D0D8FF; background: var(--primary-light); }
.dstep.on .dstep-dot { background: var(--gradient); color: #fff; }
.dstep.active { box-shadow: 0 0 0 3px rgba(91, 124, 255, .18); transform: translateY(-2px); }
.demo-picker { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 18px; }
.tag-chip {
  border: 1.5px solid var(--border); background: #fff; color: var(--text-muted);
  padding: 8px 16px; border-radius: 999px; font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all .18s ease;
}
.tag-chip:hover { border-color: var(--primary); color: var(--primary); transform: translateY(-2px); }
.tag-chip.active { background: var(--gradient); border-color: transparent; color: #fff; box-shadow: 0 4px 14px rgba(91, 124, 255, .35); }

.demo-stage {
  position: relative; min-height: 340px; border-radius: 16px; border: 1px solid var(--border);
  background:
    radial-gradient(circle at 50% 0%, rgba(91, 124, 255, .06), transparent 55%),
    #fff;
  overflow: hidden; box-shadow: var(--shadow);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}

/* 红绿灯窗框：让演示舞台像一扇真实的 App 窗口（仅去重边框，不改原布局） */
.demo-window { width: 100%; }
.demo-window :deep(.demo-stage) {
  border: 0; border-radius: 0; box-shadow: none; min-height: 320px; padding: 22px;
}

/* 待机 */
.stage-idle { text-align: center; color: var(--text-faint); }
.idle-spoon {
  width: 54px; height: 54px; margin: 0 auto 14px; border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, #fff 0 22%, transparent 23%),
              conic-gradient(from 0deg, #5B7CFF, #8AA0FF, #4D6BFE, #5B7CFF);
  animation: spin 6s linear infinite;
}
.stage-idle p { font-size: 14px; }

/* 收集：新闻飞入 */
.stage-collect { position: absolute; inset: 0; }
.fly-chip {
  position: absolute; left: 50%; top: 50%; font-size: 12px; font-weight: 600;
  padding: 7px 12px; background: #fff; border: 1px solid #D0D8FF; border-radius: 999px;
  color: var(--text); box-shadow: var(--shadow);
  animation: fly-in 1.4s cubic-bezier(.2,.7,.3,1) forwards;
}
@keyframes fly-in {
  from {
    transform: translate(calc(-50% + (var(--i, 0) - 4) * 130px), calc(-50% + ((var(--i, 0) % 3) - 1) * 110px)) scale(.4);
    opacity: 0;
  }
  70% { opacity: 1; }
  to { transform: translate(-50%, -50%) scale(1); opacity: 1; }
}

/* 分析核心（光圈与光球同心） */
.stage-analyze { position: relative; text-align: center; }
.core-wrap { position: relative; width: 84px; height: 84px; margin: 0 auto; }
.core-ball {
  position: absolute; inset: 0; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #C9D4FF, #5B7CFF 55%, #405FEA);
  box-shadow: 0 0 42px rgba(91, 124, 255, .55), inset 0 0 22px rgba(255,255,255,.35);
  animation: core-throb 1.1s ease-in-out infinite;
}
@keyframes core-throb { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }
.core-ring {
  position: absolute; left: 50%; top: 50%; width: 84px; height: 84px;
  margin: -42px 0 0 -42px; border-radius: 50%;
  border: 2px solid rgba(91, 124, 255, .45); pointer-events: none;
}
.ring-a { animation: ring-out 2.2s ease-out infinite; }
.ring-b { animation: ring-out 2.2s ease-out 1.1s infinite; }
@keyframes ring-out {
  from { transform: scale(1); opacity: .8; }
  to { transform: scale(2.6); opacity: 0; }
}
.status-line { margin-top: 26px; font-size: 14px; font-weight: 600; color: var(--text-muted); animation: status-fade .3s ease; }
@keyframes status-fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

/* 送达 */
.stage-deliver { position: relative; width: 100%; display: flex; align-items: center; justify-content: center; }
.env { animation: env-fly 1.1s cubic-bezier(.3,.7,.4,1) forwards; }
.mailbox {
  position: absolute; right: 12%; width: 84px; height: 64px; border-radius: 10px 10px 0 0;
  background: linear-gradient(180deg, #8AA0FF, #5B7CFF); border: 2.5px solid #4D6BFE;
}
.mailbox::before { content: ""; position: absolute; inset: 0 0 -14px 0; border-radius: 0 0 10px 10px; background: #F0F3FF; border: 2.5px solid #4D6BFE; border-top: none; }
.mailbox::after { content: ""; position: absolute; left: 8px; right: 8px; top: -12px; height: 12px; background: #F0F3FF; border: 2.5px solid #4D6BFE; border-bottom: none; border-radius: 6px 6px 0 0; }
.mb-flag { position: absolute; right: -30px; top: 0; width: 30px; height: 14px; background: var(--primary-active); border-radius: 0 4px 4px 0; transform-origin: left center; animation: flag-up .5s .5s ease forwards; opacity: 0; }
.mb-clock {
  position: absolute; top: -38px; left: 50%; transform: translateX(-50%);
  background: #fff; border: 1.5px solid #4D6BFE; color: #4D6BFE;
  font-size: 11px; font-weight: 800; padding: 2px 10px; border-radius: 999px; white-space: nowrap;
  animation: status-fade .4s ease .9s both;
}
@keyframes flag-up { from { opacity: 0; transform: rotate(-70deg); } to { opacity: 1; transform: rotate(0); } }
@keyframes env-fly {
  0% { transform: translate(0, 0) scale(1) rotate(0); opacity: 0; }
  15% { opacity: 1; }
  60% { transform: translate(160px, -34px) scale(.86) rotate(8deg); }
  100% { transform: translate(320px, -10px) scale(.3) rotate(4deg); opacity: 0; }
}

/* 完成：简报 */
.stage-brief { width: 100%; text-align: left; animation: fade-up .55s ease; }
.brief-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.brief-stamp {
  border: 2px solid var(--primary); color: var(--primary); font-weight: 800; font-size: 13px;
  padding: 3px 12px; border-radius: 8px; letter-spacing: .1em; transform: rotate(-6deg);
  animation: stamp-in .4s cubic-bezier(.2,2,.4,1) .1s both;
}
@keyframes stamp-in { from { transform: rotate(-6deg) scale(2.4); opacity: 0; } to { transform: rotate(-6deg) scale(1); opacity: 1; } }
.brief-sub { font-size: 13px; color: var(--text-muted); font-weight: 600; }
.brief-h { font-size: 13px; font-weight: 800; color: var(--primary); margin: 12px 0 6px; letter-spacing: .04em; }
.brief-p { font-size: 14px; color: var(--text); line-height: 1.8; }
.trace-item {
  border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
  cursor: pointer; transition: border-color .18s, box-shadow .18s; background: #fff;
}
.trace-item:hover { border-color: #D0D8FF; box-shadow: 0 4px 14px rgba(91, 124, 255, .12); }
.trace-item.open { border-color: var(--primary); }
.trace-t { font-size: 13.5px; font-weight: 700; color: var(--text); line-height: 1.5; }
.trace-meta { font-size: 12px; color: var(--text-faint); margin-top: 3px; }
.trace-detail { overflow: hidden; animation: trace-open .3s ease; }
.trace-line { height: 2px; background: linear-gradient(90deg, var(--primary), #D0D8FF); margin: 10px 0 8px; transform-origin: left; animation: line-draw .45s ease both; }
@keyframes line-draw { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes trace-open { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.trace-src { font-size: 13px; font-weight: 700; color: var(--primary); }
.trace-note { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; line-height: 1.6; }
.brief-actions { display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.brief-btns { display: flex; gap: 10px; flex-wrap: wrap; margin-left: auto; }
.subscribed-chip {
  font-size: 12.5px; font-weight: 700; color: var(--cmp-good);
  background: var(--cmp-good-soft); border: 1px solid var(--cmp-good-border); padding: 5px 12px; border-radius: 999px;
  animation: status-fade .4s ease both;
}

/* ── 溯源卖点区：证据链 ── */
.proof-card { max-width: 620px; margin: 0 auto; }
.proof-conclusion {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  background: var(--primary-light); border: 1.5px solid #D0D8FF; border-radius: 14px;
  padding: 16px 18px; cursor: pointer; transition: all .2s ease;
}
.proof-conclusion:hover { border-color: var(--primary); box-shadow: 0 8px 22px rgba(91, 124, 255, .14); }
.proof-tag {
  font-size: 11px; font-weight: 800; letter-spacing: .08em; color: #fff;
  background: var(--gradient); padding: 3px 10px; border-radius: 999px; white-space: nowrap;
}
.proof-conclusion p { flex: 1; min-width: 220px; font-size: 15px; font-weight: 700; color: var(--text); line-height: 1.7; }
.proof-hint { font-size: 12.5px; font-weight: 700; color: var(--primary); white-space: nowrap; }
.proof-chain { padding: 6px 4px 0; animation: trace-open .35s ease; }
.proof-line {
  height: 2px; background: linear-gradient(90deg, var(--primary), #D0D8FF);
  margin: 10px 0 12px; transform-origin: left; animation: line-draw .5s ease both;
}
.proof-evid {
  border-left: 3px solid #D0D8FF; background: #fff; border-radius: 0 10px 10px 0;
  padding: 10px 14px; margin-bottom: 10px; box-shadow: var(--shadow);
}
.pe-title { font-size: 13.5px; font-weight: 700; color: var(--text); }
.pe-meta { font-size: 12px; color: var(--text-muted); margin-top: 3px; }
.proof-note { font-size: 13px; color: var(--text-muted); line-height: 1.8; margin-top: 4px; }

/* ── 时间轴 ── */
.timeline {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 30px; position: relative;
}
.timeline::before {
  content: ""; position: absolute; top: 9px; left: 12.5%; right: 12.5%; height: 2px;
  background: linear-gradient(90deg, #D0D8FF, var(--primary));
  transform: scaleX(0); transform-origin: left;
}
.timeline.visible::before { animation: line-grow 1.2s ease .3s forwards; }
@keyframes line-grow { to { transform: scaleX(1); } }
.tl-node { text-align: center; position: relative; }
.tl-dot {
  width: 20px; height: 20px; margin: 0 auto 10px; border-radius: 50%;
  background: var(--gradient); border: 4px solid #fff; box-shadow: 0 0 0 2px #D0D8FF;
  opacity: 0; transform: scale(.4);
}
.timeline.visible .tl-dot { animation: dot-pop .5s ease calc(.2s + var(--d) * .35s) forwards; }
@keyframes dot-pop { to { opacity: 1; transform: scale(1); } }
.tl-time { font-size: 20px; font-weight: 800; background: var(--gradient); -webkit-background-clip: text; background-clip: text; color: transparent; }
.tl-text { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; line-height: 1.6; }

/* ── 特性卡 ── */
.feature { position: relative; padding: 24px 22px 22px; overflow: hidden; }
.feature-bar {
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--gradient); border-radius: 0 4px 4px 0;
}
.feature h4 { font-size: 15.5px; margin-bottom: 8px; }
.feature p { color: var(--text-muted); font-size: 13.5px; line-height: 1.7; }

/* ── 数据带 ── */
.stats-band {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px;
  background: linear-gradient(135deg, #F0F3FF, #F7F9FF); border-radius: 16px; border: 1px solid #D0D8FF;
  padding: 36px 20px; max-width: 980px;
}
.stat { text-align: center; }
.stat-fact { font-size: 18px; line-height: 1.6; font-weight: 700; color: var(--primary); }
.stat-label { color: var(--text-muted); font-size: 13px; margin-top: 4px; }

/* ── CTA ── */
.cta-card {
  background: var(--gradient); border-radius: 20px; color: #fff; text-align: center;
  padding: 48px 24px; box-shadow: var(--shadow-lg);
}
.cta-card h2 { font-size: 28px; margin-bottom: 8px; }
.cta-card p { opacity: .94; margin-bottom: 24px; }
.cta-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

/* ── 页脚（合规文本按链接划分） ── */
.land-footer {
  border-top: 1px solid var(--border); background: #fff; padding: 32px 20px;
  text-align: center; color: var(--text-faint); font-size: 13px;
}
.footer-links { display: flex; justify-content: center; align-items: center; gap: 16px; flex-wrap: wrap; }
.footer-links a { color: var(--text-faint); transition: color .15s; }
.footer-links a:hover { color: var(--primary); }
.footer-link-btn {
  border: none; background: none; cursor: pointer; font-family: inherit;
  font-size: 13px; color: var(--text-faint); padding: 0; transition: color .15s;
}
.footer-link-btn:hover { color: var(--primary); }
.policy-body {
  white-space: pre-wrap; line-height: 1.9; font-size: 14px; color: var(--text);
  max-height: 60vh; overflow-y: auto; padding-right: 4px;
}
.policy-body a { color: var(--primary); text-decoration: underline; word-break: break-all; }

/* ── 移动端 ── */
@media (max-width: 960px) {
  .lp-hero { padding-top: 92px; padding-bottom: 84px; }
  .float-card { padding: 6px 10px; font-size: 11.5px; border-radius: 10px; animation-name: float-drift-sm; }
  .float-card span { display: none; }
  .fc-5, .fc-6, .fc-7, .fc-8, .fc-9, .fc-10 { display: none; }
  .fc-1 { left: 4%; top: 18px; bottom: auto; right: auto; }
  .fc-2 { right: 4%; top: 30px; bottom: auto; left: auto; }
  .fc-3 { left: 6%; bottom: 18px; top: auto; right: auto; }
  .fc-4 { right: 5%; bottom: 30px; top: auto; left: auto; }
  .plans { grid-template-columns: repeat(2, 1fr); }
}
@keyframes float-drift-sm {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(4px, -8px) rotate(3deg); }
  66% { transform: translate(-3px, -4px) rotate(-2.5deg); }
}
@media (max-width: 860px) {
  .hero-title { font-size: 30px; }
  .pc-only { display: none; }
  .demo-steps { grid-template-columns: repeat(2, 1fr); }
  .pain-grid { grid-template-columns: 1fr; }
  .pain-vs { transform: rotate(90deg); }
  .timeline { grid-template-columns: 1fr; gap: 22px; }
  .timeline::before {
    top: 12%; bottom: 12%; left: 9px; right: auto; width: 2px; height: auto;
    transform: scaleY(0); transform-origin: top;
  }
  .timeline.visible::before { animation: line-grow-y 1.2s ease .3s forwards; }
  @keyframes line-grow-y { to { transform: scaleY(1); } }
  .tl-node { display: grid; grid-template-columns: 20px 92px minmax(0, 1fr); align-items: center; gap: 10px; text-align: left; }
  .tl-dot { margin: 0; }
  .tl-text { margin-top: 0; }
  .mailbox { right: 4%; }
  .brief-btns { margin-left: 0; }
}

/* ══ 本地新增 / 重配色 ══ */
.nav-anchor { color: var(--text-muted); font-size: 14px; font-weight: 600; padding: 0 6px; }
.nav-anchor:hover { color: var(--primary); }
.hot-chip::before { background: rgba(255,255,255,.85); }
.lp-hero { background: var(--gradient); }
.lp-hero::after {
  content: ""; position: absolute; top: -140px; right: -120px; width: 520px; height: 520px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,.28), rgba(255,255,255,0) 65%); pointer-events: none;
}
.btn-hero { background: #fff; color: var(--primary-active); border: 1px solid #fff; font-weight: 700; box-shadow: 0 8px 22px rgba(32, 48, 140, .22); }
.btn-hero:hover:not(:disabled) { background: var(--primary-light); color: var(--primary-active); }
.hot-tag {
  font-style: normal; font-size: 10px; font-weight: 800; color: #fff; background: var(--hot);
  border-radius: 4px; padding: 0 4px; margin-right: 5px; vertical-align: 1px;
}
.hero .float-card p::before { content: none; display: none; }
.float-card span::before { content: ""; display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--hot); margin-right: 5px; vertical-align: 1px; }
.id-picker { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; align-items: center; margin-bottom: 12px; }
.id-label { font-size: 13px; font-weight: 700; color: var(--text-faint); margin-right: 4px; }
.id-chip {
  border: 1.5px solid var(--border); background: #fff; color: var(--text); padding: 7px 14px;
  border-radius: 12px; font-size: 13.5px; font-weight: 600; cursor: pointer; transition: all .18s ease; font-family: inherit;
}
.id-chip:hover { border-color: var(--primary-border); transform: translateY(-2px); }
.id-chip.active { border-color: var(--primary); background: var(--primary-light); color: var(--primary-active); }
.duo-section { scroll-margin-top: 80px; }
.duo-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.duo-card { background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 28px; box-shadow: var(--shadow); text-align: left; }
.duo-card h3 { font-size: 22px; color: var(--text); margin: 12px 0; }
.duo-card p { font-size: 15px; line-height: 1.9; color: var(--text-muted); }
.duo-label { display: inline-block; border-radius: 999px; background: var(--primary-light); color: var(--primary-active); padding: 4px 12px; font-size: 12px; font-weight: 600; }
.duo-app { border-color: #D0D8FF; }
.duo-app h3, .duo-app .duo-position { color: #4D6BFE; }
.duo-app .duo-position { font-weight: 600; margin-bottom: 10px; }
.duo-coming { margin-top: 20px; padding: 16px; border-radius: 12px; background: #F5F7FF; border: 1px solid #E7EBF1; }
.coming-tag { display: inline-block; font-size: 12px; font-weight: 600; color: #4D6BFE; border: 1px solid #D0D8FF; border-radius: 999px; padding: 2px 10px; margin-bottom: 6px; }
.duo-more { margin-top: 18px; }
.duo-more summary { cursor: pointer; color: #4D6BFE; font-weight: 600; padding: 10px 0; min-height: 44px; }
.duo-more summary:focus-visible { outline: 3px solid #D0D8FF; outline-offset: 4px; border-radius: 10px; }
.duo-shared { text-align: center; color: var(--text-muted); font-size: 14px; line-height: 1.8; margin-top: 22px; }
@media (max-width: 860px) {
  .duo-grid { grid-template-columns: 1fr; }
  .duo-card { padding: 22px; }
  .nav-links { gap: 6px; }
  .nav-anchor { padding: 0 2px; font-size: 13px; }
}
.pricing { scroll-margin-top: 70px; }
.plans { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.plan { position: relative; background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 20px 18px; box-shadow: var(--shadow); }
.plan.featured { border: 1.5px solid var(--primary); box-shadow: var(--shadow-lg); }
.plan-badge { position: absolute; top: -10px; right: 14px; background: var(--gradient); color: #fff; font-size: 11px; font-weight: 800; padding: 2px 10px; border-radius: 999px; }
.plan-name { font-size: 13px; font-weight: 800; color: var(--primary); letter-spacing: .04em; }
.plan-price { margin: 8px 0 4px; color: var(--text); font-size: 16px; }
.plan-price b { font-size: 32px; font-weight: 800; }
.plan-price small { color: var(--text-faint); font-size: 12px; }
.plan-note { font-size: 12.5px; color: var(--text-muted); margin-bottom: 10px; }
.plan ul { margin: 0; padding-left: 18px; font-size: 13px; color: var(--text-muted); line-height: 1.9; }
h2 { text-wrap: balance; }
@media (max-width: 560px) {
  .hero-title { font-size: 28px; }
  .section { padding: 44px 16px; }
  .section h2, .cta-card h2 { font-size: 22px; }
  .stats-band { grid-template-columns: repeat(2, 1fr); margin: 0 16px; padding: 24px 12px; gap: 18px 8px; }
  .stat-fact { font-size: 16px; }
  .plans { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .plan:first-child { grid-column: 1 / -1; }
  .plan { padding: 16px 14px; }
  .plan-price b { font-size: 26px; }
  .cta-card { padding: 36px 18px; }
}
@media (prefers-reduced-motion: reduce) {
  .lp-root *, .lp-root *::before, .lp-root *::after { animation-play-state: paused !important; }
  .lp-root .reveal { opacity: 1 !important; transform: none !important; }
}

/* ══ 浅色 Hero / CTA 方案 ══ */
.lp-hero { background: linear-gradient(180deg, #FFFFFF 0%, #F5F7FF 100%) !important; color: var(--text) !important; }
.lp-hero::after { background: radial-gradient(circle, rgba(91,124,255,.14), rgba(91,124,255,0) 65%); }
.lp-hero::before {
  content: ""; position: absolute; left: 50%; top: 40px; width: 760px; height: 420px; transform: translateX(-50%);
  background: radial-gradient(ellipse at center, rgba(91,124,255,.10), rgba(91,124,255,0) 70%); pointer-events: none;
}
.lp-hero .hero-orb { opacity: .25; }
.hero-title { color: #1A1F36; }
.hero-title em { background: none; -webkit-background-clip: border-box; background-clip: border-box; color: #5B7CFF; }
.hero-title em::after { background: rgba(91,124,255,.28); }
.lp-hero p, .typing-line { color: #4A5170; }
.typed { color: #5B7CFF; }
.btn-solid { background: #5B7CFF; color: #fff; border: 1px solid #5B7CFF; font-weight: 700; border-radius: 12px; box-shadow: 0 8px 20px rgba(91,124,255,.28); }
.btn-solid:hover:not(:disabled) { background: #4D6BFE; border-color: #4D6BFE; color: #fff; }
.btn-soft { background: #fff; color: #3E5BE0; border: 1.5px solid #C9D4FF; font-weight: 700; border-radius: 12px; }
.btn-soft:hover:not(:disabled) { background: #F0F3FF; border-color: #5B7CFF; color: #3E5BE0; }
.btn-lg { border-radius: 12px; }
.trust-item { background: #fff; border: 1px solid #D6DEFF; color: #3E4A7A; border-radius: 999px; }
.trust-dot { background: #B7C4FF; }
.lp-hero .hot-chip { background: #fff; color: #3E4A7A; border: 1px solid #DCE3FF; border-radius: 999px; box-shadow: 0 2px 6px rgba(91,124,255,.06); }
.lp-hero .hot-chip:hover { background: #F0F3FF; border-color: #5B7CFF; }
.hot-chip::before { background: var(--hot); }
.float-card { background: #fff; border: 1px solid #EEF1FA; border-radius: 14px; box-shadow: 0 8px 24px rgba(30,40,90,.08); }
.cta-card { background: linear-gradient(180deg, #FFFFFF 0%, #F5F7FF 100%); border: 1px solid #DCE3FF; color: var(--text); border-radius: 16px; box-shadow: 0 10px 30px rgba(91,124,255,.08); }
.cta-card h2 { color: #1A1F36; }
.cta-card p { color: #4A5170; opacity: 1; }
/* 圆角统一：卡片 12-16，按钮 10-12，标签胶囊 */
.plan, .stats-band, .demo-stage, .feat-card, .pain-col, .brief-mini { border-radius: 14px; }
.id-chip, .tag-chip, .trace-tag, .plan-badge { border-radius: 999px; }
.lp-root .btn { border-radius: 12px; }
.lp-root .btn-sm { border-radius: 10px; }

/* t126: align public landing with the approved persona page, keep all sections. */
.lp-root { font-family:var(--font); }
.lp-hero { background:radial-gradient(1200px 420px at 50% -80px,#CBD6FF,transparent 70%),linear-gradient(180deg,#EDF1FF,#FCFCFD 100%) !important; }
.btn-solid,.btn-solid:hover:not(:disabled) { background:#16A34A;border-color:#16A34A;box-shadow:0 4px 12px rgba(22,163,74,.15); }
.btn-solid:hover:not(:disabled) { background:#15803D;border-color:#15803D; }
.btn-solid:active:not(:disabled) { background:#166534;border-color:#166534; }
.hero-title em,.typed { color:#4D6BFE; }
.plan,.stats-band,.demo-stage,.feat-card,.pain-col,.brief-mini,.float-card,.cta-card { border-radius:16px;box-shadow:var(--shadow); }
</style>
