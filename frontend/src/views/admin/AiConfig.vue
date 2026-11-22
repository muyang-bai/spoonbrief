<script setup>
import SmartSelect from '../../components/SmartSelect.vue'
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
const models = ref([])
const loadingModels = ref(false)

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

async function loadModels() {
  loadingModels.value = true
  try {
    const d = await api('/admin/ai-models', { timeout: 30000 })
    models.value = d.models || []
    if (!form.value.model && d.current) form.value.model = d.current
    t.ok(models.value.length ? `已获取 ${models.value.length} 个模型` : '未获取到模型')
  } catch (e) {
    t.err(e.message)
  } finally {
    loadingModels.value = false
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
      <p class="muted">平台默认 AI 接口：所有用户统一使用这里的配置，用户端不再提供自备 Key</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else class="card" style="max-width: 720px">
      <p class="muted" style="margin-bottom: 16px">模型服务商（DeepSeek 等）- 用于内容分析</p>
      <label class="field">
        <span>服务商</span>
        <SmartSelect v-model="form.provider" :options="providers.map(p => ({value:p.v,label:p.label}))" label="AI 服务商" />
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
        <span>模型名（从服务商自动获取）</span>
        <div style="display: flex; gap: 8px">
          <SmartSelect v-if="models.length" v-model="form.model" :options="models.map(m => ({value:m,label:m}))" label="模型" />
          <input v-else v-model="form.model" class="input" placeholder="先点右侧按钮获取模型" />
          <button class="btn btn-outline" :disabled="loadingModels" @click="loadModels">
            <span v-if="loadingModels" class="spinner"></span> 获取模型
          </button>
        </div>
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
