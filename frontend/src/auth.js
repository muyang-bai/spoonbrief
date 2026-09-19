import { reactive } from 'vue'
import { getToken, getUser, setToken, setUser, logout } from './api'

// 全局登录状态（简单响应式存储）
const initialUser = getUser()

export const auth = reactive({
  token: getToken(),
  user: initialUser,
  isAdmin: !!initialUser && initialUser.role === 'admin',
  isLoggedIn: !!getToken(),
})

export function setLogin(token, user) {
  setToken(token)
  setUser(user)
  auth.token = token
  auth.user = user
  auth.isAdmin = !!(user && user.role === 'admin')
  auth.isLoggedIn = !!token
}

export function doLogout() {
  logout()
  auth.token = ''
  auth.user = null
  auth.isAdmin = false
  auth.isLoggedIn = false
}
