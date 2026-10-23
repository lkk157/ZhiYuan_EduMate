import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import AuthLayout from '@/layouts/AuthLayout.vue'
import LoginView from '@/views/LoginView.vue'

describe('AuthLayout', () => {
  it('renders the child route inside the auth panel', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/login',
          component: AuthLayout,
          children: [{ path: '', component: LoginView }],
        },
      ],
    })
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(AuthLayout, {
      global: {
        plugins: [createPinia(), router, ElementPlus],
        components: { ...ElementPlusIcons },
      },
    })

    expect(wrapper.find('.auth-panel-inner').text()).toContain('欢迎回来')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
  })
})
