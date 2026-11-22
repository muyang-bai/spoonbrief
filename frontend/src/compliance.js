// 合规信息（t110 · M2）：库里还是「请填写…」占位时，用这里的兜底值
export const ICP_RECORD = '蜀ICP备2026011042号-2'
export const ICP_URL = 'https://beian.miit.gov.cn/'

export function effectiveText(value, fallback = '') {
  const t = typeof value === 'string' ? value.trim() : ''
  return !t || /^请填写/.test(t) ? fallback : t
}
