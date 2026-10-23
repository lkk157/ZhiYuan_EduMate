import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

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

import { getMaterial, listMaterials } from '@/api/material'
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

    const reviewButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '审核')
    await reviewButton.trigger('click')
    await flushPromises()

    expect(getMaterial).toHaveBeenCalledWith(21)
  })
})
