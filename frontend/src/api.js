// 统一 API 客户端（fetch 封装）
const API_BASE = '/api/v1'

export function getToken() {
  return localStorage.getItem('hb_token') || ''
}

export function setToken(token) {
  if (token) localStorage.setItem('hb_token', token)
  else localStorage.removeItem('hb_token')
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem('hb_user') || 'null')
  } catch {
    return null
  }
}

export function setUser(user) {
  if (user) localStorage.setItem('hb_user', JSON.stringify(user))
  else localStorage.removeItem('hb_user')
}

export function logout() {
  setToken('')
  setUser(null)
}

export async function api(path, { method = 'GET', body, params, timeout = 30000, headers: extraHeaders = {} } = {}) {
  let url = API_BASE + path
  if (params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v)
    }
    const s = qs.toString()
    if (s) url += '?' + s
  }

  const headers = { ...extraHeaders }
  if (body !== undefined && body !== null) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers['Authorization'] = 'Bearer ' + token

  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeout)

  let res
  try {
    res = await fetch(url, {
      method,
      cache: 'no-store',
      headers,
      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
  } catch (e) {
    clearTimeout(timer)
    if (e.name === 'AbortError') throw new Error('请求超时，请检查网络或稍后重试')
    throw new Error('网络错误，请检查连接')
  }
  clearTimeout(timer)

  let data = {}
  try {
    data = await res.json()
  } catch {
    /* 空响应 */
  }

  if (!res.ok) {
    const detail = typeof data === 'object' && data !== null
      ? (data.detail || data.message || `请求失败 (${res.status})`)
      : `请求失败 (${res.status})`
    const message = Array.isArray(detail) ? detail.map(item => `${(item.loc || []).slice(1).join('.')}: ${item.msg || '输入无效'}`).join('；') : String(detail)
    if (res.status === 401 && !path.startsWith('/auth/')) {
      logout()
      if (!location.pathname.startsWith('/login')) location.href = '/login'
    }
    const error = new Error(message)
    error.status = res.status
    throw error
  }
  return data
}
