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

// t158: detect deploy changes without discarding unsaved form data.
const buildVersion = 't160-20261122-email'
let updateNotice
async function checkBuild() {
 try {
  const r = await fetch('/app-version.json', { cache: 'no-store' })
  const v = await r.json()
  if (v.version && v.version !== buildVersion && !updateNotice) {
   updateNotice = document.createElement('div')
   updateNotice.setAttribute('role', 'status')
   Object.assign(updateNotice.style, {position:'fixed',bottom:'16px',left:'16px',right:'16px',zIndex:9999,padding:'14px',background:'#eef5ff',border:'1px solid #2868ed',borderRadius:'14px',color:'#18304a'})
   updateNotice.append(document.createTextNode('页面有新版本。请先保存当前修改，再刷新。 '))
   const button = document.createElement('button'); button.className = 'btn btn-primary'; button.textContent = '刷新到新版'
   button.onclick = () => location.reload(); updateNotice.append(button); document.body.append(updateNotice)
  }
 } catch (_) { /* Offline is not an authentication failure. */ }
}
window.addEventListener('pageshow', checkBuild)
document.addEventListener('visibilitychange', () => { if (!document.hidden) checkBuild() })
checkBuild()
