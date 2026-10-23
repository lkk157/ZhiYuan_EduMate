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

import { joinCourse, listCourses } from '@/api/course'
import StudentCoursesView from '@/views/student/CoursesView.vue'

const COURSE = {
  id: 9,
  title: '人工智能基础入门',
  description: '监督学习与神经网络',
  teacher: { id: 2, username: 'teacher' },
  chapter_count: 3,
  knowledge_count: 8,
  student_count: 12,
  created_at: '2026-10-20T08:00:00Z',
}

async function mountCourses() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/student/courses', component: { template: '<div />' } },
      { path: '/student/courses/:id', component: { template: '<div />' } },
    ],
  })
  await router.push('/student/courses')
  await router.isReady()

  const wrapper = mount(StudentCoursesView, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('StudentCoursesView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    joinCourse.mockReset()
    listCourses.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: { items: [COURSE], total: 1, page: 1, page_size: 9 },
    })
    joinCourse.mockResolvedValue({
      code: 0,
      message: '已加入课程',
      data: { ...COURSE, joined: true },
    })
  })

  it('renders enrolled courses and joins another course by code', async () => {
    const wrapper = await mountCourses()

    const text = wrapper.text()
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('教师 teacher')
    expect(text).toContain('3 章节')
    expect(text).toContain('12 同学')

    const input = wrapper.find('input[placeholder="输入课程邀请码"]')
    await input.setValue('ABC12345')
    const joinButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '加入课程')
    await joinButton.trigger('click')
    await flushPromises()

    expect(joinCourse).toHaveBeenCalledWith('ABC12345')
    expect(listCourses).toHaveBeenCalledTimes(2)
  })
})
