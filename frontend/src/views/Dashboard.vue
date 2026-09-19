<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, doLogout } from '../auth'
import { api } from '../api'

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

onMounted(loadAnnouncements)

watch(() => route.path, () => { sideOpen.value = false })

const navItems = [
  { to: '/dashboard/subscriptions', label: '订阅管理' },
  { to: '/dashboard/reports', label: '历史报告' },
  { to: '/dashboard/sources', label: '信息源' },
  { to: '/dashboard/emails', label: '收件邮箱' },
  { to: '/dashboard/profile', label: '我的画像' },
  { to: '/dashboard/prompts', label: '分析模板' },
  { to: '/dashboard/api-keys', label: 'API Key' },
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
  <div class="app-shell">
    <div v-if="sideOpen" class="side-overlay" @click="sideOpen = false"></div>
    <aside class="sidebar" :class="{ open: sideOpen }">
      <router-link to="/" class="brand">
        <img src="/favicon.svg" alt="logo" />
        一勺热点
      </router-link>

      <div class="nav-group-label">控制台</div>
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item" active-class="active">
        {{ item.label }}
      </router-link>

      <div class="spacer"></div>
      <router-link v-if="auth.isAdmin" to="/admin/dashboard" class="side-switch">切换到管理后台</router-link>
      <router-link to="/" class="nav-item">返回首页</router-link>
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
              <button @click="router.push('/dashboard/api-keys')">API Key</button>
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
  background: linear-gradient(135deg, #fff7ed, #fffbeb);
  border: 1px solid #fed7aa;
  border-left: 4px solid #f97316;
  border-radius: 10px;
  padding: 12px 14px;
}
.ann-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #1f2937;
}
.ann-tag {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--primary, #f97316);
  border-radius: 4px;
  padding: 1px 7px;
  letter-spacing: .08em;
}
.ann-pin {
  font-size: 11px;
  background: #f97316;
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
  color: #4b5563;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
