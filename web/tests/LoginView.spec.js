import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  fetchMe: vi.fn(),
  changePassword: vi.fn(),
}))

import { login } from '@/api/auth'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

async function mountLogin() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: LoginView },
      { path: '/student/home', component: { template: '<div />' } },
      { path: '/teacher/home', component: { template: '<div />' } },
      { path: '/admin/home', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()

  const wrapper = mount(LoginView, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  return { wrapper, router }
}

describe('LoginView', () => {
  beforeEach(() => {
    login.mockReset()
    localStorage.clear()
  })

  it('renders the login form', async () => {
    const { wrapper } = await mountLogin()

    expect(wrapper.text()).toContain('欢迎回来')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
    expect(wrapper.find('input[autocomplete="current-password"]').exists()).toBe(true)
    expect(wrapper.find('button.login-submit').exists()).toBe(true)
  })

  it('blocks submission when credentials are empty', async () => {
    const { wrapper } = await mountLogin()
    const auth = useAuthStore()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).not.toHaveBeenCalled()
    expect(auth.isAuthenticated).toBe(false)
  })

  it('redirects to the role home after a successful login', async () => {
    login.mockResolvedValueOnce({
      code: 0,
      message: 'ok',
      data: {
        access_token: 'token-123',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 1,
          username: 'student1',
          role: 'student',
          status: 'active',
          permissions: ['qa:ask', 'exercise:answer'],
        },
      },
    })
    const { wrapper, router } = await mountLogin()
    const auth = useAuthStore()

    await wrapper.find('input[autocomplete="username"]').setValue('student1')
    await wrapper.find('input[autocomplete="current-password"]').setValue('Secret123!')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({
      username: 'student1',
      password: 'Secret123!',
    })
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.role).toBe('student')
    expect(router.currentRoute.value.path).toBe('/student/home')
  })
})
