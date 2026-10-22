import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import MainLayout from '@/layouts/MainLayout.vue'
import { useAuthStore } from '@/stores/auth'

async function mountLayout(role) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.token = 'token'
  auth.user = { id: 1, username: role === 'admin' ? '管理员' : '测试用户', role }

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()

  return mount(MainLayout, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
}

describe('MainLayout', () => {
  it('renders admin navigation and role identity', async () => {
    const wrapper = await mountLayout('admin')

    expect(wrapper.text()).toContain('用户管理')
    expect(wrapper.text()).toContain('审计日志')
    expect(wrapper.text()).toContain('管理员')
    expect(wrapper.text()).toContain('管理员空间')
  })

  it('renders student navigation without admin entries', async () => {
    const wrapper = await mountLayout('student')

    expect(wrapper.text()).toContain('AI 学伴问答')
    expect(wrapper.text()).toContain('问答记录')
    expect(wrapper.text()).not.toContain('用户管理')
  })
})
