import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/admin', () => ({
  fetchAdminStats: vi.fn(),
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  setUserStatus: vi.fn(),
  resetUserPassword: vi.fn(),
  fetchRoleOverview: vi.fn(),
  listAuditLogs: vi.fn(),
}))

import { listUsers } from '@/api/admin'
import UsersView from '@/views/admin/UsersView.vue'
import { useAuthStore } from '@/stores/auth'

const USERS = [
  {
    id: 2,
    username: 'teacher1',
    email: 'teacher1@example.com',
    role: 'teacher',
    status: 'active',
    permissions: ['course:create'],
    created_at: '2026-10-20T08:00:00Z',
    last_login_at: '2026-10-23T09:30:00Z',
  },
  {
    id: 3,
    username: 'student1',
    email: null,
    role: 'student',
    status: 'disabled',
    permissions: ['qa:ask'],
    created_at: '2026-10-21T08:00:00Z',
    last_login_at: null,
  },
]

async function mountUsers() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.token = 'token'
  auth.user = { id: 1, username: 'admin', role: 'admin' }

  const wrapper = mount(UsersView, {
    global: {
      plugins: [pinia, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('AdminUsersView', () => {
  beforeEach(() => {
    listUsers.mockReset()
    listUsers.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: { items: USERS, total: 2, page: 1, page_size: 10 },
    })
  })

  it('renders users with role, status and contact details', async () => {
    const wrapper = await mountUsers()

    expect(listUsers).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 10 }),
    )
    const text = wrapper.text()
    expect(text).toContain('teacher1')
    expect(text).toContain('teacher1@example.com')
    expect(text).toContain('教师')
    expect(text).toContain('启用')
    expect(text).toContain('student1')
    expect(text).toContain('未设置邮箱')
    expect(text).toContain('禁用')
    expect(text).toContain('创建用户')
  })

  it('reloads from the first page when searching', async () => {
    const wrapper = await mountUsers()
    listUsers.mockClear()

    await wrapper.find('input[placeholder="搜索用户名或邮箱"]').setValue('ali')
    const searchButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '查询')
    await searchButton.trigger('click')
    await flushPromises()

    expect(listUsers).toHaveBeenCalledTimes(1)
    expect(listUsers).toHaveBeenLastCalledWith(
      expect.objectContaining({ keyword: 'ali', page: 1 }),
    )
  })
})
