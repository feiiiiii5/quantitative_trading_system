import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || '')
  const username = ref(localStorage.getItem('auth_user') || '')
  const role = ref(localStorage.getItem('auth_role') || '')
  const error = ref('')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  function setAuth(data: { token: string; username: string; role: string }) {
    token.value = data.token
    username.value = data.username
    role.value = data.role
    error.value = ''
    localStorage.setItem('auth_token', data.token)
    localStorage.setItem('auth_user', data.username)
    localStorage.setItem('auth_role', data.role)
  }

  function clearAuth() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_role')
  }

  async function login(user: string, password: string) {
    error.value = ''
    try {
      const res = await api.auth.login(user, password)
      if (res) {
        setAuth(res)
      }
      return res
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '登录失败'
      throw e
    }
  }

  function logout() {
    clearAuth()
  }

  async function checkAuth() {
    if (!token.value) return false
    try {
      const res = await api.auth.me()
      if (res) {
        username.value = res.username
        role.value = res.role
        return true
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '认证检查失败'
      clearAuth()
    }
    return false
  }

  return { token, username, role, error, isLoggedIn, isAdmin, login, logout, checkAuth }
})
