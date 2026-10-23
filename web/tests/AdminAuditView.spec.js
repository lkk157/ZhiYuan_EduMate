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

import { listAuditLogs } from '@/api/admin'
import AuditView from '@/views/admin/AuditView.vue'

async function mountAudit() {
  const wrapper = mount(AuditView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('AdminAuditView', () => {
  beforeEach(() => {
    listAuditLogs.mockReset()
    listAuditLogs.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: {
        items: [
          {
            id: 12,
            user_id: 1,
            username: 'admin',
            action: 'user.disable',
            target_type: 'user',
            target_id: '3',
            detail: { username: 'teacher1', status: 'disabled' },
            ip: '127.0.0.1',
            status: 'success',
            created_at: '2026-10-23T09:30:00Z',
          },
          {
            id: 11,
            user_id: null,
            username: 'intruder',
            action: 'auth.login.failed',
            target_type: 'user',
            target_id: null,
            detail: { reason: '用户名或密码错误' },
            ip: '127.0.0.1',
            status: 'failure',
            created_at: '2026-10-23T09:20:00Z',
          },
        ],
        total: 2,
        page: 1,
        page_size: 20,
      },
    })
  })

  it('renders audit entries, actors, status and redacted details', async () => {
    const wrapper = await mountAudit()

    const text = wrapper.text()
    expect(text).toContain('审计日志')
    expect(text).toContain('禁用用户')
    expect(text).toContain('登录失败')
    expect(text).toContain('admin')
    expect(text).toContain('intruder')
    expect(text).toContain('teacher1')
    expect(text).toContain('成功')
    expect(text).toContain('失败')
    expect(text).toContain('127.0.0.1')
    expect(text).toContain('用户名或密码错误')
    expect(text).toContain('条记录')
  })
})
