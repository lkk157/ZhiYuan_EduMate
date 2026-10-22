import { describe, expect, it } from 'vitest'

import { homePathForRole, menuForRole, roleLabel } from '@/utils/roles'

describe('role helpers', () => {
  it('maps each role to its home path', () => {
    expect(homePathForRole('student')).toBe('/student/home')
    expect(homePathForRole('teacher')).toBe('/teacher/home')
    expect(homePathForRole('admin')).toBe('/admin/home')
    expect(homePathForRole('unknown')).toBe('/login')
  })

  it('returns role-specific menus', () => {
    expect(menuForRole('student').map((item) => item.label)).toContain('AI 学伴问答')
    expect(menuForRole('teacher').map((item) => item.label)).toContain('资料上传')
    expect(menuForRole('admin').map((item) => item.label)).toContain('审计日志')
    expect(menuForRole('unknown')).toEqual([])
  })

  it('labels roles in Chinese', () => {
    expect(roleLabel('student')).toBe('学生')
    expect(roleLabel('teacher')).toBe('教师')
    expect(roleLabel('admin')).toBe('管理员')
    expect(roleLabel()).toBe('用户')
  })
})
