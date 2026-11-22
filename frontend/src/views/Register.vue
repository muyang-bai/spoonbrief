<script setup>
import SiteFooter from '../components/SiteFooter.vue'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { setLogin } from '../auth'
import { t } from '../toast'

const router = useRouter()
const email = ref('')
const code = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)

const emailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))
const nicknameValid = computed(() => /^[a-zA-Z\u4e00-\u9fff-]{2,20}$/.test(nickname.value))
const passwordValid = computed(() => password.value.length >= 8 && /[a-zA-Z]/.test(password.value) && /\d/.test(password.value))

let timer = null

async function sendCode() {
  error.value = ''
  if (!emailValid.value) {
    error.value = '请输入正确的邮箱地址'
    return
  }
  sending.value = true
  try {
    await api('/auth/send-code', { method: 'POST', body: { email: email.value } })
    t.ok('验证码已提交发送，请查收邮箱（5 分钟内有效）')
    countdown.value = 60
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

async function doRegister() {
  error.value = ''
  if (!emailValid.value) return (error.value = '请输入正确的邮箱地址')
  if (!code.value) return (error.value = '请输入邮箱验证码')
  if (!nicknameValid.value) return (error.value = '昵称需 2-20 位，仅允许字母、连字符、中文')
  if (!passwordValid.value) return (error.value = '密码需至少 8 位且同时包含字母与数字')
  if (password.value !== confirmPassword.value) return (error.value = '两次输入的密码不一致')

  loading.value = true
  try {
    const res = await api('/auth/register', {
      method: 'POST',
      body: { email: email.value, code: code.value, nickname: nickname.value, password: password.value },
    })
    setLogin(res.access_token, res.user)
    t.ok('注册成功，欢迎加入')
    router.push('/dashboard/subscriptions')
  } catch (e) {
    error.value = e.message
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
        <h2>创建你的账户</h2>
        <p class="muted" style="margin-top: 8px">注册后即可设置关注方向，把简报送到邮箱</p>
      </div>

      <label class="field">
        <span>邮箱地址</span>
        <div style="display: flex; gap: 8px">
          <input v-model="email" class="input" placeholder="you@example.com" />
          <button class="btn btn-outline" style="flex-shrink: 0" :disabled="sending || countdown > 0" @click="sendCode">
            {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
          </button>
        </div>
      </label>
      <label class="field">
        <span>邮箱验证码</span>
        <input v-model="code" class="input" placeholder="6 位验证码" maxlength="6" />
      </label>
      <label class="field">
        <span>昵称（2-20 位，字母/中文/连字符）</span>
        <input v-model="nickname" class="input" placeholder="你的昵称" />
      </label>
      <label class="field">
        <span>密码（至少 8 位，含字母和数字）</span>
        <input v-model="password" type="password" class="input" placeholder="设置密码" />
      </label>
      <label class="field">
        <span>确认密码</span>
        <input v-model="confirmPassword" type="password" class="input" placeholder="再次输入密码" @keyup.enter="doRegister" />
      </label>

      <p v-if="error" class="form-error">{{ error }}</p>
      <button class="btn btn-primary btn-block" :disabled="loading" @click="doRegister">
        <span v-if="loading" class="spinner"></span> 注册并进入
      </button>
      <p class="muted" style="text-align: center; margin-top: 16px">
        已有账号？
        <router-link to="/login">直接登录</router-link>
      </p>
      <p class="muted" style="text-align: center; margin-top: 12px; font-size: 12.5px">注册即表示你已阅读并同意<router-link to="/privacy">《隐私政策》</router-link></p>
    </div>
    <SiteFooter compact />
  </div>
</template>

<style scoped>
.auth-nav .brand { display:flex;align-items:center;gap:11px;font-weight:650;color:var(--ink,#18304a);font-size:16px; }
.auth-nav .wordmark { line-height:1.35; }
.auth-nav .wordmark small { display:block;color:#72849b;font-size:10px;letter-spacing:.15em;font-weight:400;margin-top:2px; }
.auth-card h2 { margin:0; }
</style>
