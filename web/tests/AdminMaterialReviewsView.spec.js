import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/admin', () => ({
  fetchReviewPolicy: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  listMaterials: vi.fn(),
  getMaterial: vi.fn(),
  uploadMaterial: vi.fn(),
  reviewMaterial: vi.fn(),
  batchReviewMaterials: vi.fn(),
  retryMaterialIndex: vi.fn(),
  deleteMaterial: vi.fn(),
  downloadMaterial: vi.fn(),
  fetchRagHealth: vi.fn(),
}))

import { fetchReviewPolicy } from '@/api/admin'
import {
  batchReviewMaterials,
  getMaterial,
  listMaterials,
} from '@/api/material'
import AdminMaterialReviewsView from '@/views/admin/MaterialReviewsView.vue'

const MATERIAL = {
  id: 21,
  course_id: 2,
  course_title: '数据结构与算法',
  chapter_title: '线性表',
  title: '线性表讲义',
  source_filename: 'linear-list.pdf',
  file_type: '.pdf',
  file_size: 4096,
  status: 'pending',
  index_status: 'pending',
  index_error: null,
  rag_filename: 'm21__linear-list.pdf',
  vector_doc_id: null,
  view_count: 0,
  download_count: 0,
  uploader: { id: 2, username: 'teacher' },
  created_at: '2026-10-23T08:00:00Z',
  review_comment: null,
}

async function mountReviews() {
  const wrapper = mount(AdminMaterialReviewsView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('AdminMaterialReviewsView', () => {
  beforeEach(() => {
    listMaterials.mockReset()
    getMaterial.mockReset()
    fetchReviewPolicy.mockReset()
    batchReviewMaterials.mockReset()
    fetchReviewPolicy.mockResolvedValue({
      code: 0,
      data: {
        auto_review_enabled: true,
        course_rules: ['课程简介非空'],
        material_rules: ['课程已发布且资料关联章节', '支持 PDF / DOCX / PPTX 自动审核'],
      },
    })
    batchReviewMaterials.mockResolvedValue({
      code: 0,
      message: '已通过 1 份资料，正在后台索引',
      data: { succeeded: [{ id: 21 }], failed: [], count: 1 },
    })
    listMaterials.mockResolvedValue({
      code: 0,
      data: { items: [MATERIAL], total: 1, page: 1, page_size: 10 },
    })
    getMaterial.mockResolvedValue({ code: 0, data: MATERIAL })
  })

  it('lists pending materials and opens the review detail', async () => {
    const wrapper = await mountReviews()

    expect(listMaterials).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'pending', page: 1 }),
    )
    const text = wrapper.text()
    expect(text).toContain('资料审核')
    expect(text).toContain('线性表讲义')
    expect(text).toContain('数据结构与算法')
    expect(text).toContain('teacher')
    expect(text).toContain('待审核')
    expect(text).toContain('自动审核已启用')
    expect(text).toContain('批量通过')
    expect(text).toContain('批量驳回')

    const reviewButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '审核')
    await reviewButton.trigger('click')
    await flushPromises()

    expect(getMaterial).toHaveBeenCalledWith(21)
  })
})
