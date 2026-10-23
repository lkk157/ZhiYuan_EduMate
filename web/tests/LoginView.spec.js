import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  fetchMe: vi.fn(),
  changePassword: vi.fn(),
}))

import { login, register } from '@/api/auth'
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

async function switchToRegister(wrapper) {
  const tab = wrapper
    .findAll('.auth-switch button')
    .find((button) => button.text() === '注册')
  await tab.trigger('click')
}

describe('LoginView', () => {
  beforeEach(() => {
    login.mockReset()
    register.mockReset()
    localStorage.clear()
  })

  it('renders login and registration tabs', async () => {
    const { wrapper } = await mountLogin()

    expect(wrapper.text()).toContain('欢迎回来')
    expect(wrapper.text()).toContain('注册')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
    expect(wrapper.find('input[autocomplete="current-password"]').exists()).toBe(true)
    expect(wrapper.find('button.login-submit').exists()).toBe(true)
  })

  it('switches to registration and shows email and confirm fields', async () => {
    const { wrapper } = await mountLogin()

    await switchToRegister(wrapper)

    expect(wrapper.text()).toContain('创建学生账号')
    expect(wrapper.find('input[autocomplete="email"]').exists()).toBe(true)
    expect(wrapper.findAll('input[autocomplete="new-password"]').length).toBe(2)
  })

  it('blocks login submission when credentials are empty', async () => {
    const { wrapper } = await mountLogin()
    const auth = useAuthStore()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).not.toHaveBeenCalled()
    expect(auth.isAuthenticated).toBe(false)
  })

  it('blocks registration when passwords do not match', async () => {
    const { wrapper } = await mountLogin()
    await switchToRegister(wrapper)

    await wrapper.find('input[autocomplete="username"]').setValue('newstudent')
    const passwordInputs = wrapper.findAll('input[autocomplete="new-password"]')
    await passwordInputs[0].setValue('NewSecret123!')
    await passwordInputs[1].setValue('Different123!')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(register).not.toHaveBeenCalled()
  })

  it('registers a student and redirects to the student home', async () => {
    register.mockResolvedValueOnce({
      code: 0,
      message: '注册成功',
      data: {
        access_token: 'register-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 4,
          username: 'newstudent',
          role: 'student',
          status: 'active',
          permissions: ['qa:ask', 'exercise:answer'],
        },
      },
    })
    const { wrapper, router } = await mountLogin()
    const auth = useAuthStore()

    await switchToRegister(wrapper)
    await wrapper.find('input[autocomplete="username"]').setValue('NewStudent')
    await wrapper.find('input[autocomplete="email"]').setValue('new@example.com')
    const passwordInputs = wrapper.findAll('input[autocomplete="new-password"]')
    await passwordInputs[0].setValue('NewSecret123!')
    await passwordInputs[1].setValue('NewSecret123!')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(register).toHaveBeenCalledWith({
      username: 'NewStudent',
      password: 'NewSecret123!',
      password_confirm: 'NewSecret123!',
      email: 'new@example.com',
    })
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.role).toBe('student')
    expect(router.currentRoute.value.path).toBe('/student/home')
  })

  it('allows registration without the optional email', async () => {
    register.mockResolvedValueOnce({
      code: 0,
      message: '注册成功',
      data: {
        access_token: 'register-token-2',
        user: {
          id: 5,
          username: 'noemail',
          role: 'student',
          status: 'active',
          permissions: ['qa:ask'],
        },
      },
    })
    const { wrapper, router } = await mountLogin()

    await switchToRegister(wrapper)
    await wrapper.find('input[autocomplete="username"]').setValue('noemail')
    const passwordInputs = wrapper.findAll('input[autocomplete="new-password"]')
    await passwordInputs[0].setValue('NewSecret123!')
    await passwordInputs[1].setValue('NewSecret123!')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(register).toHaveBeenCalledWith({
      username: 'noemail',
      password: 'NewSecret123!',
      password_confirm: 'NewSecret123!',
      email: null,
    })
    expect(router.currentRoute.value.path).toBe('/student/home')
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
