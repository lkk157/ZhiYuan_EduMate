import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/course', () => ({
  listCourses: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  listMaterials: vi.fn(),
  getMaterial: vi.fn(),
  uploadMaterial: vi.fn(),
  reviewMaterial: vi.fn(),
  retryMaterialIndex: vi.fn(),
  deleteMaterial: vi.fn(),
  downloadMaterial: vi.fn(),
  previewMaterial: vi.fn(),
  markMaterialViewed: vi.fn(),
  fetchRagHealth: vi.fn(),
}))

import { listCourses } from '@/api/course'
import {
  listMaterials,
  markMaterialViewed,
  previewMaterial,
} from '@/api/material'
import StudentMaterialsView from '@/views/student/MaterialsView.vue'

const MATERIAL = {
  id: 31,
  course_id: 1,
  course_title: '人工智能基础入门',
  chapter_title: '第一章 绪论',
  title: '监督学习导论',
  source_filename: 'supervised-learning.pdf',
  file_type: '.pdf',
  file_size: 8192,
  status: 'approved',
  index_status: 'indexed',
  download_count: 5,
  created_at: '2026-10-23T08:00:00Z',
}

async function mountMaterials() {
  const wrapper = mount(StudentMaterialsView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('StudentMaterialsView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    listMaterials.mockReset()
    previewMaterial.mockReset()
    markMaterialViewed.mockReset()
    previewMaterial.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }))
    markMaterialViewed.mockResolvedValue({ code: 0, data: { view_count: 1 } })
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:preview')
    globalThis.URL.revokeObjectURL = vi.fn()
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
      data: { items: [MATERIAL], total: 1, page: 1, page_size: 12 },
    })
  })

  it('renders approved materials from enrolled courses', async () => {
    const wrapper = await mountMaterials()

    const text = wrapper.text()
    expect(text).toContain('学习资料')
    expect(text).toContain('监督学习导论')
    expect(text).toContain('人工智能基础入门')
    expect(text).toContain('第一章 绪论')
    expect(text).toContain('PDF')
    expect(text).toContain('8.0 KB')
    expect(text).toContain('下载')
    expect(text).toContain('预览')
  })

  it('opens the preview dialog and records a view', async () => {
    const wrapper = await mountMaterials()

    const previewButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '预览')
    await previewButton.trigger('click')
    await flushPromises()

    expect(previewMaterial).toHaveBeenCalledWith(31)
    expect(markMaterialViewed).toHaveBeenCalledWith(31)
  })
})
