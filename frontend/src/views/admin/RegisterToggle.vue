<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api'
import { t } from '../../toast'

const loading = ref(true)
const allow = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api('/admin/register-toggle')
    allow.value = String(res.allow_registration) === 'true'
  } catch (e) {
    t.err(e.message)
  } finally {
    loading.value = false
  }
}

async function toggle() {
  if (saving.value) return
  const next = !allow.value
  saving.value = true
  try {
    await api('/admin/register-toggle', { method: 'POST', body: { allow_registration: next } })
    allow.value = next
    t.ok(next ? '已开启注册' : '已关闭注册')
  } catch (e) {
    t.err(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-actions">
      <p class="muted">控制是否允许新用户注册，关闭后已注册用户仍可正常登录</p>
    </div>

    <div class="card" style="max-width: 680px">
      <div v-if="loading" class="loading-center">加载中…</div>

      <template v-else>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 20px">
          <div style="flex: 1">
            <h3 style="margin-bottom: 6px">🚪 注册开关</h3>
            <p class="muted" style="margin: 0">控制是否允许新用户注册，关闭后已注册用户仍可正常登录</p>
          </div>
          <label style="display: inline-block; position: relative; width: 64px; height: 34px; cursor: pointer; flex-shrink: 0">
            <input type="checkbox" :checked="allow" :disabled="saving" style="opacity: 0; width: 0; height: 0" @change="toggle" />
            <span
              style="position: absolute; inset: 0; border-radius: 999px; transition: background .2s"
              :style="allow ? 'background: var(--gradient)' : 'background: #d1d5db'"
            ></span>
            <span
              style="position: absolute; top: 3px; left: 3px; width: 28px; height: 28px; background: #fff; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,.25); transition: transform .2s"
              :style="allow ? 'transform: translateX(30px)' : ''"
            ></span>
          </label>
        </div>

        <hr class="sep" />

        <div style="display: flex; align-items: center; gap: 10px">
          <span v-if="allow" class="badge badge-green">允许注册</span>
          <span v-else class="badge badge-red">已关闭注册</span>
          <span v-if="saving" class="spinner spinner-dark"></span>
          <span v-if="saving" class="faint">保存中…</span>
        </div>
      </template>
    </div>
  </div>
</template>
