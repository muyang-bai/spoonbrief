import { createRouter, createWebHistory } from 'vue-router'
import { auth } from './auth'

const routes = [
  { path: '/', name: 'landing', beforeEnter: () => { window.location.replace('/'); return false } },
  { path: '/login', name: 'login', component: () => import('./views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('./views/Register.vue') },
  { path: '/privacy', name: 'privacy', component: () => import('./views/Privacy.vue'), meta: { title: '隐私政策' } },
  { path: '/unsubscribe-help', name: 'unsubscribe-help', component: () => import('./views/UnsubscribeHelp.vue'), meta: { title: '退订说明' } },
  {
    path: '/dashboard',
    component: () => import('./views/Dashboard.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard/subscriptions' },
      { path: 'subscriptions', name: 'subscriptions', component: () => import('./views/Subscriptions.vue'), meta: { title: '订阅管理' } },
      { path: 'reports', name: 'reports', component: () => import('./views/Reports.vue'), meta: { title: '历史报告' } },
      { path: 'sources', name: 'sources', component: () => import('./views/Sources.vue'), meta: { title: '信息源' } },
      { path: 'emails', name: 'emails', component: () => import('./views/Emails.vue'), meta: { title: '收件邮箱' } },
      { path: 'profile', name: 'profile', component: () => import('./views/Profile.vue'), meta: { title: '我的画像' } },
      { path: 'prompts', name: 'prompts', component: () => import('./views/Prompts.vue'), meta: { title: '分析模板' } },
      { path: 'api-keys', name: 'apikeys', component: () => import('./views/ApiKeys.vue'), meta: { title: 'AI 额度用量' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('./views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('./views/admin/Dashboard.vue'), meta: { title: '数据面板' } },
      { path: 'users', name: 'admin-users', component: () => import('./views/admin/Users.vue'), meta: { title: '用户管理' } },
      { path: 'smtp', name: 'admin-smtp', component: () => import('./views/admin/Smtp.vue'), meta: { title: 'SMTP 邮件' } },
      { path: 'ai-config', name: 'admin-aiconfig', component: () => import('./views/admin/AiConfig.vue'), meta: { title: 'AI 接口' } },
      { path: 'token-stats', name: 'admin-tokenstats', component: () => import('./views/admin/TokenStats.vue'), meta: { title: 'AI 用量' } },
      { path: 'sources', name: 'admin-sources', component: () => import('./views/admin/Sources.vue'), meta: { title: '信息源管理' } },
      { path: 'prompts', name: 'admin-prompts', component: () => import('./views/admin/Prompts.vue'), meta: { title: '官方模板' } },
      { path: 'announcements', name: 'admin-announcements', component: () => import('./views/admin/Announcements.vue'), meta: { title: '公告管理' } },
      { path: 'compliance', name: 'admin-compliance', component: () => import('./views/admin/Compliance.vue'), meta: { title: '合规文本' } },
      { path: 'register-toggle', name: 'admin-regtoggle', component: () => import('./views/admin/RegisterToggle.vue'), meta: { title: '注册开关' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  // 命名对照表：一勺热点 SpoonBrief · 页面名
  document.title = '一勺热点 SpoonBrief' + (to.meta.title ? ' · ' + to.meta.title : '')
  // 已登录用户访问登录/注册页 → 自动跳转控制台
  if ((to.name === 'login' || to.name === 'register') && auth.isLoggedIn) return '/dashboard/subscriptions'
  if (to.meta.requiresAuth && !auth.isLoggedIn) return '/login'
  if (to.meta.requiresAdmin && !auth.isAdmin) return '/dashboard/subscriptions'
  return true
})

export default router
