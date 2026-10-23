import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/course', () => ({
  listCourses: vi.fn(),
  getCourse: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  listMaterials: vi.fn(),
  getMaterial: vi.fn(),
  uploadMaterial: vi.fn(),
  reviewMaterial: vi.fn(),
  retryMaterialIndex: vi.fn(),
  deleteMaterial: vi.fn(),
  downloadMaterial: vi.fn(),
  fetchRagHealth: vi.fn(),
}))

import { listCourses } from '@/api/course'
import {
  fetchRagHealth,
  listMaterials,
  retryMaterialIndex,
} from '@/api/material'
import TeacherMaterialsView from '@/views/teacher/MaterialsView.vue'

const MATERIAL = {
  id: 11,
  course_id: 1,
  course_title: '人工智能基础入门',
  chapter_id: 1,
  chapter_title: '第一章 绪论',
  title: '第一章讲义',
  source_filename: 'lecture-01.pdf',
  file_type: '.pdf',
  file_size: 2048,
  status: 'approved',
  index_status: 'failed',
  index_error: '模拟索引失败',
  rag_filename: 'm11__lecture-01.pdf',
  vector_doc_id: null,
  view_count: 0,
  download_count: 3,
  created_at: '2026-10-23T08:00:00Z',
  uploader: { id: 2, username: 'teacher' },
}

async function mountMaterials() {
  const wrapper = mount(TeacherMaterialsView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('TeacherMaterialsView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    listMaterials.mockReset()
    fetchRagHealth.mockReset()
    retryMaterialIndex.mockReset()

    listCourses.mockResolvedValue({
      code: 0,
      data: {
        items: [{ id: 1, title: '人工智能基础入门' }],
        total: 1,
        page: 1,
        page_size: 100,
      },
    })
    listMaterials.mockResolvedValue({
      code: 0,
      data: { items: [MATERIAL], total: 1, page: 1, page_size: 10 },
    })
    fetchRagHealth.mockResolvedValue({
      code: 0,
      data: { status: 'ok', reachable: true, auth_ok: true, error: null },
    })
    retryMaterialIndex.mockResolvedValue({ code: 0, data: { id: 11 } })
  })

  it('renders materials, RAG health and retries a failed index', async () => {
    const wrapper = await mountMaterials()

    const text = wrapper.text()
    expect(text).toContain('第一章讲义')
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('第一章 绪论')
    expect(text).toContain('已通过')
    expect(text).toContain('索引失败')
    expect(text).toContain('RAG 正常')
    expect(text).toContain('重试')

    const retryButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '重试')
    await retryButton.trigger('click')
    await flushPromises()

    expect(retryMaterialIndex).toHaveBeenCalledWith(11)
  })
})
