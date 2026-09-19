<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { t } from '../toast'
import Modal from '../components/Modal.vue'

const keys = ref([])
const loading = ref(true)
const showModal = ref(false)
const saving = ref(false)
const form = ref(blankForm())

const providers = [
  { v: 'deepseek', label: 'DeepSeek' },
  { v: 'volcano', label: '火山方舟' },
  { v: 'openai', label: 'OpenAI' },
]

function blankForm() {
  return { provider: 'deepseek', api_key: '', base_url: '', model: '', label: '' }
}

function providerLabel(v) {
  return providers.find((p) => p.v === v)?.label || v || '—'
}

function providerBadge(v) {
  return { deepseek: 'badge-blue', volcano: 'badge-red', openai: 'badge-teal' }[v] || 'badge-gray'
}

function fmtTime(s) {
  return s ? new Date(s).toLocaleString('zh-CN') : '—'
}

async function load() {
  loading.value = true
  try {
    keys.value = await api('/api-keys/')
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

function openAdd() {
  form.value = blankForm()
  showModal.value = true
}

async function save() {
  if (!form.value.provider) return t.err('请选择服务商')
  if (!form.value.api_key.trim()) return t.err('请填写 API Key')
  saving.value = true
  try {
    await api('/api-keys/', {
      method: 'POST',
      body: {
        provider: form.value.provider,
        api_key: form.value.api_key.trim(),
        base_url: form.value.base_url.trim(),
        model: form.value.model.trim(),
        label: form.value.label.trim(),
      },
    })
    t.ok('API Key 已添加')
    showModal.value = false
    await load()
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(k) {
  const name = k.label || providerLabel(k.provider)
  if (!confirm(`确认删除此 API Key「${name}」吗？`)) return
  try {
    await api(`/api-keys/${k.id}`, { method: 'DELETE' })
    t.ok('API Key 已删除')
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
      <p class="muted">配置你自己的 API 接口</p>
      <button class="btn btn-primary" @click="openAdd">＋ 添加 API Key</button>
    </div>

    <div class="card" style="margin-bottom: 18px">
      <p class="muted">添加你自己的 API Key，分析时优先使用。未添加则使用平台默认接口。</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else-if="keys.length === 0" class="card empty">
      <div class="big">🔑</div>
      <p>暂无添加，点击右上角「添加 API Key」使用你自己的额度</p>
    </div>

    <div v-else class="grid-2">
      <div v-for="k in keys" :key="k.id" class="card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px">
          <div style="min-width: 0">
            <h3 style="margin-bottom: 10px">
              <span class="badge" :class="providerBadge(k.provider)">{{ providerLabel(k.provider) }}</span>
              <span v-if="k.is_platform" class="badge badge-teal" style="margin-left: 6px">平台</span>
              <span v-if="k.is_active === false" class="badge badge-gray" style="margin-left: 6px">已停用</span>
            </h3>
            <p v-if="k.label" class="muted">标签：{{ k.label }}</p>
            <p class="muted">模型：{{ k.model || '默认' }}</p>
            <p class="faint" style="word-break: break-all">Base URL：{{ k.base_url || '—' }}</p>
            <p class="faint">添加时间：{{ fmtTime(k.created_at) }}</p>
          </div>
          <button class="btn btn-sm" style="color: var(--danger)" :disabled="k.is_platform" :title="k.is_platform ? '平台 Key 不可删除' : ''" @click="remove(k)">删除</button>
        </div>
      </div>
    </div>

    <Modal :show="showModal" title="添加 API Key" @close="showModal = false">
      <label class="field">
        <span>服务商</span>
        <select v-model="form.provider" class="select">
          <option v-for="p in providers" :key="p.v" :value="p.v">{{ p.label }}</option>
        </select>
      </label>
      <label class="field">
        <span>API Key</span>
        <input v-model="form.api_key" type="password" class="input" placeholder="sk-..." autocomplete="off" />
        <p class="muted" style="margin-top: 6px">密钥使用 AES-256 对称加密存储</p>
      </label>
      <label class="field">
        <span>Base URL（可选）</span>
        <input v-model="form.base_url" class="input" placeholder="https://api.deepseek.com" />
      </label>
      <label class="field">
        <span>模型名（可选）</span>
        <input v-model="form.model" class="input" placeholder="如：deepseek-v4-flash" />
      </label>
      <label class="field">
        <span>标签（可选）</span>
        <input v-model="form.label" class="input" placeholder="如：我的DeepSeek" />
      </label>
      <div class="modal-actions">
        <button class="btn btn-outline" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner"></span> 添加
        </button>
      </div>
    </Modal>
  </div>
</template>
