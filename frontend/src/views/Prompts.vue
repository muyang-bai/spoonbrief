<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import Modal from '../components/Modal.vue'

const data = ref({ platform: [], open_source: [], my: [] })
const loading = ref(true)
const tab = ref('platform')

const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref(blankForm())

const showGuide = ref(false)

const showDetail = ref(false)
const detail = ref(null)

const fileInput = ref(null)
const importing = ref(false)

function blankForm() {
  return {
    name: '',
    description: '',
    system_prompt: '',
    user_prompt_template: '',
    model: '',
    temperature: 70,
    max_tokens: 2000,
    is_open_source: false,
    suitable_for: '',
    tags: '',
    usage_hint: '',
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api('/prompts/')
    data.value = {
      platform: res.platform || [],
      open_source: res.open_source || [],
      my: res.my || [],
    }
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function currentList() {
  if (tab.value === 'platform') return data.value.platform
  if (tab.value === 'open_source') return data.value.open_source
  return data.value.my
}

function splitList(v) {
  if (!v) return []
  if (Array.isArray(v)) return v.map(String)
  return String(v).split(',').map((s) => s.trim()).filter(Boolean)
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

function openCreate() {
  editing.value = null
  form.value = blankForm()
  showForm.value = true
}

function openEdit(p) {
  editing.value = p
  form.value = {
    name: p.name || '',
    description: p.description || '',
    system_prompt: p.system_prompt || '',
    user_prompt_template: p.user_prompt_template || '',
    model: p.model || '',
    temperature: p.temperature ?? 70,
    max_tokens: p.max_tokens ?? 2000,
    is_open_source: !!p.is_open_source,
    suitable_for: Array.isArray(p.suitable_for) ? p.suitable_for.join(',') : (p.suitable_for || ''),
    tags: Array.isArray(p.tags) ? p.tags.join(',') : (p.tags || ''),
    usage_hint: p.usage_hint || '',
  }
  showForm.value = true
}

async function save() {
  if (!form.value.name.trim()) return t.err('请输入模板名称')
  if (!form.value.system_prompt.trim()) return t.err('请输入System Prompt')
  saving.value = true
  try {
    const body = {
      name: form.value.name.trim(),
      description: form.value.description.trim(),
      system_prompt: form.value.system_prompt,
      user_prompt_template: form.value.user_prompt_template,
      model: form.value.model.trim(),
      temperature: Number(form.value.temperature),
      max_tokens: Number(form.value.max_tokens) || 0,
      is_open_source: !!form.value.is_open_source,
      suitable_for: form.value.suitable_for.trim(),
      tags: form.value.tags.trim(),
      usage_hint: form.value.usage_hint.trim(),
    }
    if (editing.value) {
      await api(`/prompts/${editing.value.id}`, { method: 'PUT', body })
      t.ok('模板已更新')
    } else {
      await api('/prompts/', { method: 'POST', body })
      t.ok('模板创建成功！')
    }
    showForm.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(p) {
  if (!confirm(`确认删除此模板「${p.name}」吗？`)) return
  try {
    await api(`/prompts/${p.id}`, { method: 'DELETE' })
    t.ok('模板已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

function openDetail(p) {
  detail.value = p
  showDetail.value = true
}

async function download(p) {
  try {
    const json = await api(`/prompts/${p.id}/export`)
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${p.name || 'skill'}.spoonskill.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    t.ok('已导出')
  } catch (e) {
    t.err(e.message)
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  try {
    const text = await file.text()
    const json = JSON.parse(text)
    if (!json || typeof json !== 'object') throw new SyntaxError('bad json')
    importing.value = true
    await api('/prompts/import', { method: 'POST', body: json })
    t.ok('导入成功！')
    await load()
  } catch (err) {
    if (err instanceof SyntaxError) t.err('文件不是有效的 JSON')
    else t.err(err.message)
  } finally {
    importing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">浏览官方与社区分享的分析模板，或创建你自己的模板</p>
      <div class="toolbar">
        <button class="btn btn-outline" @click="showGuide = true">📖 创建指南</button>
        <button class="btn btn-outline" :disabled="importing" @click="pickFile">
          <span v-if="importing" class="spinner spinner-dark"></span> 导入 Skill
        </button>
        <input ref="fileInput" type="file" accept=".json" style="display: none" @change="onFile" />
        <button class="btn btn-primary" @click="openCreate">＋ 创建模板</button>
      </div>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'platform' }" @click="tab = 'platform'">官方模板</button>
      <button class="tab" :class="{ active: tab === 'open_source' }" @click="tab = 'open_source'">开源模板</button>
      <button class="tab" :class="{ active: tab === 'my' }" @click="tab = 'my'">我的模板</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="currentList().length === 0" class="card empty">
      <div class="big">🎯</div>
      <p v-if="tab === 'platform'">暂无可用模板</p>
      <p v-else-if="tab === 'open_source'">暂无用户分享的模板，创建模板并勾选「开源此模板」即可分享</p>
      <template v-else>
        <p>还没有创建模板，点击右上角「创建模板」按钮开始</p>
        <button class="btn btn-primary" style="margin-top: 16px" @click="openCreate">创建模板</button>
      </template>
    </div>

    <div v-else class="grid-2">
      <div v-for="p in currentList()" :key="p.id" class="card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px">
          <h3 style="margin-bottom: 4px">{{ p.name }}</h3>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px">
          <span v-if="p.model" class="badge badge-gray">{{ p.model }}</span>
          <span v-if="p.temperature != null" class="badge badge-teal">温度: {{ p.temperature }}</span>
          <span v-if="p.max_tokens" class="badge badge-blue">最大字数: {{ p.max_tokens }}</span>
        </div>
        <p v-if="p.description" class="muted" style="margin-bottom: 8px">{{ p.description }}</p>
        <p v-if="tab === 'platform'" class="faint" style="margin-bottom: 8px">平台官方模板，由管理员维护</p>

        <div v-if="splitList(p.suitable_for).length" style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px">
          <span class="muted" style="align-self: center">适用画像：</span>
          <span v-for="s in splitList(p.suitable_for)" :key="s" class="chip">{{ s }}</span>
        </div>
        <div v-if="splitList(p.tags).length" style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px">
          <span v-for="s in splitList(p.tags)" :key="s" class="chip">{{ s }}</span>
        </div>
        <p v-if="p.usage_hint" class="muted" style="margin-bottom: 8px">使用提示：{{ p.usage_hint }}</p>

        <p v-if="tab !== 'platform'" class="faint">创作者：{{ p.owner_id || '—' }} · 创建时间：{{ fmtTime(p.created_at) }}</p>

        <div style="display: flex; gap: 8px; margin-top: 14px">
          <template v-if="tab !== 'platform'">
            <button class="btn btn-outline btn-sm" @click="openDetail(p)">查看详情</button>
            <button v-if="!p.is_platform || p.is_open_source" class="btn btn-teal btn-sm" @click="download(p)">⬇ 下载此 Skill</button>
          </template>
          <template v-if="tab === 'my'">
            <button class="btn btn-outline btn-sm" @click="openEdit(p)">编辑</button>
            <button class="btn btn-sm" style="color: var(--danger)" @click="remove(p)">删除</button>
          </template>
        </div>
      </div>
    </div>

    <!-- 创建 / 编辑模板 -->
    <Modal :show="showForm" :title="editing ? '编辑模板' : '创建模板'" width="640px" @close="showForm = false">
      <label class="field">
        <span>模板名称</span>
        <input v-model="form.name" class="input" placeholder="给模板起个名字，让其他人一眼知道它的用途" />
      </label>
      <label class="field">
        <span>模板简介</span>
        <textarea v-model="form.description" class="textarea" placeholder="用一两句话告诉其他用户这个模板擅长什么"></textarea>
      </label>
      <label class="field">
        <span>System Prompt（角色设定）</span>
        <textarea v-model="form.system_prompt" class="textarea" rows="5"></textarea>
        <p class="muted" style="margin-top: 6px">告诉 AI 它是谁，怎么思考。</p>
      </label>
      <label class="field">
        <span>User Prompt（分析指令，支持 {content} {persona} 变量）</span>
        <textarea v-model="form.user_prompt_template" class="textarea" rows="4"></textarea>
        <p class="muted" style="margin-top: 6px">{content} 会被替换为热点信息，{persona} 会被替换为用户画像</p>
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>模型名</span>
          <input v-model="form.model" class="input" placeholder="如：deepseek-v4-flash" />
        </label>
        <label class="field">
          <span>最大字数（tokens）</span>
          <input v-model.number="form.max_tokens" type="number" min="1" step="1" class="input" />
        </label>
      </div>
      <label class="field">
        <span>温度（0-100）：{{ form.temperature }}</span>
        <input v-model.number="form.temperature" type="range" min="0" max="100" style="width: 100%; accent-color: var(--primary)" />
      </label>
      <label class="field">
        <span>适用画像（逗号分隔）</span>
        <input v-model="form.suitable_for" class="input" placeholder="如：教育,考研,政策,AI" />
        <p class="muted" style="margin-top: 6px">勾选后，拥有对应画像的用户会优先看到此模板</p>
      </label>
      <label class="field">
        <span>标签（逗号分隔）</span>
        <input v-model="form.tags" class="input" placeholder="帮助其他用户搜索到这个模板" />
      </label>
      <label class="field">
        <span>使用提示</span>
        <input v-model="form.usage_hint" class="input" placeholder="告诉其他用户如何使用这个模板" />
      </label>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="form.is_open_source" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">开源此模板（勾选后所有用户可见可用）</span>
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showForm = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> {{ editing ? '保存修改' : '创建模板' }}
        </button>
      </div>
    </Modal>

    <!-- 模板详情 -->
    <Modal :show="showDetail" :title="detail?.name || '模板详情'" width="640px" @close="showDetail = false">
      <template v-if="detail">
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px">
          <span v-if="detail.model" class="badge badge-gray">{{ detail.model }}</span>
          <span v-if="detail.temperature != null" class="badge badge-teal">温度: {{ detail.temperature }}</span>
          <span v-if="detail.max_tokens" class="badge badge-blue">最大字数: {{ detail.max_tokens }}</span>
          <span class="badge">{{ detail.is_open_source ? '开源' : '私有' }}</span>
        </div>
        <p v-if="detail.description" class="muted" style="margin-bottom: 12px">{{ detail.description }}</p>
        <p v-if="detail.usage_hint" class="muted" style="margin-bottom: 12px">使用提示：{{ detail.usage_hint }}</p>
        <div v-if="detail.system_prompt" style="margin-bottom: 12px">
          <p class="muted" style="font-weight: 600">System Prompt（角色设定）</p>
          <div class="muted" style="white-space: pre-wrap; word-break: break-word; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; margin-top: 6px">{{ detail.system_prompt }}</div>
        </div>
        <div v-if="detail.user_prompt_template" style="margin-bottom: 12px">
          <p class="muted" style="font-weight: 600">User Prompt（分析指令）</p>
          <div class="muted" style="white-space: pre-wrap; word-break: break-word; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; margin-top: 6px">{{ detail.user_prompt_template }}</div>
        </div>
        <div v-if="splitList(detail.suitable_for).length" style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px">
          <span class="muted" style="align-self: center">适用画像：</span>
          <span v-for="s in splitList(detail.suitable_for)" :key="s" class="chip">{{ s }}</span>
        </div>
        <div v-if="splitList(detail.tags).length" style="display: flex; gap: 6px; flex-wrap: wrap">
          <span class="muted" style="align-self: center">标签：</span>
          <span v-for="s in splitList(detail.tags)" :key="s" class="chip">{{ s }}</span>
        </div>
        <p class="faint" style="margin-top: 12px">创作者：{{ detail.owner_id || '—' }} · 创建时间：{{ fmtTime(detail.created_at) }}</p>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showDetail = false">关闭</button>
          <button v-if="!detail.is_platform || detail.is_open_source" class="btn btn-teal" @click="download(detail)">⬇ 下载此 Skill</button>
        </div>
      </template>
    </Modal>

    <!-- 创建模板指南 -->
    <Modal :show="showGuide" title="📖 分析模板创建指南" width="680px" @close="showGuide = false">
      <div class="report-html" style="font-size: 14px">
        <h3>模板是什么？</h3>
        <p>模板 = <strong>AI 的角色设定</strong> + <strong>分析指令</strong>。创建订阅时选择不同模板，AI 就会以不同身份和框架为您分析热点。</p>

        <h3>两个变量（重要）</h3>
        <ul>
          <li><strong>{content}</strong>：热点信息。系统会自动把抓取到的新闻注入到这个位置。您的模板中<strong>必须包含</strong>此变量，否则 AI 看不到任何新闻。</li>
          <li><strong>{persona}</strong>：读者画像。系统会自动注入您在"我的画像"中填写的身份与兴趣。可选，但包含它 AI 才能"以您的视角"分析。</li>
        </ul>
        <p>注意：变量必须使用<strong>单个</strong>花括号 <span class="code">{content}</span>，不要写成双花括号。</p>

        <h3>推荐结构（可直接复制）</h3>
        <p class="code" style="display: block; padding: 10px 14px; white-space: pre-wrap">你是一位资深分析师，风格犀利直接。
输出三大模块：
1. 白话解读：每条热点 2-3 句话讲清"是什么、为什么重要"
2. 与我相关：结合读者画像分析对我的影响
3. 行动建议：3-5 条具体可执行的下一步
引用热点必须标注来源编号（如「据[3]报道」），禁止编造。

## 读者画像
{persona}

## 热点信息
{content}</p>

        <h3>输出规范（必须遵守）</h3>
        <ul>
          <li>只输出 HTML 正文片段（<span class="code">&lt;h3&gt; &lt;p&gt; &lt;ul&gt;&lt;li&gt; &lt;strong&gt;</span>），禁止整页结构、CSS、内联样式</li>
          <li>直接输出内容，不要先描述"我接下来会输出什么"</li>
          <li>引用热点必须标注来源编号；没有依据的内容不要编造</li>
        </ul>

        <h3>开源说明</h3>
        <ul>
          <li><strong>勾选"开源此模板"</strong>：所有用户都能在"开源模板"页看到并使用您的模板（也可下载导入）</li>
          <li><strong>不勾选</strong>：仅您自己可见、可用，属于私有模板</li>
          <li>官方模板由管理员维护，普通用户不可编辑；您创建的模板随时可以编辑、删除</li>
        </ul>

        <h3>命名与描述技巧</h3>
        <ul>
          <li>名称：一眼看出角色，如"考研政策分析师"、"短线情报员"</li>
          <li>描述：一句话说明擅长什么，如"解读教育政策，给出备考行动清单"</li>
          <li>适用画像：勾选对应身份（学生/创业者/投资者/创作者），匹配的用户会优先看到</li>
        </ul>
      </div>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showGuide = false">关闭</button>
        <button class="btn btn-primary" @click="showGuide = false; openCreate()">去创建模板</button>
      </div>
    </Modal>
  </div>
</template>
