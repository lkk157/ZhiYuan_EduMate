import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/home', () => ({
  getStudentHome: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  markMaterialViewed: vi.fn(),
}))

import { getStudentHome } from '@/api/home'
import { markMaterialViewed } from '@/api/material'
import { useAuthStore } from '@/stores/auth'
import HomeView from '@/views/student/HomeView.vue'

function homePayload() {
  return {
    code: 0,
    data: {
      stats: {
        course_count: 1,
        weekly_questions: 3,
        recommendation_count: 2,
        personal_material_count: 1,
        average_mastery: null,
      },
      courses: [
        {
          id: 1,
          title: '人工智能基础入门',
          description: '从监督学习开始',
          teacher: { id: 2, username: 'teacher' },
          chapter_count: 2,
          knowledge_count: 5,
          student_count: 8,
        },
      ],
      hot: [
        {
          id: 11,
          title: '监督学习讲义',
          file_type: '.pdf',
          course_id: 1,
          course_title: '人工智能基础入门',
          reason: '热门资料 · 浏览 12 次 / 下载 3 次',
          view_count: 12,
        },
      ],
      recommendations: {
        seed: { id: 11, title: '监督学习讲义' },
        same_chapter: [
          {
            id: 12,
            title: '同章节练习',
            file_type: '.pdf',
            course_id: 1,
            course_title: '人工智能基础入门',
            chapter_title: '第一章 绪论',
            reason: '同章节推荐 · 与你浏览的《监督学习讲义》同属「第一章 绪论」',
            view_count: 2,
          },
        ],
        similar: [
          {
            id: 13,
            title: '相似知识点资料',
            file_type: '.docx',
            course_id: 1,
            course_title: '人工智能基础入门',
            chapter_title: '第二章 模型',
            reason: '相似资料 · 与你浏览的《监督学习讲义》共享知识点「监督学习」',
            view_count: 1,
          },
        ],
      },
      recent_personal: [
        {
          id: 21,
          title: '我的算法笔记',
          file_type: '.pdf',
          knowledge_base_name: '我的知识库',
          index_status: 'indexed',
          created_at: '2026-10-23T09:00:00Z',
        },
      ],
    },
  }
}

async function mountHome() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.token = 'token'
  auth.user = { id: 3, username: 'student', role: 'student' }

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/student/home', component: { template: '<div />' } },
      { path: '/student/courses', component: { template: '<div />' } },
      { path: '/student/courses/:id', component: { template: '<div />' } },
      { path: '/student/materials', component: { template: '<div />' } },
      { path: '/student/knowledge-bases', component: { template: '<div />' } },
      { path: '/student/qa', component: { template: '<div />' } },
    ],
  })
  await router.push('/student/home')
  await router.isReady()

  const wrapper = mount(HomeView, {
    global: {
      plugins: [pinia, router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('StudentHomeView', () => {
  beforeEach(() => {
    getStudentHome.mockReset()
    markMaterialViewed.mockReset()
    getStudentHome.mockResolvedValue(homePayload())
    markMaterialViewed.mockResolvedValue({ code: 0, data: { view_count: 13 } })
  })

  it('renders courses, hot materials and reasoned recommendations', async () => {
    const { wrapper } = await mountHome()
    const text = wrapper.text()

    expect(text).toContain('你好，student')
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('监督学习讲义')
    expect(text).toContain('热门资料 · 浏览 12 次 / 下载 3 次')
    expect(text).toContain('同章节练习')
    expect(text).toContain('同属「第一章 绪论」')
    expect(text).toContain('相似知识点资料')
    expect(text).toContain('共享知识点「监督学习」')
    expect(text).toContain('我的算法笔记')
    expect(text).toContain('我的知识库')
    expect(text).toContain('本周问答')
    expect(text).toContain('3')
  })

  it('records a view before opening a recommended material', async () => {
    const { wrapper, router } = await mountHome()

    await wrapper.find('.material-row').trigger('click')
    await flushPromises()

    expect(markMaterialViewed).toHaveBeenCalledWith(11)
    expect(router.currentRoute.value.path).toBe('/student/courses/1')
  })

  it('shows join-course guidance when the student has no courses', async () => {
    getStudentHome.mockResolvedValue({
      code: 0,
      data: {
        stats: {
          course_count: 0,
          weekly_questions: 0,
          recommendation_count: 0,
          personal_material_count: 0,
          average_mastery: null,
        },
        courses: [],
        hot: [],
        recommendations: { seed: null, same_chapter: [], similar: [] },
        recent_personal: [],
      },
    })

    const { wrapper } = await mountHome()
    const text = wrapper.text()

    expect(text).toContain('还没有加入课程')
    expect(text).toContain('去加入课程')
    expect(text).toContain('推荐正在准备')
    expect(text).toContain('个人知识库还是空的')
  })
})
