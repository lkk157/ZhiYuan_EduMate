import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/auth', () => ({
  login: vi.fn(async () => ({
    code: 0,
    message: 'ok',
    data: {
      access_token: 'token-123',
      user: { id: 1, username: 'student1', role: 'student' },
    },
  })),
  register: vi.fn(async () => ({
    code: 0,
    message: '注册成功',
    data: {
      access_token: 'register-token',
      user: { id: 2, username: 'newstudent', role: 'student' },
    },
  })),
  fetchMe: vi.fn(async () => ({
    code: 0,
    message: 'ok',
    data: { id: 1, username: 'student1', role: 'student' },
  })),
}))

import { useAuthStore } from '@/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('persists token and user after login', async () => {
    const auth = useAuthStore()

    const user = await auth.login({ username: 'student1', password: 'secret123' })

    expect(user.role).toBe('student')
    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem('edumate_token')).toBe('token-123')
    expect(JSON.parse(localStorage.getItem('edumate_user')).username).toBe('student1')
  })

  it('persists token and user after registration', async () => {
    const auth = useAuthStore()

    const user = await auth.register({
      username: 'newstudent',
      password: 'NewSecret123!',
      password_confirm: 'NewSecret123!',
    })

    expect(user.role).toBe('student')
    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem('edumate_token')).toBe('register-token')
    expect(JSON.parse(localStorage.getItem('edumate_user')).username).toBe('newstudent')
  })

  it('clears state and storage on logout', () => {
    localStorage.setItem('edumate_token', 'token-123')
    localStorage.setItem('edumate_user', JSON.stringify({ username: 'admin', role: 'admin' }))
    const auth = useAuthStore()

    auth.logout()

    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('edumate_token')).toBeNull()
    expect(localStorage.getItem('edumate_user')).toBeNull()
  })
})
