import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/course', () => ({
  listCourses: vi.fn(),
}))

vi.mock('@/api/knowledgeBase', () => ({
  listKnowledgeBases: vi.fn(),
}))

vi.mock('@/api/qa', () => ({
  askQuestion: vi.fn(),
  listQaHistory: vi.fn(),
}))

import { listCourses } from '@/api/course'
import { listKnowledgeBases } from '@/api/knowledgeBase'
import { listQaHistory } from '@/api/qa'
import QaHistoryView from '@/views/student/QaHistoryView.vue'

async function mountHistory() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/student/qa-history', component: { template: '<div />' } },
      { path: '/student/qa', component: { template: '<div />' } },
    ],
  })
  await router.push('/student/qa-history')
  await router.isReady()

  const wrapper = mount(QaHistoryView, {
    global: {
      plugins: [router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('QaHistoryView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    listKnowledgeBases.mockReset()
    listQaHistory.mockReset()
    listCourses.mockResolvedValue({
      code: 0,
      data: { items: [{ id: 1, title: '人工智能基础入门' }] },
    })
    listKnowledgeBases.mockResolvedValue({
      code: 0,
      data: { items: [{ id: 2, name: '我的知识库' }] },
    })
    listQaHistory.mockResolvedValue({
      code: 0,
      data: {
        items: [
          {
            id: 1,
            scope: 'course',
            question: '什么是监督学习？',
            answer: '监督学习使用带标签的数据训练模型。',
            references: [
              {
                material_id: 11,
                file_name: 'm11__lecture.pdf',
                page_no: 3,
                snippet: '监督学习使用带标签的数据。',
                score: 0.88,
                scope: 'course',
                title: '课程讲义',
                course_title: '人工智能基础入门',
                chapter_title: '第一章 绪论',
              },
            ],
            hit: true,
            status: 'success',
            latency_ms: 120,
            course_id: 1,
            course_title: '人工智能基础入门',
            knowledge_base_id: null,
            knowledge_base_name: null,
            created_at: '2026-10-23T10:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      },
    })
  })

  it('renders history with answers, citations and scope', async () => {
    const wrapper = await mountHistory()

    const text = wrapper.text()
    expect(text).toContain('问答记录')
    expect(text).toContain('什么是监督学习？')
    expect(text).toContain('监督学习使用带标签的数据训练模型。')
    expect(text).toContain('引用来源')
    expect(text).toContain('课程讲义')
    expect(text).toContain('课程知识库')
    expect(text).toContain('人工智能基础入门')

    const toggle = wrapper.find('.sources-toggle')
    expect(toggle.exists()).toBe(true)
    expect(wrapper.find('.citations').attributes('style')).toContain('display: none')

    await toggle.trigger('click')
    expect(wrapper.find('.citations').attributes('style') || '').not.toContain('display: none')
  })
})
