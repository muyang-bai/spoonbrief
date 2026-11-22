<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, doLogout } from '../../auth'

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const sideOpen = ref(false)   // 移动端侧边栏抽屉

watch(() => route.path, () => { sideOpen.value = false })

const adminItems = [
  { to: '/admin/dashboard', label: '数据面板' },
  { to: '/admin/users', label: '用户管理' },
  { to: '/admin/smtp', label: 'SMTP 邮件' },
  { to: '/admin/ai-config', label: 'AI 接口' },
  { to: '/admin/token-stats', label: 'AI 用量' },
  { to: '/admin/sources', label: '信息源管理' },
  { to: '/admin/prompts', label: '官方模板' },
  { to: '/admin/announcements', label: '公告管理' },
  { to: '/admin/compliance', label: '合规文本' },
  { to: '/admin/register-toggle', label: '注册开关' },
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
      <a href="/" class="brand" aria-label="一勺热点首页">
        <svg class="mark" viewBox="0 0 44 44" aria-hidden="true"><g fill="none" stroke="#2868ed" stroke-width="2.4" stroke-linecap="round"><ellipse cx="15" cy="14" rx="6" ry="8" transform="rotate(36 15 14)"/><path d="M19.5 20.5 31 35"/></g><circle cx="33" cy="11" r="3" fill="#2868ed"/><circle cx="36" cy="21" r="1.6" fill="#8db8fa"/><circle cx="26" cy="5" r="1.3" fill="#b7d2fa"/></svg>
        <span class="wordmark">一勺热点<small>SPOONBRIEF</small></span>
      </a>

      <div class="nav-group-label">管理后台</div>
      <router-link v-for="item in adminItems" :key="item.to" :to="item.to" class="nav-item" active-class="active">
        {{ item.label }}
      </router-link>

      <div class="spacer"></div>
      <router-link to="/dashboard/subscriptions" class="side-switch">切换到控制台</router-link>
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
              <button style="color: var(--danger)" @click="logout">退出登录</button>
            </div>
          </div>
        </div>
      </div>
      <router-view />
    </div>
  </div>
</template>
