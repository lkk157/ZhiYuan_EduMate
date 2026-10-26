import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/course', () => ({
  listCourses: vi.fn(),
  createCourse: vi.fn(),
  updateCourse: vi.fn(),
  submitCourse: vi.fn(),
  getCourse: vi.fn(),
  reviewCourse: vi.fn(),
  joinCourse: vi.fn(),
  listCourseStudents: vi.fn(),
  addStudent: vi.fn(),
  removeStudent: vi.fn(),
  rotateInvite: vi.fn(),
  toggleInvite: vi.fn(),
  createChapter: vi.fn(),
  updateChapter: vi.fn(),
  deleteChapter: vi.fn(),
  createKnowledge: vi.fn(),
  updateKnowledge: vi.fn(),
  deleteKnowledge: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  listMaterials: vi.fn(),
}))

import { getCourse, listCourseStudents } from '@/api/course'
import { listMaterials } from '@/api/material'
import CourseEditorView from '@/views/teacher/CourseEditorView.vue'

const COURSE = {
  id: 1,
  title: '人工智能基础入门',
  description: '从监督学习到神经网络',
  status: 'approved',
  teacher: { id: 2, username: 'teacher' },
  invite_code: 'ABC12345',
  invite_enabled: true,
  chapter_count: 1,
  knowledge_count: 1,
  student_count: 1,
  created_at: '2026-10-20T08:00:00Z',
  updated_at: '2026-10-22T08:00:00Z',
  submitted_at: '2026-10-21T08:00:00Z',
  reviewed_at: '2026-10-22T08:00:00Z',
  review_comment: null,
  chapters: [
    {
      id: 1,
      title: '第一章 绪论',
      description: '课程导论',
      order_no: 0,
      knowledges: [
        {
          id: 1,
          chapter_id: 1,
          name: '监督学习',
          description: '从标注数据中学习',
          difficulty: 2,
        },
      ],
    },
  ],
}

async function mountEditor() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/teacher/courses', component: { template: '<div />' } },
      { path: '/teacher/courses/:id', component: { template: '<div />' } },
    ],
  })
  await router.push('/teacher/courses/1')
  await router.isReady()

  const wrapper = mount(CourseEditorView, {
    global: {
      plugins: [router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('TeacherCourseEditorView', () => {
  beforeEach(() => {
    getCourse.mockReset()
    listCourseStudents.mockReset()
    listMaterials.mockReset()
    getCourse.mockResolvedValue({ code: 0, message: 'ok', data: COURSE })
    listMaterials.mockResolvedValue({
      code: 0,
      data: {
        items: [
          {
            id: 11,
            title: '第一章讲义',
            chapter_id: 1,
            chapter_title: '第一章 绪论',
            status: 'approved',
            index_status: 'indexed',
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })
    listCourseStudents.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: {
        items: [
          {
            student_id: 3,
            username: 'student',
            email: 'student@example.com',
            source: 'invite_code',
            enrolled_at: '2026-10-22T08:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })
  })

  it('renders curriculum, invite code and roster for a published course', async () => {
    const wrapper = await mountEditor()

    expect(getCourse).toHaveBeenCalledWith('1')
    expect(listCourseStudents).toHaveBeenCalledWith(1, { page_size: 100 })
    expect(listMaterials).toHaveBeenCalledWith({ course_id: 1, page_size: 100 })
    const text = wrapper.text()
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('已发布')
    expect(text).toContain('第一章 绪论')
    expect(text).toContain('监督学习')
    expect(text).toContain('第一章讲义')
    expect(text).toContain('本章资料 1 份')
    expect(text).toContain('ABC12345')
    expect(text).toContain('student')
    expect(text).toContain('邀请码加入')
    expect(text).toContain('课程已发布')
    expect(text).toContain('修改即时生效')
    expect(text).toContain('编辑课程信息')
  })
})
