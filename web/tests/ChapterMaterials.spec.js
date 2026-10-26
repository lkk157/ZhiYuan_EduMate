import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api/course', () => ({
  getCourse: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  listMaterials: vi.fn(),
  downloadMaterial: vi.fn(),
}))

import { getCourse } from '@/api/course'
import { listMaterials } from '@/api/material'
import CourseDetailView from '@/views/student/CourseDetailView.vue'
import ChapterMaterialsView from '@/views/student/ChapterMaterialsView.vue'

function coursePayload() {
  return {
    code: 0,
    data: {
      id: 1,
      title: '人工智能基础入门',
      description: '从监督学习开始',
      teacher: { id: 2, username: 'teacher' },
      chapter_count: 2,
      knowledge_count: 3,
      student_count: 8,
      chapters: [
        {
          id: 11,
          title: '第一章 绪论',
          description: '课程导论',
          order_no: 0,
          knowledges: [
            { id: 101, name: '监督学习', description: '带标签数据', difficulty: 2 },
          ],
        },
        {
          id: 12,
          title: '第二章 模型',
          description: '常见模型',
          order_no: 1,
          knowledges: [
            { id: 102, name: '线性回归', description: '回归模型', difficulty: 3 },
            { id: 103, name: '神经网络', description: '深度模型', difficulty: 4 },
          ],
        },
      ],
    },
  }
}

function material(id, title, chapterId) {
  return {
    id,
    title,
    chapter_id: chapterId,
    chapter_title: chapterId === 11 ? '第一章 绪论' : '第二章 模型',
    knowledge_id: chapterId === 11 ? 101 : 102,
    knowledge_title: chapterId === 11 ? '监督学习' : '线性回归',
    course_id: 1,
    course_title: '人工智能基础入门',
    source_filename: `${title}.pdf`,
    file_type: '.pdf',
    file_size: 2048,
    view_count: 3,
    download_count: 1,
  }
}

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/student/courses', component: { template: '<div />' } },
      { path: '/student/courses/:id', component: CourseDetailView },
      {
        path: '/student/courses/:courseId/chapters/:chapterId',
        name: 'student-chapter',
        component: ChapterMaterialsView,
      },
    ],
  })
}

async function mountAt(component, path) {
  const router = buildRouter()
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, {
    global: {
      plugins: [router, ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('student course chapters', () => {
  beforeEach(() => {
    getCourse.mockReset()
    listMaterials.mockReset()
    getCourse.mockResolvedValue(coursePayload())
    listMaterials.mockResolvedValue({
      code: 0,
      data: {
        items: [material(1, '监督学习讲义', 11), material(2, '监督学习练习', 11), material(3, '线性回归讲义', 12)],
        total: 3,
        page: 1,
        page_size: 100,
      },
    })
  })

  it('shows material counts inside chapters and opens the chapter page', async () => {
    const { wrapper, router } = await mountAt(CourseDetailView, '/student/courses/1')

    const text = wrapper.text()
    expect(text).toContain('第一章 绪论')
    expect(text).toContain('2 份资料')
    expect(text).toContain('1 份资料')
    expect(text).not.toContain('课程资料')

    await wrapper.findAll('.chapter-card')[0].trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/student/courses/1/chapters/11')
  })

  it('loads only the selected chapter materials on the chapter page', async () => {
    listMaterials.mockResolvedValue({
      code: 0,
      data: {
        items: [material(1, '监督学习讲义', 11)],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })

    const { wrapper } = await mountAt(
      ChapterMaterialsView,
      '/student/courses/1/chapters/11',
    )

    expect(listMaterials).toHaveBeenCalledWith({
      course_id: '1',
      chapter_id: '11',
      page_size: 100,
    })
    const text = wrapper.text()
    expect(text).toContain('第一章 绪论')
    expect(text).toContain('监督学习讲义')
    expect(text).toContain('监督学习')
    expect(text).toContain('1 份已发布资料')
    expect(text).not.toContain('线性回归讲义')
  })
})
