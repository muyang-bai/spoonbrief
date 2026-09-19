<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'

const form = ref({
  host: '',
  port: '',
  user: '',
  password: '',
  from_email: '',
  from_name: '',
  use_ssl: 'false',
})
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)

const useSsl = computed({
  get: () => form.value.use_ssl === 'true',
  set: (v) => { form.value.use_ssl = v ? 'true' : 'false' },
})

async function load() {
  loading.value = true
  try {
    const d = await api('/admin/smtp')
    const ssl = d.use_ssl === true || d.use_ssl === 1 || ['true', '1', 'on', 'yes'].includes(String(d.use_ssl).toLowerCase())
    form.value = {
      host: d.host || '',
      port: String(d.port ?? ''),
      user: d.user || '',
      password: d.password || '',
      from_email: d.from_email || '',
      from_name: d.from_name || '',
      use_ssl: ssl ? 'true' : 'false',
    }
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.value.host.trim()) return t.err('请填写 SMTP 服务器地址')
  saving.value = true
  try {
    await api('/admin/smtp', {
      method: 'PUT',
      body: { ...form.value, host: form.value.host.trim(), port: String(form.value.port).trim() },
    })
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
    const res = await api('/admin/smtp/test', { method: 'POST', timeout: 60000 })
    t.ok(res.message || '测试邮件发送成功')
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
      <p class="muted">邮件服务 - 用于发送简报邮件</p>
    </div>

    <div v-if="loading" class="loading-center">加载中…</div>

    <div v-else class="card" style="max-width: 720px">
      <div class="grid-2" style="grid-template-columns: 1fr 1fr; gap: 12px">
        <label class="field">
          <span>SMTP 服务器</span>
          <input v-model="form.host" class="input" placeholder="smtp.example.com" />
        </label>
        <label class="field">
          <span>端口</span>
          <input v-model="form.port" class="input" placeholder="465" />
        </label>
        <label class="field">
          <span>用户名</span>
          <input v-model="form.user" class="input" placeholder="SMTP 登录账号" />
        </label>
        <label class="field">
          <span>密码 / 授权码</span>
          <input v-model="form.password" type="password" class="input" placeholder="SMTP 密码或授权码" />
        </label>
        <label class="field">
          <span>发件邮箱</span>
          <input v-model="form.from_email" class="input" placeholder="noreply@example.com" />
        </label>
        <label class="field">
          <span>发件人名称</span>
          <input v-model="form.from_name" class="input" placeholder="一勺热点" />
        </label>
      </div>
      <label class="field" style="display: flex; align-items: center; gap: 8px">
        <input v-model="useSsl" type="checkbox" style="accent-color: var(--primary); width: 16px; height: 16px" />
        <span style="margin: 0">使用 SSL（加密连接）</span>
      </label>
      <div class="toolbar">
        <button class="btn btn-primary" :disabled="saving || testing" @click="save">
          <span v-if="saving" class="spinner"></span> 保存配置
        </button>
        <button class="btn btn-teal" :disabled="saving || testing" @click="test">
          <span v-if="testing" class="spinner"></span> 测试发送
        </button>
      </div>
    </div>
  </div>
</template>
