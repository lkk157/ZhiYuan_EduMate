import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

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
import { askQuestion } from '@/api/qa'
import QaView from '@/views/student/QaView.vue'

async function mountQa() {
  const wrapper = mount(QaView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('QaView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    listKnowledgeBases.mockReset()
    askQuestion.mockReset()

    listCourses.mockResolvedValue({
      code: 0,
      data: {
        items: [{ id: 1, title: '人工智能基础入门' }],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })
    listKnowledgeBases.mockResolvedValue({
      code: 0,
      data: { items: [{ id: 2, name: '我的知识库' }] },
    })
    askQuestion.mockResolvedValue({
      code: 0,
      message: '问答完成',
      data: {
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
        scope_note: null,
        course_id: 1,
        course_title: '人工智能基础入门',
        knowledge_base_id: null,
        knowledge_base_name: null,
      },
    })
  })

  it('asks within the course scope and renders citations', async () => {
    const wrapper = await mountQa()

    await wrapper
      .find('textarea[placeholder="输入你的问题，例如：什么是监督学习？"]')
      .setValue('什么是监督学习？')
    await wrapper.find('.send-button').trigger('click')
    await flushPromises()

    expect(askQuestion).toHaveBeenCalledWith({
      question: '什么是监督学习？',
      scope: 'course',
      course_id: 1,
    })
    const text = wrapper.text()
    expect(text).toContain('监督学习使用带标签的数据训练模型。')
    expect(text).toContain('引用来源')
    expect(text).toContain('课程讲义')
    expect(text).toContain('第 3 页')
    expect(text).toContain('已找到依据')
    expect(text).toContain('人工智能基础入门')

    const toggle = wrapper.find('.sources-toggle')
    expect(toggle.exists()).toBe(true)
    expect(wrapper.find('.citations').attributes('style')).toContain('display: none')

    await toggle.trigger('click')
    expect(wrapper.find('.citations').attributes('style') || '').not.toContain('display: none')
  })
})
