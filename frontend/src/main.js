import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

createApp(App).use(router).mount('#app')

/* 全局波纹微交互（克制：仅在支持动效的设备上启用） */
const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
if (!reduceMotion) {
  document.addEventListener('pointerdown', (e) => {
    const btn = e.target.closest('.btn, .tag-chip, .hot-chip, .nav-item, .side-switch, .tab, .seg-btn')
    if (!btn || btn.disabled) return
    const rect = btn.getBoundingClientRect()
    const d = Math.max(rect.width, rect.height) * 2
    const s = document.createElement('span')
    s.className = 'ripple'
    s.style.width = s.style.height = `${d}px`
    s.style.left = `${e.clientX - rect.left - d / 2}px`
    s.style.top = `${e.clientY - rect.top - d / 2}px`
    btn.appendChild(s)
    setTimeout(() => s.remove(), 600)
  })
}
