<script setup>
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
const nicknameValid = computed(() => /^[a-zA-Z\u4e00-\u9fff\-]{2,20}$/.test(nickname.value))
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
    t.ok('验证码已发送，请查收邮箱（5 分钟内有效）')
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
  <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px">
    <div class="card" style="width: 100%; max-width: 420px; padding: 32px">
      <div style="text-align: center; margin-bottom: 22px">
        <router-link to="/" title="返回首页">
          <img src="/favicon.svg" alt="logo" style="width: 52px; height: 52px; cursor: pointer" />
        </router-link>
        <h2 style="margin-top: 10px">创建你的账户</h2>
        <p class="muted" style="margin-top: 4px">免费注册，立即开启你的智能情报之旅</p>
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
    </div>
  </div>
</template>
