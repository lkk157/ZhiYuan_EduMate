import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/knowledgeBase', () => ({
  listKnowledgeBases: vi.fn(),
  createKnowledgeBase: vi.fn(),
  updateKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
  listKnowledgeBaseMaterials: vi.fn(),
  uploadKnowledgeBaseMaterial: vi.fn(),
  deleteKnowledgeBaseMaterial: vi.fn(),
  retryKnowledgeBaseMaterial: vi.fn(),
}))

vi.mock('@/api/material', () => ({
  downloadMaterial: vi.fn(),
}))

import {
  listKnowledgeBaseMaterials,
  listKnowledgeBases,
} from '@/api/knowledgeBase'
import KnowledgeBasesView from '@/views/student/KnowledgeBasesView.vue'

const KB = {
  id: 1,
  name: '我的知识库',
  description: '个人学习资料默认知识库',
  is_default: true,
  status: 'active',
  material_count: 1,
  indexed_count: 1,
  created_at: '2026-10-23T08:00:00Z',
  updated_at: '2026-10-23T08:00:00Z',
}

const MATERIAL = {
  id: 41,
  scope: 'personal',
  knowledge_base_id: 1,
  knowledge_base_name: '我的知识库',
  title: '算法笔记',
  source_filename: 'algorithm-notes.pdf',
  file_type: '.pdf',
  file_size: 4096,
  index_status: 'indexed',
  index_error: null,
  download_count: 0,
  created_at: '2026-10-23T08:00:00Z',
}

async function mountView() {
  const wrapper = mount(KnowledgeBasesView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('KnowledgeBasesView', () => {
  beforeEach(() => {
    listKnowledgeBases.mockReset()
    listKnowledgeBaseMaterials.mockReset()
    listKnowledgeBases.mockResolvedValue({
      code: 0,
      data: { items: [KB] },
    })
    listKnowledgeBaseMaterials.mockResolvedValue({
      code: 0,
      data: { items: [MATERIAL], total: 1, page: 1, page_size: 10 },
    })
  })

  it('renders the default knowledge base and its indexed materials', async () => {
    const wrapper = await mountView()

    expect(listKnowledgeBases).toHaveBeenCalled()
    expect(listKnowledgeBaseMaterials).toHaveBeenCalledWith(1, {
      page: 1,
      page_size: 10,
    })
    const text = wrapper.text()
    expect(text).toContain('我的知识库')
    expect(text).toContain('默认')
    expect(text).toContain('算法笔记')
    expect(text).toContain('algorithm-notes.pdf')
    expect(text).toContain('已索引')
    expect(text).toContain('上传资料')
  })
})
