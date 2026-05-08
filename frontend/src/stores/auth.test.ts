import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api', () => ({
  api: {
    auth: {
      login: vi.fn(),
      me: vi.fn(),
    },
  },
}))

import { api } from '@/api'

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('initializes with empty state when no localStorage', () => {
    const store = useAuthStore()
    expect(store.token).toBe('')
    expect(store.username).toBe('')
    expect(store.isLoggedIn).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('restores state from localStorage', () => {
    localStorage.setItem('auth_token', 'test-jwt')
    localStorage.setItem('auth_user', 'admin')
    localStorage.setItem('auth_role', 'admin')
    setActivePinia(createPinia())
    const store = useAuthStore()
    expect(store.token).toBe('test-jwt')
    expect(store.username).toBe('admin')
    expect(store.isLoggedIn).toBe(true)
    expect(store.isAdmin).toBe(true)
  })

  it('login sets auth state and localStorage', async () => {
    const mockRes = { token: 'jwt-123', username: 'trader', role: 'user' }
    vi.mocked(api.auth.login).mockResolvedValue(mockRes)
    const store = useAuthStore()
    const res = await store.login('trader', 'pass')
    expect(res).toEqual(mockRes)
    expect(store.token).toBe('jwt-123')
    expect(store.username).toBe('trader')
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('auth_token')).toBe('jwt-123')
  })

  it('login sets error on failure', async () => {
    vi.mocked(api.auth.login).mockRejectedValue(new Error('Invalid credentials'))
    const store = useAuthStore()
    await expect(store.login('bad', 'creds')).rejects.toThrow('Invalid credentials')
    expect(store.error).toBe('Invalid credentials')
    expect(store.isLoggedIn).toBe(false)
  })

  it('logout clears auth state and localStorage', async () => {
    vi.mocked(api.auth.login).mockResolvedValue({ token: 'jwt', username: 'u', role: 'user' })
    const store = useAuthStore()
    await store.login('u', 'p')
    expect(store.isLoggedIn).toBe(true)
    store.logout()
    expect(store.token).toBe('')
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('checkAuth returns true and updates user on success', async () => {
    localStorage.setItem('auth_token', 'jwt')
    setActivePinia(createPinia())
    vi.mocked(api.auth.me).mockResolvedValue({ username: 'admin2', role: 'admin' })
    const store = useAuthStore()
    const result = await store.checkAuth()
    expect(result).toBe(true)
    expect(store.username).toBe('admin2')
    expect(store.isAdmin).toBe(true)
  })

  it('checkAuth returns false and clears auth on failure', async () => {
    localStorage.setItem('auth_token', 'bad-jwt')
    setActivePinia(createPinia())
    vi.mocked(api.auth.me).mockRejectedValue(new Error('Unauthorized'))
    const store = useAuthStore()
    const result = await store.checkAuth()
    expect(result).toBe(false)
    expect(store.token).toBe('')
  })
})
