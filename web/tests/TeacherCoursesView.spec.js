import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
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

import { listCourses } from '@/api/course'
import TeacherCoursesView from '@/views/teacher/CoursesView.vue'

const COURSES = [
  {
    id: 1,
    title: '人工智能基础入门',
    description: '从监督学习到神经网络',
    status: 'draft',
    chapter_count: 2,
    knowledge_count: 5,
    student_count: 0,
    created_at: '2026-10-20T08:00:00Z',
    review_comment: null,
  },
  {
    id: 2,
    title: '数据结构与算法',
    description: '线性表、树与图',
    status: 'approved',
    chapter_count: 4,
    knowledge_count: 12,
    student_count: 8,
    created_at: '2026-10-18T08:00:00Z',
    review_comment: null,
  },
]

async function mountCourses() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/teacher/courses', component: { template: '<div />' } },
      { path: '/teacher/courses/:id', component: { template: '<div />' } },
    ],
  })
  await router.push('/teacher/courses')
  await router.isReady()

  const wrapper = mount(TeacherCoursesView, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('TeacherCoursesView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    listCourses.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: { items: COURSES, total: 2, page: 1, page_size: 9 },
    })
  })

  it('renders owned courses with status, structure and actions', async () => {
    const wrapper = await mountCourses()

    expect(listCourses).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 9 }),
    )
    const text = wrapper.text()
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('数据结构与算法')
    expect(text).toContain('草稿')
    expect(text).toContain('已发布')
    expect(text).toContain('2 章节')
    expect(text).toContain('8 学生')
    expect(text).toContain('提交审核')
    expect(text).toContain('管理课程')
    expect(text).toContain('创建课程')
  })
})
