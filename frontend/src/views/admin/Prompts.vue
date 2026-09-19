<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'
import Modal from '../../components/Modal.vue'

const prompts = ref([])
const loading = ref(true)
const showModal = ref(false)
const editing = ref(null)
const form = ref(blankForm())
const saving = ref(false)

const models = [
  'deepseek-v4-flash',
  'deepseek-reasoner',
]

function blankForm() {
  return {
    name: '',
    description: '',
    system_prompt: '',
    user_prompt_template: '',
    model: 'deepseek-v4-flash',
    temperature: 70,
    max_tokens: 2000,
    is_default: false,
    is_active: true,
    is_platform: true,
    is_open_source: false,
    suitable_for: '',
    tags: '',
    usage_hint: '',
  }
}

const userPromptPlaceholder =
  '告诉 AI 如何分析热点。可用变量：{{hotspots}} 会被替换为热点信息，{{profile}} 会被替换为用户画像'

function bodyFrom(form) {
  return {
    name: form.name,
    description: form.description,
    system_prompt: form.system_prompt,
    user_prompt_template: form.user_prompt_template,
    model: form.model,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
    is_default: form.is_default,
    is_active: form.is_active,
    is_platform: form.is_platform,
    is_open_source: form.is_open_source,
    suitable_for: form.suitable_for,
    tags: form.tags,
    usage_hint: form.usage_hint,
  }
}

async function load() {
  loading.value = true
  try {
    prompts.value = await api('/admin/prompts')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = blankForm()
  showModal.value = true
}

function openEdit(p) {
  editing.value = p
  form.value = {
    name: p.name || '',
    description: p.description || '',
    system_prompt: p.system_prompt || '',
    user_prompt_template: p.user_prompt_template || '',
    model: p.model || 'deepseek-v4-flash',
    temperature: p.temperature ?? 70,
    max_tokens: p.max_tokens ?? 2000,
    is_default: !!p.is_default,
    is_active: !!p.is_active,
    is_platform: !!p.is_platform,
    is_open_source: !!p.is_open_source,
    suitable_for: p.suitable_for || '',
    tags: p.tags || '',
    usage_hint: p.usage_hint || '',
  }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return t.err('请输入模板名称')
  saving.value = true
  try {
    const body = bodyFrom(form.value)
    if (editing.value) {
      await api(`/admin/prompts/${editing.value.id}`, { method: 'PUT', body })
      t.ok('模板已更新')
    } else {
      await api('/admin/prompts', { method: 'POST', body })
      t.ok('模板创建成功！')
    }
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(p) {
  if (!confirm('确认删除此模板？')) return
  try {
    await api(`/admin/prompts/${p.id}`, { method: 'DELETE' })
    t.ok('模板已删除')
    await load()
  } catch (e) {
    t.err(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">官方维护的Skill模板，定义它的分析风格和知识范围</p>
      <button class="btn btn-primary" @click="openCreate">＋ 新建模板</button>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="prompts.length === 0" class="card empty">
      <div class="big">🎯</div>
      <p>还没有创建模板</p>
      <p class="muted" style="margin: 8px 0 16px">创建官方模板，供用户端分析与 Skill 市场使用</p>
      <button class="btn btn-primary" @click="openCreate">创建第一个模板</button>
    </div>

    <div v-else class="card" style="padding: 8px 12px">
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>模型</th>
            <th>温度</th>
            <th>默认</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in prompts" :key="p.id">
            <td>
              <div style="display: flex; align-items: center; gap: 8px">
                {{ p.name }}
                <span v-if="p.is_platform" class="badge badge-blue">官方</span>
              </div>
              <div class="faint" style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                {{ p.description || '—' }}
              </div>
            </td>
            <td>{{ p.model || '—' }}</td>
            <td>{{ p.temperature ?? '—' }}</td>
            <td>
              <span v-if="p.is_default" class="badge">默认分析师</span>
              <span v-else class="faint">—</span>
            </td>
            <td>
              <span v-if="p.is_active" class="badge badge-green">启用</span>
              <span v-else class="badge badge-gray">停用</span>
            </td>
            <td>
              <div style="display: flex; gap: 6px">
                <button class="btn btn-outline btn-sm" @click="openEdit(p)">编辑</button>
                <button class="btn btn-sm" style="color: var(--danger)" @click="remove(p)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :show="showModal" :title="editing ? '编辑模板' : '新建模板'" width="680px" @close="showModal = false">
      <label class="field">
        <span>名称</span>
        <input v-model="form.name" class="input" placeholder="给模板起个名字，让其他人一眼知道它的用途" />
      </label>
      <label class="field">
        <span>描述</span>
        <input v-model="form.description" class="input" placeholder="用一两句话告诉其他用户这个模板擅长什么" />
      </label>
      <label class="field">
        <span>System Prompt</span>
        <textarea v-model="form.system_prompt" class="textarea" placeholder="请输入System Prompt。告诉 AI 它是谁、怎么思考。例如：你是一位资深…"></textarea>
      </label>
      <label class="field">
        <span>User Prompt 模板</span>
        <textarea v-model="form.user_prompt_template" class="textarea" :placeholder="userPromptPlaceholder"></textarea>
      </label>
      <label class="field">
        <span>模型</span>
        <input v-model="form.model" class="input" list="model-suggest" placeholder="deepseek-v4-flash" />
        <datalist id="model-suggest">
          <option v-for="m in models" :key="m" :value="m" />
        </datalist>
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>温度（0-100）</span>
          <input v-model.number="form.temperature" type="number" min="0" max="100" class="input" />
        </label>
        <label class="field">
          <span>最大字数（tokens）</span>
          <input v-model.number="form.max_tokens" type="number" min="1" class="input" />
        </label>
      </div>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="form.is_default" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">设为默认分析师（官方）</span>
      </label>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="form.is_open_source" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">开源此模板（勾选后所有用户可见可用）</span>
      </label>
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>适用画像</span>
          <input v-model="form.suitable_for" class="input" placeholder="如：考研学生、投资者" />
        </label>
        <label class="field">
          <span>标签</span>
          <input v-model="form.tags" class="input" placeholder="教育,考研,政策,AI" />
        </label>
      </div>
      <label class="field">
        <span>使用提示</span>
        <input v-model="form.usage_hint" class="input" placeholder="帮助其他用户搜索到这个模板" />
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> {{ editing ? '保存修改' : '创建模板' }}
        </button>
      </div>
    </Modal>
  </div>
</template>
