import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

vi.mock('@/api/admin', () => ({
  fetchReviewPolicy: vi.fn(),
}))

vi.mock('@/api/course', () => ({
  listCourses: vi.fn(),
  createCourse: vi.fn(),
  updateCourse: vi.fn(),
  submitCourse: vi.fn(),
  getCourse: vi.fn(),
  reviewCourse: vi.fn(),
  batchReviewCourses: vi.fn(),
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

import { fetchReviewPolicy } from '@/api/admin'
import { batchReviewCourses, getCourse, listCourses } from '@/api/course'
import AdminReviewsView from '@/views/admin/ReviewsView.vue'

const PENDING_COURSE = {
  id: 7,
  title: '机器学习基础',
  description: '面向初学者的机器学习课程',
  status: 'pending',
  teacher: { id: 2, username: 'teacher' },
  chapter_count: 2,
  knowledge_count: 6,
  student_count: 0,
  submitted_at: '2026-10-23T08:00:00Z',
  review_comment: null,
}

async function mountReviews() {
  const wrapper = mount(AdminReviewsView, {
    global: {
      plugins: [ElementPlus],
      components: { ...ElementPlusIcons },
    },
  })
  await flushPromises()
  return wrapper
}

describe('AdminReviewsView', () => {
  beforeEach(() => {
    listCourses.mockReset()
    getCourse.mockReset()
    fetchReviewPolicy.mockReset()
    batchReviewCourses.mockReset()
    fetchReviewPolicy.mockResolvedValue({
      code: 0,
      data: {
        auto_review_enabled: true,
        course_rules: ['课程简介非空', '至少包含 1 个章节和 1 个知识点'],
        material_rules: ['课程已发布且资料关联章节'],
      },
    })
    batchReviewCourses.mockResolvedValue({
      code: 0,
      message: '已通过 1 门课程',
      data: { succeeded: [{ id: 7 }], failed: [], count: 1 },
    })
    listCourses.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: { items: [PENDING_COURSE], total: 1, page: 1, page_size: 10 },
    })
    getCourse.mockResolvedValue({
      code: 0,
      message: 'ok',
      data: {
        ...PENDING_COURSE,
        chapters: [
          {
            id: 1,
            title: '第一章 绪论',
            description: '课程导论',
            order_no: 0,
            knowledges: [
              { id: 1, chapter_id: 1, name: '监督学习', difficulty: 2 },
            ],
          },
        ],
      },
    })
  })

  it('lists pending courses and opens the review detail', async () => {
    const wrapper = await mountReviews()

    expect(listCourses).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'pending', page: 1 }),
    )
    const text = wrapper.text()
    expect(text).toContain('课程审核')
    expect(text).toContain('机器学习基础')
    expect(text).toContain('teacher')
    expect(text).toContain('待审核')
    expect(text).toContain('2 章 · 6 知识点')
    expect(text).toContain('自动审核已启用')
    expect(text).toContain('批量通过')
    expect(text).toContain('批量驳回')

    const reviewButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '审核')
    await reviewButton.trigger('click')
    await flushPromises()

    expect(getCourse).toHaveBeenCalledWith(7)
  })
})
