import { reactive } from 'vue'

export const confirmState = reactive({ show: false, title: '请确认', text: '', okText: '确认删除', danger: true })
let resolver = null

export function confirmDialog(opts = {}) {
  confirmState.title = opts.title || '请确认'
  confirmState.text = opts.text || ''
  confirmState.okText = opts.okText || '确认删除'
  confirmState.danger = opts.danger !== false
  confirmState.show = true
  return new Promise((resolve) => { resolver = resolve })
}

export function settleConfirm(value) {
  confirmState.show = false
  const fn = resolver
  resolver = null
  if (fn) fn(!!value)
}
