import { describe, expect, it, vi } from 'vitest'
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
    ],
  })
  await router.push('/')
  await router.isReady()

  return mount(LoginView, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
}

describe('LoginView', () => {
  it('renders the login form', async () => {
    const wrapper = await mountLogin()

    expect(wrapper.text()).toContain('欢迎回来')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
    expect(wrapper.find('input[autocomplete="current-password"]').exists()).toBe(true)
    expect(wrapper.find('button.login-submit').exists()).toBe(true)
  })

  it('blocks submission when credentials are empty', async () => {
    login.mockClear()
    const wrapper = await mountLogin()
    const auth = useAuthStore()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).not.toHaveBeenCalled()
    expect(auth.isAuthenticated).toBe(false)
  })
})
