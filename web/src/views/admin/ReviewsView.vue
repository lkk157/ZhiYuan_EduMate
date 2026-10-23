<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

import { getCourse, listCourses, reviewCourse } from '@/api/course'
import { COURSE_STATUS_META, courseStatusLabel, courseStatusType } from '@/utils/course'
import { formatDateTime } from '@/utils/format'

const loading = ref(false)
const courses = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const statusFilter = ref('pending')

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const reviewComment = ref('')
const reviewing = ref(false)

const statusOptions = Object.entries(COURSE_STATUS_META).map(([value, meta]) => ({
  value,
  label: meta.label,
}))

async function load() {
  loading.value = true
  try {
    const body = await listCourses({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      status: statusFilter.value || undefined,
    })
    courses.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载课程列表失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'pending'
  search()
}

async function openDetail(course) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  reviewComment.value = course.review_comment || ''
  try {
    const body = await getCourse(course.id)
    detail.value = body?.data || null
  } catch (error) {
    ElMessage.error(error?.message || '加载课程详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function approve() {
  try {
    await ElMessageBox.confirm(
      '审核通过后课程将对学生开放，确定通过吗？',
      '通过审核',
      { type: 'success', confirmButtonText: '通过', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await submitReview('approve')
}

async function reject() {
  if (!reviewComment.value.trim()) {
    ElMessage.warning('驳回课程时必须填写审核意见')
    return
  }
  try {
    await ElMessageBox.confirm(
      '驳回后教师可根据审核意见修改并重新提交。确定驳回吗？',
      '驳回课程',
      { type: 'warning', confirmButtonText: '驳回', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await submitReview('reject')
}

async function submitReview(decision) {
  reviewing.value = true
  try {
    await reviewCourse(detail.value.id, {
      decision,
      comment: reviewComment.value.trim() || null,
    })
    ElMessage.success(decision === 'approve' ? '课程已通过审核' : '课程已驳回')
    detailVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '审核操作失败')
  } finally {
    reviewing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page admin-reviews">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">COURSE REVIEW</span>
        <h1>课程审核</h1>
        <p>查看教师提交的课程结构与知识点，通过后学生即可凭邀请码加入。</p>
      </div>
      <div class="pending-chip">
        <strong>{{ statusFilter === 'pending' ? total : '—' }}</strong>
        <span>待审核</span>
      </div>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-input
          v-model="keyword"
          class="keyword-input"
          placeholder="搜索课程名称"
          :prefix-icon="Search"
          clearable
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="statusFilter" class="status-select" @change="search">
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section class="table-card em-card">
      <el-table v-loading="loading" :data="courses">
        <el-table-column label="课程" min-width="260">
          <template #default="{ row }">
            <div class="course-cell">
              <span class="course-letter">{{ row.title.slice(0, 1) }}</span>
              <div>
                <strong>{{ row.title }}</strong>
                <small>{{ row.description || '暂无课程简介' }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="教师" width="120">
          <template #default="{ row }">{{ row.teacher.username }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="courseStatusType(row.status)" effect="light">
              {{ courseStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结构" width="150">
          <template #default="{ row }">
            <span class="structure-text">
              {{ row.chapter_count }} 章 · {{ row.knowledge_count }} 知识点
            </span>
          </template>
        </el-table-column>
        <el-table-column label="学生" width="80" align="center">
          <template #default="{ row }">{{ row.student_count }}</template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.submitted_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="openDetail(row)"
            >
              {{ row.status === 'pending' ? '审核' : '查看' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="没有匹配的课程" :image-size="80" />
        </template>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </section>

    <el-dialog v-model="detailVisible" title="课程审核" width="780px">
      <div v-loading="detailLoading" class="review-detail">
        <template v-if="detail">
          <div class="detail-head">
            <div>
              <el-tag :type="courseStatusType(detail.status)" effect="light" round>
                {{ courseStatusLabel(detail.status) }}
              </el-tag>
              <h2>{{ detail.title }}</h2>
              <p>{{ detail.description || '暂无课程简介' }}</p>
            </div>
            <div class="detail-meta">
              <span>教师：{{ detail.teacher.username }}</span>
              <span>提交：{{ formatDateTime(detail.submitted_at) }}</span>
              <span>
                {{ detail.chapter_count }} 章节 · {{ detail.knowledge_count }} 知识点
              </span>
            </div>
          </div>

          <div v-if="detail.status === 'rejected' && detail.review_comment" class="reject-note">
            {{ detail.review_comment }}
          </div>

          <div class="detail-chapters">
            <article v-for="(chapter, index) in detail.chapters" :key="chapter.id" class="detail-chapter">
              <header>
                <span>{{ index + 1 }}</span>
                <strong>{{ chapter.title }}</strong>
              </header>
              <p v-if="chapter.description">{{ chapter.description }}</p>
              <div class="knowledge-chips">
                <span v-for="knowledge in chapter.knowledges" :key="knowledge.id">
                  {{ knowledge.name }}
                  <em>难度 {{ knowledge.difficulty }}</em>
                </span>
                <span v-if="!chapter.knowledges.length" class="empty-chip">暂无知识点</span>
              </div>
            </article>
            <el-empty
              v-if="!detail.chapters.length"
              description="该课程还没有章节"
              :image-size="70"
            />
          </div>

          <div v-if="detail.status === 'pending'" class="review-box">
            <label>审核意见</label>
            <el-input
              v-model="reviewComment"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="通过时可选填；驳回时必须说明原因"
            />
            <div class="review-actions">
              <el-button type="danger" plain :loading="reviewing" @click="reject">
                驳回
              </el-button>
              <el-button type="success" :loading="reviewing" @click="approve">
                通过审核
              </el-button>
            </div>
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-reviews {
  display: grid;
  gap: 18px;
}

.pending-chip {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 12px 20px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--em-shadow-card);
}

.pending-chip strong {
  color: #ea8a0a;
  font-size: 24px;
  font-weight: 750;
}

.pending-chip span {
  color: var(--em-text-muted);
  font-size: 12px;
}

.filter-card {
  padding: 18px 20px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.keyword-input {
  width: 240px;
}

.status-select {
  width: 150px;
}

.table-card {
  padding: 8px 8px 18px;
}

.course-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.course-letter {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 11px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-weight: 700;
}

.course-cell div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.35;
}

.course-cell strong {
  font-size: 14px;
}

.course-cell small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.structure-text,
.time-text {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 14px 0;
}

.review-detail {
  min-height: 120px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.detail-head h2 {
  margin-top: 10px;
  font-size: 22px;
}

.detail-head p {
  margin-top: 6px;
  color: var(--em-text-secondary);
}

.detail-meta {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 4px;
  color: var(--em-text-muted);
  font-size: 12px;
  text-align: right;
}

.reject-note {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.detail-chapters {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.detail-chapter {
  padding: 12px 14px;
  border: 1px solid var(--em-border);
  border-radius: 12px;
  background: #fbfdff;
}

.detail-chapter header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-chapter header span {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 7px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 11px;
  font-weight: 700;
}

.detail-chapter header strong {
  font-size: 14px;
}

.detail-chapter p {
  margin-top: 4px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.knowledge-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.knowledge-chips span {
  padding: 3px 9px;
  border-radius: 999px;
  background: #eef4fc;
  color: #52637a;
  font-size: 11px;
}

.knowledge-chips em {
  margin-left: 4px;
  color: var(--em-text-muted);
  font-style: normal;
}

.knowledge-chips .empty-chip {
  background: transparent;
  color: var(--em-text-muted);
}

.review-box {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px dashed var(--em-border);
}

.review-box label {
  display: block;
  margin-bottom: 8px;
  color: #40526a;
  font-size: 13px;
  font-weight: 600;
}

.review-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

@media (max-width: 760px) {
  .keyword-input,
  .status-select {
    width: 100%;
  }

  .detail-head {
    flex-direction: column;
  }

  .detail-meta {
    text-align: left;
  }
}
</style>
