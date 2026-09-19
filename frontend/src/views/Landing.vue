<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import Modal from '../components/Modal.vue'

const compliance = ref({ icp_record: '', privacy_policy: '', disclaimer: '' })

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

/* ── 数字 count-up ── */
let statObserver = null
function setupCountUp() {
  const els = document.querySelectorAll('[data-count]')
  if (!els.length) return
  statObserver = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return
      const el = e.target
      statObserver.unobserve(el)
      const target = Number(el.dataset.count)
      const dur = 1400
      const t0 = performance.now()
      function step(now) {
        const p = Math.min((now - t0) / dur, 1)
        const eased = 1 - Math.pow(1 - p, 3)
        el.textContent = Math.round(target * eased)
        if (p < 1) requestAnimationFrame(step)
      }
      requestAnimationFrame(step)
    })
  }, { threshold: 0.4 })
  els.forEach((el) => statObserver.observe(el))
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
    insight: '国产算力进入"硬研发补课"期：燧原科技 IPO 募资 61.19 亿，研发人员占比 76.73%。机会点——绑定你的专业背景做垂直场景工具，大厂看不上、外行进不来的窗口期约 12 个月。',
    news: [
      { t: '燧原科技科创板 IPO 发行结果落定，募资 61.19 亿元', src: 'IT之家', cred: 8, cross: 3 },
      { t: '国产刻蚀机良率突破，多家设备厂上调全年指引', src: '财新网', cred: 9, cross: 3 },
    ],
  },
  'AI 大模型': {
    insight: '行业从"无 AI 不产品"切换到"AI 必须证明自己不是拐杖"：OECD 数据显示，每天用 AI 的学生成绩反低 28 分；无 AI 功能的 LibreOffice 反而创下载纪录。风险点——避免做通用型 AI 工具。',
    news: [
      { t: 'OECD 报告：不常用 AI 的学生，测试得分高出 28 分', src: 'IT之家', cred: 8, cross: 2 },
      { t: 'LibreOffice 无 AI 版本首周下载量破 103 万', src: '开源中国', cred: 7, cross: 2 },
    ],
  },
  '新能源车': {
    insight: '价格战进入下半场，出海成为唯一增量：多家车企把欧洲与中东列为战略市场。机会点——关注"电池回收 + 换电标准"这个被低估的细分赛道。',
    news: [
      { t: '头部车企集体上调海外销量目标，中东成新战场', src: '财新网', cred: 8, cross: 3 },
      { t: '动力电池回收新国标落地，千亿市场启动', src: '中新网', cred: 9, cross: 2 },
    ],
  },
  '黄金': {
    insight: '避险需求与央行购金共振，金价高位震荡加大。对策——定投而非追高，把黄金定位为组合的"保险仓"，配置比例控制在 5%-10%。',
    news: [
      { t: '全球央行连续 12 个月净购金，创历史同期纪录', src: '财新网', cred: 9, cross: 3 },
      { t: '美联储降息预期升温，黄金避险属性再获定价', src: '雪球热帖', cred: 6, cross: 2 },
    ],
  },
  '考研政策': {
    insight: '集成电路、人工智能方向扩招信号明确，多所高校新增示范性微电子学院。行动点——本周内核对目标院校简章，把"扩招但竞争更卷"写进你的择校模型。',
    news: [
      { t: '教育部：扩大集成电路等关键领域专业硕士招生', src: '中新网', cred: 10, cross: 3 },
      { t: '4 所高校获批新增示范性微电子学院', src: '极客公园', cred: 8, cross: 2 },
    ],
  },
  '人形机器人': {
    insight: '量产元年临近，降本速度超预期：核心零部件国产化率快速爬升。机会点——关注"灵巧手 + 传感器"供应链，避开整机概念炒作。',
    news: [
      { t: '多家厂商公布人形机器人量产时间表，单价跌破 20 万', src: 'IT之家', cred: 7, cross: 3 },
      { t: '灵巧手核心零部件国产化率一年翻倍', src: '量子位', cred: 7, cross: 2 },
    ],
  },
  '低空经济': {
    insight: '政策密集落地，eVTOL 适航审定提速，但空域管理与基建仍是瓶颈。机会点——先盯"起降场 + 空管系统"这类卖铲子的环节。',
    news: [
      { t: '多省市发布低空经济三年行动方案', src: '中新网', cred: 9, cross: 3 },
      { t: '首张 eVTOL 生产许可证颁发，商业化进入倒计时', src: 'IT之家', cred: 8, cross: 2 },
    ],
  },
  '美联储': {
    insight: '降息路径与缩表节奏的博弈主导全球资产定价。对策——降低单一货币敞口，权益仓位分批而非一次性押注。',
    news: [
      { t: '美联储官员密集发声，市场重估 9 月降息幅度', src: '财新网', cred: 9, cross: 3 },
      { t: '美债收益率曲线陡峭化，资金再配置启动', src: '雪球热帖', cred: 6, cross: 2 },
    ],
  },
  '算力': {
    insight: '国产算力资本化加速：一级市场估值抬升，二级市场开始"按业绩说话"。机会点——跟踪"AI 算力 + 电力平衡"交叉方向的 ETF 与标的。',
    news: [
      { t: '国产 AI 芯片四款新品同期流片，性能对标国际旗舰', src: 'IT之家', cred: 7, cross: 3 },
      { t: '智算中心电力缺口凸显，"算电协同"写入多地规划', src: '财新网', cred: 9, cross: 2 },
    ],
  },
  '出海': {
    insight: '从产品出海升级为组织出海：本地化合规与品牌溢价成为分水岭。风险点——地缘政策反复，单一市场集中度不宜过高。',
    news: [
      { t: '跨境电商新政出台，海外仓建设获真金白银补贴', src: '中新网', cred: 9, cross: 3 },
      { t: '国产 AI 应用横扫东南亚应用商店榜单', src: '36氪快讯', cred: 7, cross: 2 },
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

const timelineNodes = [
  { time: '23:00', text: '你入睡，订阅任务进入待命' },
  { time: '06:00', text: 'AI 全局分析师开始工作' },
  { time: '07:30', text: '分析完成，多源交叉验证通过' },
  { time: '08:00', text: '简报躺在你的邮箱，等你醒来' },
]

const features = [
  { title: '全局分析', text: '结合你的身份与兴趣，把热点翻译成机会、风险与行动建议，而不是再甩给你一堆链接' },
  { title: '溯源可信', text: '每条结论都指向原始新闻，多源交叉验证后才采信——AI 说错了，你能立刻查到出处' },
  { title: '定时送达', text: '北京时间自由设定，每天 / 每周 / 每月准时投递，支持多个收件邮箱，从不错过' },
  { title: '你的视角', text: '学生、投资者、创业者…多重身份交叉解读，同样一条新闻，得到专属于你的结论' },
]

const FLY_HEADLINES = ['芯片出口管制再升级，产业链加速重构', 'A 股午后放量拉升，两市成交破万亿', '大模型价格战：推理成本一年降 92%', '黄金续创历史新高，央行连续增持', '低空经济首张牌照落地', '考研国家线公布，AI 专业扩招 30%', '人形机器人量产时间表密集发布', '新能源车渗透率首次突破 60%', '美联储释放降息信号，人民币走强', '开源社区爆发：提示词成新生产力']

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
    ? `你同时关注「${tags.join('、')}」——AI 全局分析师把它们放进同一张图交叉解读。` + primary.insight
    : primary.insight

  phase.value = 'collect'
  await sleep(1400)
  phase.value = 'analyze'
  const lines = [
    `正在读取你的兴趣画像：${tags.join('、')}…`,
    '正在扫描 14 个信源 · 700+ 条热点…',
    '多源交叉验证，剔除重复与谣言…',
    '正在生成全局分析与行动建议…',
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
  tickTyping()
  setupReveal()
  setupCountUp()
  try {
    compliance.value = await api('/public/icp')
  } catch { /* 忽略 */ }
})

onBeforeUnmount(() => {
  clearTimeout(typeTimer)
  if (observer) observer.disconnect()
  if (statObserver) statObserver.disconnect()
})
</script>

<template>
  <div>
    <!-- ═══ 顶部导航 ═══ -->
    <header class="land-nav">
      <div class="navbar">
        <router-link to="/" class="brand">
          <img src="/favicon.svg" alt="一勺热点" />
          一勺热点
        </router-link>
        <nav class="nav-links">
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
    <section class="hero">
      <div class="hero-orb" style="width: 260px; height: 260px; top: -60px; left: -60px"></div>
      <div class="hero-orb" style="width: 150px; height: 150px; top: 46px; right: 8%; animation-delay: 1.4s"></div>
      <div class="hero-orb" style="width: 90px; height: 90px; bottom: 26px; left: 12%; animation-delay: 2.6s"></div>

      <!-- 漂浮新闻卡片（左右分布，从加载起持续晃动） -->
      <div class="float-card fc-1"><p>芯片 · 上游涨价</p><span>09:02</span></div>
      <div class="float-card fc-2"><p>金价再创新高</p><span>08:47</span></div>
      <div class="float-card fc-3"><p>AI 专业扩招</p><span>07:58</span></div>
      <div class="float-card fc-4"><p>低空经济 · 首张牌照</p><span>09:21</span></div>
      <div class="float-card fc-5"><p>考研 · 国家线公布</p><span>08:12</span></div>
      <div class="float-card fc-6"><p>出海 · 新政落地</p><span>07:44</span></div>
      <div class="float-card fc-7"><p>机器人 · 量产降价</p><span>09:30</span></div>
      <div class="float-card fc-8"><p>黄金 · 央行增持</p><span>08:55</span></div>
      <div class="float-card fc-9"><p>大模型 · 推理降价</p><span>08:26</span></div>
      <div class="float-card fc-10"><p>算力 · 需求爆发</p><span>07:35</span></div>

      <h1 class="hero-title">全网热点，AI 分析后<br /><em>喂到你嘴边</em></h1>
      <p class="sub">AI 全局分析师读懂你的身份与兴趣，把每天的热点提炼成<br class="pc-only" />机会、风险与行动建议，定时送到你的邮箱——不用刷，张嘴就行。</p>

      <div class="hero-actions">
        <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-primary btn-lg">进入控制台，管理你的订阅</button></router-link>
        <router-link v-else to="/register"><button class="btn btn-primary btn-lg">免费注册，明早 8 点收到第一封</button></router-link>
        <button class="btn btn-ghost btn-lg" @click="useHotWord('AI 大模型')">先体验：亲手生成一份简报</button>
      </div>

      <!-- 卖点信任条 -->
      <div class="hero-trust">
        <span class="trust-item">每条结论可溯源</span>
        <span class="trust-dot"></span>
        <span class="trust-item">多源交叉验证</span>
        <span class="trust-dot"></span>
        <span class="trust-item">定时送到嘴边</span>
      </div>

      <p class="typing-line">今天 AI 正在关注：<span class="typed">{{ typedText }}</span><span class="typing-caret"></span></p>

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
      <h2 class="reveal">每天 700+ 条热点，90% 与你无关</h2>
      <p class="lead reveal">刷不完的信息流，才是你真正的时间黑洞</p>
      <div class="pain-grid">
        <div class="pain-side reveal">
          <p class="pain-label pain-label-bad">没有 一勺热点 的早晨</p>
          <div class="waterfall">
            <div class="wf-col">
              <p v-for="(t, i) in FLY_HEADLINES.slice(0, 10)" :key="'a' + i">{{ t }}</p>
              <p v-for="(t, i) in FLY_HEADLINES.slice(0, 10)" :key="'a2' + i">{{ t }}</p>
            </div>
          </div>
          <p class="pain-caption">刷了 40 分钟，记住的只有焦虑</p>
        </div>
        <div class="pain-vs reveal">→</div>
        <div class="pain-side reveal">
          <p class="pain-label pain-label-good">有了 一勺热点 的早晨</p>
          <div class="brief-mini">
            <div class="brief-mini-head">一勺热点 · 今日简报</div>
            <div class="brief-mini-body">
              <p class="b-h">你的机会</p>
              <p class="b-t">国产算力扩产，结合你的专业背景，窗口期约 12 个月</p>
              <p class="b-h">你的风险</p>
              <p class="b-t">AI 依赖正在腐蚀判断力，本周先停用一次代写</p>
              <p class="b-h">溯源</p>
              <p class="b-t">财新网 · 可信度 9/10 · 3 源交叉验证</p>
            </div>
          </div>
          <p class="pain-caption">读 3 分钟，直接进入决策</p>
        </div>
      </div>
    </section>

    <!-- ═══ 交互演示台 ═══ -->
    <section id="demo-stage" class="section demo-section">
      <h2 class="reveal">别听我讲，亲手生成一份</h2>
      <p class="lead reveal">选 1-3 个你关心的方向，点生成——10 秒看完 AI 全局分析师的一整天</p>

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
            {{ ['collect','analyze','deliver'].includes(phase) ? '生成中…' : '生成我的简报' }}
          </button>
        </div>

        <!-- 舞台（外层类用 phase-* 命名空间，避免与内部 stage-* 内容类冲突） -->
        <div class="demo-stage" :class="'phase-' + phase">
          <!-- 待机 -->
          <div v-if="phase === 'idle' || phase === 'ready'" class="stage-idle">
            <div class="idle-spoon"></div>
            <p v-if="phase === 'ready'">方向已选好：{{ selectedTags.join('、') }}，点上方「生成我的简报」开始</p>
            <p v-else>选择方向，体验「信息喂到嘴边」的全过程</p>
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
              <rect x="1" y="1" width="62" height="42" rx="6" fill="#fff" stroke="#f97316" stroke-width="2.5" />
              <path d="M2 4 L32 26 L62 4" fill="none" stroke="#f97316" stroke-width="2.5" stroke-linecap="round" />
            </svg>
            <div class="mailbox">
              <div class="mb-flag"></div>
              <div class="mb-clock">08:00</div>
            </div>
          </div>

          <!-- 完成：展开简报（可溯源） -->
          <div v-if="phase === 'done' && demoBrief" class="stage-brief">
            <div class="brief-head">
              <div class="brief-stamp">已送达</div>
              <p class="brief-sub">一勺热点 · 结合你的兴趣「{{ selectedTags.join('、') }}」</p>
            </div>
            <div class="brief-body">
              <p class="brief-h">AI 全局分析</p>
              <p class="brief-p">{{ demoBrief.insight }}</p>
              <p class="brief-h">原始热点 · 点击任意一条溯源</p>
              <div
                v-for="(n, i) in demoBrief.news"
                :key="i"
                class="trace-item"
                :class="{ open: tracedIdx === i }"
                @click="trace(i)"
              >
                <p class="trace-t">{{ i + 1 }}. {{ n.t }}</p>
                <p class="trace-meta">来源：{{ n.src }} · 可信度 {{ n.cred }}/10<span v-if="n.cross > 1"> · {{ n.cross }} 源交叉验证</span></p>
                <div v-if="tracedIdx === i" class="trace-detail">
                  <div class="trace-line"></div>
                  <p class="trace-src">溯源：{{ n.src }} 原始报道</p>
                  <p class="trace-note">本结论来自上方原始新闻，{{ n.cross > 1 ? `另有 ${n.cross - 1} 家独立信源报道同一事件，交叉验证通过` : '单一信源，已标注可信度供你判断' }}</p>
                </div>
              </div>
            </div>
            <div class="brief-actions">
              <span class="subscribed-chip">已订阅 · 每天 08:00 送达</span>
              <div class="brief-btns">
                <button class="btn btn-outline btn-sm" @click="resetDemo">换一批方向，再来一次</button>
                <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-primary btn-sm">进入控制台，创建订阅</button></router-link>
                <router-link v-else to="/register"><button class="btn btn-primary btn-sm">注册，让这份简报每天到达</button></router-link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 定时送达时间轴 ═══ -->
    <section class="section">
      <h2 class="reveal">你睡觉时，它在工作</h2>
      <p class="lead reveal">北京时间定时，醒来第一封就是你的私人简报</p>
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
      <p class="lead reveal">你只负责最后一件事：做决定</p>
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
      <h2 class="reveal">AI 会出错，我们让它无处可藏</h2>
      <p class="lead reveal">每一条结论都有迹可循——这是 一勺热点 和普通 AI 新闻工具最大的不同</p>
      <div class="proof-card reveal">
        <div class="proof-conclusion" :class="{ open: proofOpen }" @click="proofOpen = !proofOpen">
          <span class="proof-tag">AI 结论</span>
          <p>「国产算力扩产加速，结合你的专业背景，窗口期约 12 个月」</p>
          <span class="proof-hint">{{ proofOpen ? '收起证据链' : '点击查看证据链' }}</span>
        </div>
        <div v-if="proofOpen" class="proof-chain">
          <div class="proof-line"></div>
          <div class="proof-evid">
            <p class="pe-title">证据 1 · 燧原科技科创板 IPO 募资 61.19 亿元</p>
            <p class="pe-meta">来源：IT之家 · 可信度 8/10 · 3 源交叉验证</p>
          </div>
          <div class="proof-evid">
            <p class="pe-title">证据 2 · 国产刻蚀机良率突破，多家设备厂上调全年指引</p>
            <p class="pe-meta">来源：财新网 · 可信度 9/10 · 3 源交叉验证</p>
          </div>
          <p class="proof-note">AI 的每句结论都标注出处、经过多源交叉验证才采信——它说错了，你能第一时间查证。判断权，永远在你手里。</p>
        </div>
      </div>
    </section>

    <!-- ═══ 数据区 ═══ -->
    <section class="section stats-band">
      <div class="stat reveal"><p class="stat-num"><span data-count="14">0</span> 个</p><p class="stat-label">精选公开信源</p></div>
      <div class="stat reveal"><p class="stat-num"><span data-count="700">0</span>+ 条</p><p class="stat-label">信息池滚动热点</p></div>
      <div class="stat reveal"><p class="stat-num"><span data-count="40">0</span> 分钟</p><p class="stat-label">每天省下的刷屏时间</p></div>
      <div class="stat reveal"><p class="stat-num">08:00</p><p class="stat-label">简报准时躺在邮箱</p></div>
    </section>

    <!-- ═══ CTA ═══ -->
    <section class="section cta-band">
      <div class="cta-card reveal">
        <h2 v-if="auth.isLoggedIn">回到控制台，继续订阅</h2>
        <h2 v-else>明天早上，信息喂到嘴边</h2>
        <p v-if="auth.isLoggedIn">管理你的订阅与画像，让简报持续为你工作。</p>
        <p v-else>注册只需 1 分钟，创建你的第一份订阅，明早 8 点见。</p>
        <div class="cta-actions">
          <router-link v-if="auth.isLoggedIn" to="/dashboard/subscriptions"><button class="btn btn-primary btn-lg">进入控制台</button></router-link>
          <template v-else>
            <router-link to="/register"><button class="btn btn-primary btn-lg">免费注册</button></router-link>
            <router-link to="/login"><button class="btn btn-ghost btn-lg">已有账号，直接登录</button></router-link>
          </template>
        </div>
      </div>
    </section>

    <!-- ═══ 页脚：合规文本按链接划分 ═══ -->
    <footer class="land-footer">
      <div class="footer-links">
        <a v-if="compliance.icp_record" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">{{ compliance.icp_record }}</a>
        <button v-if="compliance.privacy_policy" class="footer-link-btn" type="button" @click="openPolicy('privacy')">隐私政策</button>
        <button v-if="compliance.disclaimer" class="footer-link-btn" type="button" @click="openPolicy('disclaimer')">免责声明</button>
      </div>
      <p style="margin-top: 10px">一勺热点 · AI 驱动的热点情报邮件 · 随时退订</p>
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
  background: linear-gradient(90deg, #fff, #ffe0b8);
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
.typing-caret::after { content: "▍"; margin-left: 2px; animation: caret-blink 1s steps(1) infinite; }
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
.fc-1  { left: 7%;  top: 20%; animation-delay: -0.8s; }
.fc-2  { right: 8%; top: 30%; animation-delay: -3.2s; animation-duration: 8s; }
.fc-3  { left: 13%; bottom: 20%; animation-delay: -5.1s; animation-duration: 6.4s; }
.fc-4  { right: 12%; bottom: 26%; animation-delay: -1.9s; animation-duration: 7.8s; }
.fc-5  { left: 24%; top: 13%; animation-delay: -4.3s; animation-duration: 8.8s; }
.fc-6  { right: 22%; top: 14%; animation-delay: -6.2s; animation-duration: 7.2s; }
.fc-7  { right: 30%; bottom: 13%; animation-delay: -2.7s; animation-duration: 6.8s; }
.fc-8  { left: 30%; bottom: 8%; animation-delay: -5.8s; animation-duration: 8.4s; }
.fc-9  { right: 3%; top: 52%; animation-delay: -0.4s; animation-duration: 9s; }
.fc-10 { left: 3%; top: 54%; animation-delay: -3.9s; animation-duration: 7.6s; }

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
.pain-label { font-size: 13px; font-weight: 700; margin-bottom: 10px; text-align: center; padding: 6px 10px; border-radius: 8px; }
.pain-label-bad { background: #fef2f2; color: var(--danger); }
.pain-label-good { background: #ecfdf5; color: var(--success); }
.pain-vs { display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800; color: var(--primary); }
.waterfall {
  flex: 1; overflow: hidden; border-radius: 12px; border: 1px solid #fecaca; background: #fff;
  position: relative; min-height: 300px;
}
.wf-col { position: absolute; inset: 0; animation: wf-fall 26s linear infinite; }
.wf-col p {
  margin: 0 0 10px; padding: 9px 12px; background: #fff5f5; border: 1px solid #fee2e2;
  border-radius: 8px; font-size: 12.5px; color: #7f1d1d; line-height: 1.5;
}
@keyframes wf-fall { from { transform: translateY(0); } to { transform: translateY(-50%); } }
.pain-caption { margin-top: 10px; text-align: center; font-size: 13px; color: var(--text-muted); font-weight: 600; }
.brief-mini {
  flex: 1; background: #fff; border-radius: 12px; border: 1px solid #a7f3d0;
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
.dstep.on { color: var(--primary); border-color: #fed7aa; background: var(--primary-light); }
.dstep.on .dstep-dot { background: var(--gradient); color: #fff; }
.dstep.active { box-shadow: 0 0 0 3px rgba(249,115,22,.18); transform: translateY(-2px); }
.demo-picker { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 18px; }
.tag-chip {
  border: 1.5px solid var(--border); background: #fff; color: var(--text-muted);
  padding: 8px 16px; border-radius: 999px; font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all .18s ease;
}
.tag-chip:hover { border-color: var(--primary); color: var(--primary); transform: translateY(-2px); }
.tag-chip.active { background: var(--gradient); border-color: transparent; color: #fff; box-shadow: 0 4px 14px rgba(249,115,22,.35); }

.demo-stage {
  position: relative; min-height: 340px; border-radius: 18px; border: 1px solid var(--border);
  background:
    radial-gradient(circle at 50% 0%, rgba(249,115,22,.06), transparent 55%),
    #fff;
  overflow: hidden; box-shadow: var(--shadow);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}

/* 待机 */
.stage-idle { text-align: center; color: var(--text-faint); }
.idle-spoon {
  width: 54px; height: 54px; margin: 0 auto 14px; border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, #fff 0 22%, transparent 23%),
              conic-gradient(from 0deg, #f97316, #f59e0b, #ea580c, #f97316);
  animation: spin 6s linear infinite;
}
.stage-idle p { font-size: 14px; }

/* 收集：新闻飞入 */
.stage-collect { position: absolute; inset: 0; }
.fly-chip {
  position: absolute; left: 50%; top: 50%; font-size: 12px; font-weight: 600;
  padding: 7px 12px; background: #fff; border: 1px solid #fed7aa; border-radius: 8px;
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
  background: radial-gradient(circle at 35% 30%, #ffd9b0, #f97316 55%, #ea580c);
  box-shadow: 0 0 42px rgba(249,115,22,.55), inset 0 0 22px rgba(255,255,255,.35);
  animation: core-throb 1.1s ease-in-out infinite;
}
@keyframes core-throb { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }
.core-ring {
  position: absolute; left: 50%; top: 50%; width: 84px; height: 84px;
  margin: -42px 0 0 -42px; border-radius: 50%;
  border: 2px solid rgba(249,115,22,.45); pointer-events: none;
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
  background: linear-gradient(180deg, #fb923c, #ea580c); border: 2.5px solid #c2410c;
}
.mailbox::before { content: ""; position: absolute; inset: 0 0 -14px 0; border-radius: 0 0 10px 10px; background: #fff7ed; border: 2.5px solid #c2410c; border-top: none; }
.mailbox::after { content: ""; position: absolute; left: 8px; right: 8px; top: -12px; height: 12px; background: #fff7ed; border: 2.5px solid #c2410c; border-bottom: none; border-radius: 6px 6px 0 0; }
.mb-flag { position: absolute; right: -30px; top: 0; width: 30px; height: 14px; background: #ef4444; border-radius: 0 4px 4px 0; transform-origin: left center; animation: flag-up .5s .5s ease forwards; opacity: 0; }
.mb-clock {
  position: absolute; top: -38px; left: 50%; transform: translateX(-50%);
  background: #fff; border: 1.5px solid #c2410c; color: #c2410c;
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
.trace-item:hover { border-color: #fed7aa; box-shadow: 0 4px 14px rgba(249,115,22,.12); }
.trace-item.open { border-color: var(--primary); }
.trace-t { font-size: 13.5px; font-weight: 700; color: var(--text); line-height: 1.5; }
.trace-meta { font-size: 12px; color: var(--text-faint); margin-top: 3px; }
.trace-detail { overflow: hidden; animation: trace-open .3s ease; }
.trace-line { height: 2px; background: linear-gradient(90deg, var(--primary), #fed7aa); margin: 10px 0 8px; transform-origin: left; animation: line-draw .45s ease both; }
@keyframes line-draw { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes trace-open { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.trace-src { font-size: 13px; font-weight: 700; color: var(--primary); }
.trace-note { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; line-height: 1.6; }
.brief-actions { display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.brief-btns { display: flex; gap: 10px; flex-wrap: wrap; margin-left: auto; }
.subscribed-chip {
  font-size: 12.5px; font-weight: 700; color: var(--success);
  background: #ecfdf5; border: 1px solid #a7f3d0; padding: 5px 12px; border-radius: 999px;
  animation: status-fade .4s ease both;
}

/* ── 溯源卖点区：证据链 ── */
.proof-card { max-width: 620px; margin: 0 auto; }
.proof-conclusion {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  background: var(--primary-light); border: 1.5px solid #fed7aa; border-radius: 14px;
  padding: 16px 18px; cursor: pointer; transition: all .2s ease;
}
.proof-conclusion:hover { border-color: var(--primary); box-shadow: 0 8px 22px rgba(249,115,22,.14); }
.proof-tag {
  font-size: 11px; font-weight: 800; letter-spacing: .08em; color: #fff;
  background: var(--gradient); padding: 3px 10px; border-radius: 6px; white-space: nowrap;
}
.proof-conclusion p { flex: 1; min-width: 220px; font-size: 15px; font-weight: 700; color: var(--text); line-height: 1.7; }
.proof-hint { font-size: 12.5px; font-weight: 700; color: var(--primary); white-space: nowrap; }
.proof-chain { padding: 6px 4px 0; animation: trace-open .35s ease; }
.proof-line {
  height: 2px; background: linear-gradient(90deg, var(--primary), #fed7aa);
  margin: 10px 0 12px; transform-origin: left; animation: line-draw .5s ease both;
}
.proof-evid {
  border-left: 3px solid #fed7aa; background: #fff; border-radius: 0 10px 10px 0;
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
  background: linear-gradient(90deg, #fed7aa, var(--primary));
  transform: scaleX(0); transform-origin: left;
}
.timeline.visible::before { animation: line-grow 1.2s ease .3s forwards; }
@keyframes line-grow { to { transform: scaleX(1); } }
.tl-node { text-align: center; position: relative; }
.tl-dot {
  width: 20px; height: 20px; margin: 0 auto 10px; border-radius: 50%;
  background: var(--gradient); border: 4px solid #fff; box-shadow: 0 0 0 2px #fed7aa;
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
  background: linear-gradient(135deg, #fff7ed, #fffbeb); border-radius: 18px; border: 1px solid #fed7aa;
  padding: 36px 20px; max-width: 980px;
}
.stat { text-align: center; }
.stat-num { font-size: 34px; font-weight: 800; background: var(--gradient); -webkit-background-clip: text; background-clip: text; color: transparent; }
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
  .float-card { display: none; }
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
  .tl-node { display: grid; grid-template-columns: 28px 64px 1fr; align-items: center; gap: 10px; text-align: left; }
  .tl-dot { margin: 0; }
  .tl-text { margin-top: 0; }
  .mailbox { right: 4%; }
  .brief-btns { margin-left: 0; }
}
</style>
