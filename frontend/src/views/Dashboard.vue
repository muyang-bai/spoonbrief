<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, doLogout, setLogin } from '../auth'
import { api } from '../api'
import SiteFooter from '../components/SiteFooter.vue'

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const sideOpen = ref(false)   // 移动端侧边栏抽屉

// 站内公告（用户端横幅展示，支持单条关闭并记住）
const DISMISS_KEY = 'hmb_dismissed_announcements'
const announcements = ref([])

function loadAnnouncements() {
  api('/announcements/')
    .then((list) => {
      let dismissed = []
      try { dismissed = JSON.parse(localStorage.getItem(DISMISS_KEY) || '[]') } catch (e) { dismissed = [] }
      const set = new Set(dismissed)
      announcements.value = (list || []).filter((a) => !set.has(a.id))
    })
    .catch(() => {})
}

function dismissAnn(id) {
  announcements.value = announcements.value.filter((a) => a.id !== id)
  let dismissed = []
  try { dismissed = JSON.parse(localStorage.getItem(DISMISS_KEY) || '[]') } catch (e) { dismissed = [] }
  dismissed.push(id)
  localStorage.setItem(DISMISS_KEY, JSON.stringify([...new Set(dismissed)]))
}

onMounted(() => { loadAnnouncements(); api('/profile/').then(({id,email,nickname,role}) => setLogin(auth.token, {id,email,nickname,role})).catch(() => {}) })

watch(() => route.path, () => { sideOpen.value = false })

const navItems = [
  { to: '/dashboard/subscriptions', label: '订阅管理' },
  { to: '/dashboard/reports', label: '历史报告' },
  { to: '/dashboard/sources', label: '信息源' },
  { to: '/dashboard/emails', label: '收件邮箱' },
  { to: '/dashboard/profile', label: '我的画像' },
  { to: '/dashboard/prompts', label: '分析模板' },
  { to: '/dashboard/api-keys', label: '积分用量' },
]

function logout() {
  doLogout()
  router.push('/')
}

function initial() {
  const n = auth.user?.nickname || '用'
  return n.slice(0, 1).toUpperCase()
}
</script>

<template>
  <div class="app-shell user-dashboard">
    <div v-if="sideOpen" class="side-overlay" @click="sideOpen = false"></div>
    <aside class="sidebar" :class="{ open: sideOpen }">
      <a href="/" class="brand" aria-label="一勺热点首页">
        <svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="#2868ed" stroke-width="2.4" stroke-linecap="round"><ellipse cx="15" cy="14" rx="6" ry="8" transform="rotate(36 15 14)"/><path d="M19.5 20.5 31 35"/></g><circle cx="33" cy="11" r="3" fill="#2868ed"/><circle cx="36" cy="21" r="1.6" fill="#8db8fa"/><circle cx="26" cy="5" r="1.3" fill="#b7d2fa"/></svg>
        <span class="wordmark">一勺热点<small>SPOONBRIEF</small></span>
      </a>

      <div class="nav-group-label">控制台</div>
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item" active-class="active">
        {{ item.label }}
      </router-link>

      <div class="spacer"></div>
      <router-link v-if="auth.isAdmin" to="/admin/dashboard" class="side-switch">切换到管理后台</router-link>
      <a href="/" class="nav-item">返回首页</a>
    </aside>

    <div class="main">
      <div class="topbar">
        <div style="display: flex; align-items: center; gap: 10px">
          <button class="hamburger" @click="sideOpen = true">☰</button>
          <h1>{{ $route.meta.title || '' }}</h1>
        </div>
        <div class="user-menu">
          <span class="muted">{{ auth.user?.nickname }}</span>
          <div class="dropdown">
            <button class="avatar" style="border: none; cursor: pointer" @click="menuOpen = !menuOpen">{{ initial() }}</button>
            <div v-if="menuOpen" class="dropdown-menu" @click="menuOpen = false">
              <button @click="router.push('/dashboard/profile')">我的画像</button>
              <button @click="router.push('/dashboard/api-keys')">积分用量</button>
              <button style="color: var(--danger)" @click="logout">退出登录</button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="announcements.length" class="ann-list">
        <div v-for="a in announcements" :key="a.id" class="ann-card">
          <div class="ann-head">
            <span class="ann-tag">公告</span>
            <strong>{{ a.title }}</strong>
            <span v-if="a.is_pinned" class="ann-pin">置顶</span>
            <button class="ann-close" title="关闭此公告" @click="dismissAnn(a.id)">✕</button>
          </div>
          <p class="ann-body">{{ a.body }}</p>
        </div>
      </div>
      <router-view />
      <SiteFooter />
    </div>
  </div>
</template>

<style scoped>
.ann-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.ann-card {
  background: #fff;
  border: 1px solid #dde8f5;
  border-left: 4px solid #2868ed;
  border-radius: 16px;
  padding: 12px 14px;
}
.ann-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #18304a;
}
.ann-tag {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: #2868ed;
  border-radius: 4px;
  padding: 1px 7px;
  letter-spacing: .08em;
}
.ann-pin {
  font-size: 11px;
  background: #2868ed;
  color: #fff;
  border-radius: 4px;
  padding: 1px 6px;
}
.ann-close {
  margin-left: auto;
  border: none;
  background: none;
  cursor: pointer;
  color: #9ca3af;
  font-size: 14px;
  line-height: 1;
  padding: 4px;
}
.ann-close:hover {
  color: #ef4444;
}
.ann-body {
  margin: 6px 0 0;
  font-size: 14px;
  color: #60748a;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
