import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
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

import { fetchRoleOverview } from '@/api/admin'
import RolesView from '@/views/admin/RolesView.vue'

async function mountRoles() {
  const wrapper = mount(RolesView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('AdminRolesView', () => {
  beforeEach(() => {
    fetchRoleOverview.mockReset()
    fetchRoleOverview.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: {
        roles: [
          {
            id: 1,
            name: 'admin',
            description: '系统管理员，拥有全部治理权限',
            user_count: 1,
            permissions: ['user:manage', 'course:review'],
          },
          {
            id: 2,
            name: 'teacher',
            description: '教师，负责课程、资料与学情',
            user_count: 2,
            permissions: ['course:review'],
          },
          {
            id: 3,
            name: 'student',
            description: '学生，进行学习、问答与练习',
            user_count: 5,
            permissions: [],
          },
        ],
        permissions: [
          {
            code: 'user:manage',
            name: '用户管理',
            description: '创建、编辑、禁用用户与分配角色',
          },
          {
            code: 'course:review',
            name: '课程审核',
            description: '审核教师提交的课程',
          },
        ],
      },
    })
  })

  it('renders role cards and the permission matrix', async () => {
    const wrapper = await mountRoles()

    const text = wrapper.text()
    expect(text).toContain('角色权限')
    expect(text).toContain('系统管理员')
    expect(text).toContain('教师')
    expect(text).toContain('学生')
    expect(text).toContain('用户管理')
    expect(text).toContain('course:review')
    expect(text).toContain('创建、编辑、禁用用户与分配角色')

    expect(wrapper.findAll('.perm-yes').length).toBe(3)
    expect(wrapper.find('.matrix-card').exists()).toBe(true)
    expect(wrapper.find('.matrix-scroll').exists()).toBe(true)
    expect(wrapper.find('.matrix-table').exists()).toBe(true)
  })
})
