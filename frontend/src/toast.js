import { reactive } from 'vue'

// 全局轻量提示（toast）
export const toasts = reactive([])
let seq = 0

export function toast(message, type = 'success', duration = 3200) {
  const id = ++seq
  toasts.push({ id, message, type })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, duration)
}

export const t = {
  ok: (m) => toast(m, 'success'),
  err: (m) => toast(m || '操作失败，请稍后重试', 'error', 4200),
  info: (m) => toast(m, 'info', 4200),
}
