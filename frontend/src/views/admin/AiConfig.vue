<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'

const form = ref({
  provider: 'deepseek',
  api_key: '',
  base_url: '',
  model: '',
  enabled: false,
})
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)

const providers = [
  { v: 'deepseek', label: 'DeepSeek' },
  { v: 'volcano', label: '火山引擎 (Volcano)' },
]

async function load() {
  loading.value = true
  try {
    const d = await api('/admin/ai-config')
    const on = d.enabled === true || d.enabled === 1 || ['true', '1', 'on', 'yes'].includes(String(d.enabled).toLowerCase())
    form.value = {
      provider: d.provider || 'deepseek',
      api_key: d.api_key || '',
      base_url: d.base_url || '',
      model: d.model || '',
      enabled: on,
    }
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await api('/admin/ai-config', { method: 'PUT', body: { ...form.value } })
    t.ok('配置已保存')
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  try {
    const res = await api('/admin/ai-config/test', { method: 'POST', timeout: 120000 })
    t.ok(res.message || '测试成功')
  } catch (e) {
    t.err(e.message)
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">配置平台默认AI接口，用户未提供自有Key时将使用此配置</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else class="card" style="max-width: 720px">
      <p class="muted" style="margin-bottom: 16px">模型服务商（DeepSeek 等）- 用于内容分析</p>
      <label class="field">
        <span>服务商</span>
        <select v-model="form.provider" class="select">
          <option v-for="p in providers" :key="p.v" :value="p.v">{{ p.label }}</option>
        </select>
      </label>
      <label class="field">
        <span>API Key</span>
        <input v-model="form.api_key" type="password" class="input" placeholder="sk-..." />
      </label>
      <label class="field">
        <span>Base URL</span>
        <input v-model="form.base_url" class="input" placeholder="https://api.deepseek.com/v1" />
      </label>
      <label class="field">
        <span>模型名</span>
        <input v-model="form.model" class="input" placeholder="deepseek-v4-flash" />
      </label>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="form.enabled" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">启用平台默认 AI 接口</span>
      </label>
      <div class="toolbar">
        <button class="btn btn-primary" :disabled="saving || testing" @click="save">
          <span v-if="saving" class="spinner"></span> 保存配置
        </button>
        <button class="btn btn-teal" :disabled="saving || testing" @click="test">
          <span v-if="testing" class="spinner"></span> 测试连接
        </button>
      </div>
    </div>
  </div>
</template>
