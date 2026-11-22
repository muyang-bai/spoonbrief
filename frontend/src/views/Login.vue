<script setup>
import SiteFooter from '../components/SiteFooter.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { setLogin } from '../auth'
import { t } from '../toast'

const router = useRouter()
const account = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

// ── 忘记密码 ──
const resetMode = ref(false)
const resetEmail = ref('')
const resetCode = ref('')
const resetPassword = ref('')
const resetSending = ref(false)
const resetCountdown = ref(0)
const resetError = ref('')
let resetTimer = null

async function doLogin() {
  error.value = ''
  if (!account.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    const res = await api('/auth/login', { method: 'POST', body: { account: account.value, password: password.value } })
    setLogin(res.access_token, res.user)
    t.ok('欢迎回来')
    router.push('/dashboard/subscriptions')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function sendResetCode() {
  resetError.value = ''
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(resetEmail.value)) {
    resetError.value = '请输入正确的邮箱地址'
    return
  }
  resetSending.value = true
  try {
    await api('/auth/send-reset-code', { method: 'POST', body: { email: resetEmail.value } })
    t.ok('重置验证码已提交发送，请查收邮箱（5 分钟内有效）')
    resetCountdown.value = 60
    resetTimer = setInterval(() => {
      resetCountdown.value -= 1
      if (resetCountdown.value <= 0) clearInterval(resetTimer)
    }, 1000)
  } catch (e) {
    resetError.value = e.message
  } finally {
    resetSending.value = false
  }
}

async function doReset() {
  resetError.value = ''
  if (!resetCode.value) return (resetError.value = '请输入邮箱验证码')
  if (resetPassword.value.length < 8 || !/[a-zA-Z]/.test(resetPassword.value) || !/\d/.test(resetPassword.value)) {
    return (resetError.value = '新密码至少 8 位，且同时包含字母与数字')
  }
  loading.value = true
  try {
    await api('/auth/reset-password', {
      method: 'POST',
      body: { email: resetEmail.value, code: resetCode.value, new_password: resetPassword.value },
    })
    t.ok('密码已重置，请用新密码登录')
    resetMode.value = false
    password.value = ''
  } catch (e) {
    resetError.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
  <header class="auth-nav">
    <a href="/" class="brand" aria-label="返回一勺热点首页">
      <svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="#2868ed" stroke-width="2.4" stroke-linecap="round"><ellipse cx="15" cy="14" rx="6" ry="8" transform="rotate(36 15 14)"/><path d="M19.5 20.5 31 35"/></g><circle cx="33" cy="11" r="3" fill="#2868ed"/><circle cx="36" cy="21" r="1.6" fill="#8db8fa"/><circle cx="26" cy="5" r="1.3" fill="#b7d2fa"/></svg>
      <span class="wordmark">一勺热点<small>SPOONBRIEF</small></span>
    </a>
    <nav class="nav-links">
      <a href="/" class="muted">返回首页</a>
    </nav>
  </header>
    <div class="card auth-card">
      <div style="text-align: center; margin-bottom: 22px">
        <h2>{{ resetMode ? '找回密码' : '登录一勺热点' }}</h2>
        <p v-if="resetMode" class="muted" style="margin-top: 8px">通过注册邮箱验证码重置密码</p>
        <p v-else class="muted" style="margin-top: 8px">使用已有账号继续管理订阅和简报</p>
      </div>

      <!-- 忘记密码 -->
      <template v-if="resetMode">
        <label class="field">
          <span>注册邮箱</span>
          <div style="display: flex; gap: 8px">
            <input v-model="resetEmail" class="input" placeholder="you@example.com" />
            <button class="btn btn-outline" style="flex-shrink: 0" :disabled="resetSending || resetCountdown > 0" @click="sendResetCode">
              {{ resetCountdown > 0 ? `${resetCountdown}s` : '发送验证码' }}
            </button>
          </div>
        </label>
        <label class="field">
          <span>邮箱验证码</span>
          <input v-model="resetCode" class="input" placeholder="6 位验证码" maxlength="6" />
        </label>
        <label class="field">
          <span>新密码（至少 8 位，含字母和数字）</span>
          <input v-model="resetPassword" type="password" class="input" placeholder="设置新密码" @keyup.enter="doReset" />
        </label>
        <p v-if="resetError" class="form-error">{{ resetError }}</p>
        <button class="btn btn-primary btn-block" :disabled="loading" @click="doReset">
          <span v-if="loading" class="spinner"></span> 重置密码
        </button>
        <p class="muted" style="text-align: center; margin-top: 16px">
          <button class="footer-link-btn" type="button" @click="resetMode = false">← 返回登录</button>
        </p>
      </template>

      <!-- 登录 -->
      <template v-else>
        <label class="field">
          <span>账号</span>
          <input v-model="account" class="input" placeholder="邮箱或昵称" @keyup.enter="doLogin" />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" @keyup.enter="doLogin" />
        </label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="btn btn-primary btn-block" style="margin-top: 6px" :disabled="loading" @click="doLogin">
          <span v-if="loading" class="spinner"></span> 登录
        </button>
        <p class="muted" style="text-align: center; margin-top: 16px">
          <button class="footer-link-btn" type="button" @click="resetMode = true">忘记密码？</button>
          &nbsp;·&nbsp;还没有账号？
          <router-link to="/register">免费注册</router-link>
        </p>
      </template>
    </div>
    <SiteFooter compact />
  </div>
</template>

<style scoped>
.footer-link-btn {
  border: none;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: inherit;
  color: var(--primary);
  padding: 0;
}
.auth-nav .brand { display:flex;align-items:center;gap:11px;font-weight:650;color:var(--ink,#18304a);font-size:16px; }
.auth-nav .wordmark { line-height:1.35; }
.auth-nav .wordmark small { display:block;color:#72849b;font-size:10px;letter-spacing:.15em;font-weight:400;margin-top:2px; }
.auth-card h2 { margin:0; }
</style>
