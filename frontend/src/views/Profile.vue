<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'

const profile = ref(null)
const quota = ref(null)
const loading = ref(true)
const saving = ref(false)

const identityOptions = [
  { v: '学生' },
  { v: '创业者' },
  { v: '投资者' },
  { v: '创作者' },
]

function blankSections() {
  return {
    student: { major: '', target_school: '' },
    entrepreneur: { industry: '', stage: '' },
    investor: { focus_areas: '', risk_preference: '' },
    creator: { domains: '', platform: '' },
  }
}

const form = ref({
  identities: [],
  ...blankSections(),
  interestsText: '',
  self_description: '',
})

const quotaPct = computed(() => {
  if (!quota.value || !quota.value.quota_total) return 0
  return Math.min(100, Math.round((quota.value.quota_used / quota.value.quota_total) * 100))
})

function applyPersona(raw) {
  let persona = {}
  if (raw) {
    try {
      persona = JSON.parse(raw) || {}
    } catch {
      persona = {}
    }
  }
  const pickObj = (stored, keys) => {
    const out = {}
    for (const k of keys) {
      out[k] = stored && typeof stored[k] === 'string' ? stored[k] : ''
    }
    return out
  }
  // 兼容旧版键名：从任意别名键取值填入标准键
  const pickAlias = (stored, aliasMap) => {
    const out = {}
    for (const [stdKey, aliases] of Object.entries(aliasMap)) {
      let v = ''
      for (const a of [stdKey, ...aliases]) {
        if (stored && typeof stored[a] === 'string' && stored[a]) { v = stored[a]; break }
      }
      out[stdKey] = v
    }
    return out
  }
  const pickSection = (key, aliasMap) =>
    pickAlias(persona[key] && typeof persona[key] === 'object' ? persona[key] : {}, aliasMap)

  let interestsText = ''
  if (Array.isArray(persona.interests)) interestsText = persona.interests.join(', ')
  else if (persona.interests && typeof persona.interests === 'object') {
    const vals = []
    for (const v of Object.values(persona.interests)) {
      if (Array.isArray(v)) vals.push(...v)
      else if (typeof v === 'string') vals.push(v)
    }
    interestsText = vals.join(', ')
  } else if (typeof persona.interests === 'string') interestsText = persona.interests

  form.value = {
    identities: Array.isArray(persona.identities) ? persona.identities.slice() : [],
    student: pickSection('student', { major: ['school', '专业'], target_school: ['grade', '院校', 'target'] }),
    entrepreneur: pickSection('entrepreneur', { industry: ['行业'], stage: ['阶段'] }),
    investor: pickSection('investor', { focus_areas: ['focus', '关注领域'], risk_preference: ['风险偏好'] }),
    creator: pickSection('creator', { domains: ['field', '领域'], platform: ['平台'] }),
    interestsText,
    self_description: typeof persona.self_description === 'string' ? persona.self_description : '',
  }
}

async function load() {
  loading.value = true
  try {
    const [p, q] = await Promise.all([api('/profile/'), api('/profile/quota')])
    profile.value = p
    quota.value = q
    applyPersona(p.persona_json)
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function hasIdentity(v) {
  return form.value.identities.includes(v)
}

function toggleIdentity(v) {
  const i = form.value.identities.indexOf(v)
  if (i >= 0) form.value.identities.splice(i, 1)
  else form.value.identities.push(v)
}

function chipStyle(v) {
  const active = hasIdentity(v)
  return {
    border: active ? '1px solid transparent' : '1px solid var(--border)',
    background: active ? '' : '#f3f4f6',
    color: active ? '' : 'var(--text-muted)',
    cursor: 'pointer',
    fontFamily: 'inherit',
  }
}

async function save() {
  saving.value = true
  try {
    const body = {
      identities: [...form.value.identities],
      student: { ...form.value.student },
      entrepreneur: { ...form.value.entrepreneur },
      investor: { ...form.value.investor },
      creator: { ...form.value.creator },
      interests: form.value.interestsText.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      self_description: form.value.self_description,
    }
    await api('/profile/persona', { method: 'PUT', body })
    t.ok('画像已更新')
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div v-if="loading" class="loading-center">加载中…</div>

    <template v-else>
      <div class="grid-2">
        <div class="card">
          <h3>账号信息</h3>
          <div style="display: flex; flex-direction: column; gap: 12px">
            <div>
              <div class="faint">邮箱</div>
              <div>{{ profile?.email || '—' }}</div>
            </div>
            <div>
              <div class="faint">昵称</div>
              <div>{{ profile?.nickname || '—' }}</div>
            </div>
            <div>
              <div class="faint">角色</div>
              <span class="badge" :class="profile?.role === 'admin' ? 'badge-red' : 'badge-blue'">
                {{ profile?.role === 'admin' ? '管理员' : '普通用户' }}
              </span>
            </div>
            <div>
              <div class="faint">上次登录时间</div>
              <div>{{ fmtTime(profile?.last_login_at) }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <h3>API 配额</h3>
          <div style="font-size: 44px; font-weight: 800; line-height: 1.15; background: var(--gradient); -webkit-background-clip: text; background-clip: text; color: transparent;">
            {{ quota?.quota_remaining ?? '—' }}
          </div>
          <div class="muted">本月剩余分析次数</div>
          <div style="background: #f3f4f6; border-radius: 999px; height: 10px; overflow: hidden; margin: 16px 0 8px">
            <div :style="{ width: quotaPct + '%', height: '100%', background: 'var(--gradient)', transition: 'width .3s' }"></div>
          </div>
          <p class="muted">已使用 {{ quota?.quota_used ?? 0 }} / 总配额 {{ quota?.quota_total ?? 0 }} 次</p>
          <p class="faint">重置时间：{{ fmtTime(quota?.quota_reset_at) }}</p>
          <div v-if="quota?.is_exhausted" class="danger-zone" style="margin-top: 14px">
            ⚠️ 本月配额已用完，AI 分析将暂时无法生成，请等待下月重置或添加自己的 API Key
          </div>
        </div>
      </div>

      <div class="card" style="margin-top: 18px">
        <h3>AI 画像</h3>
        <p class="muted">告诉 AI 你的完整情况，越详细分析越精准</p>
        <p class="faint" style="margin-bottom: 16px">会根据你的身份自动调整分析视角</p>

        <div style="margin-bottom: 16px">
          <p class="muted" style="font-size: 13px; font-weight: 600; margin-bottom: 6px">身份角色（可多选）</p>
          <div class="toolbar" style="margin-bottom: 6px">
            <button
              v-for="o in identityOptions"
              :key="o.v"
              type="button"
              class="chip"
              :style="chipStyle(o.v)"
              @click="toggleIdentity(o.v)"
            >
              {{ o.v }}<span v-if="hasIdentity(o.v)"> ✓</span>
            </button>
          </div>
          <p class="faint">选择你的身份角色（可多选），AI 将针对每个身份做交叉分析</p>
        </div>

        <div v-if="hasIdentity('学生')" style="margin-bottom: 16px">
          <p style="font-weight: 700; margin-bottom: 10px">学生信息</p>
          <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
            <label class="field">
              <span>专业</span>
              <input v-model="form.student.major" class="input" placeholder="例如：计算机科学与技术" />
            </label>
            <label class="field">
              <span>目标院校</span>
              <input v-model="form.student.target_school" class="input" placeholder="例如：清华大学" />
            </label>
          </div>
          <p class="faint">输入你的专业和目标院校，AI 会针对性分析</p>
        </div>

        <div v-if="hasIdentity('创业者')" style="margin-bottom: 16px">
          <p style="font-weight: 700; margin-bottom: 10px">创业者信息</p>
          <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
            <label class="field">
              <span>行业</span>
              <input v-model="form.entrepreneur.industry" class="input" placeholder="例如：人工智能 / 跨境电商" />
            </label>
            <label class="field">
              <span>阶段</span>
              <input v-model="form.entrepreneur.stage" class="input" placeholder="例如：种子轮 / A 轮 / 已盈利" />
            </label>
          </div>
        </div>

        <div v-if="hasIdentity('投资者')" style="margin-bottom: 16px">
          <p style="font-weight: 700; margin-bottom: 10px">投资者信息</p>
          <label class="field">
            <span>关注领域</span>
            <input v-model="form.investor.focus_areas" class="input" placeholder="例如：新能源、半导体、AI" />
          </label>
          <label class="field">
            <span>风险偏好</span>
            <input v-model="form.investor.risk_preference" class="input" placeholder="例如：稳健型 / 平衡型 / 激进型" />
          </label>
        </div>

        <div v-if="hasIdentity('创作者')" style="margin-bottom: 16px">
          <p style="font-weight: 700; margin-bottom: 10px">创作者信息</p>
          <label class="field">
            <span>内容领域</span>
            <input v-model="form.creator.domains" class="input" placeholder="例如：科技测评、知识科普" />
          </label>
          <label class="field">
            <span>发布平台</span>
            <input v-model="form.creator.platform" class="input" placeholder="例如：B站、公众号、抖音" />
          </label>
        </div>

        <hr v-if="form.identities.length > 0" class="sep" />

        <label class="field">
          <span>兴趣标签（逗号分隔）</span>
          <input v-model="form.interestsText" class="input" placeholder="教育,考研,政策,AI" />
        </label>
        <label class="field">
          <span>自我介绍</span>
          <textarea v-model="form.self_description" class="textarea" placeholder="例如：我是大二学生，计算机专业，打算考研"></textarea>
        </label>

        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
          <button class="btn btn-primary" :disabled="saving" @click="save">
            <span v-if="saving" class="spinner"></span> 保存画像
          </button>
          <span class="faint">热点信息将按你的兴趣优先级排序</span>
        </div>
      </div>
    </template>
  </div>
</template>
