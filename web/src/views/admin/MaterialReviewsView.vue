<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Refresh, Search, WarningFilled } from '@element-plus/icons-vue'

import {
  downloadMaterial,
  getMaterial,
  listMaterials,
  reviewMaterial,
} from '@/api/material'
import { formatDateTime } from '@/utils/format'
import {
  fileTypeLabel,
  formatFileSize,
  indexStatusLabel,
  indexStatusType,
  materialStatusLabel,
  materialStatusType,
} from '@/utils/material'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const statusFilter = ref('pending')
const indexFilter = ref('')

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const reviewComment = ref('')
const reviewing = ref(false)
const downloading = ref(false)

const pendingCount = computed(() =>
  statusFilter.value === 'pending' ? total.value : null,
)

const statusOptions = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
]
const indexOptions = [
  { value: 'pending', label: '待索引' },
  { value: 'indexing', label: '索引中' },
  { value: 'indexed', label: '已索引' },
  { value: 'failed', label: '索引失败' },
]

async function load() {
  loading.value = true
  try {
    const body = await listMaterials({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      index_status: indexFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载资料列表失败')
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
  indexFilter.value = ''
  search()
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  reviewComment.value = row.review_comment || ''
  try {
    const body = await getMaterial(row.id)
    detail.value = body?.data || null
  } catch (error) {
    ElMessage.error(error?.message || '加载资料详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function approve() {
  try {
    await ElMessageBox.confirm(
      '审核通过后资料将进入课程知识库索引，学生可在课程中下载。确定通过吗？',
      '通过资料审核',
      { type: 'success', confirmButtonText: '通过', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await submitReview('approve')
}

async function reject() {
  if (!reviewComment.value.trim()) {
    ElMessage.warning('驳回资料时必须填写审核意见')
    return
  }
  try {
    await ElMessageBox.confirm(
      '驳回后教师可根据意见替换或重新上传资料。确定驳回吗？',
      '驳回资料',
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
    await reviewMaterial(detail.value.id, {
      decision,
      comment: reviewComment.value.trim() || null,
    })
    ElMessage.success(decision === 'approve' ? '资料已通过审核' : '资料已驳回')
    detailVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '审核操作失败')
  } finally {
    reviewing.value = false
  }
}

async function download(row) {
  downloading.value = true
  try {
    const blob = await downloadMaterial(row.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = row.source_filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(error?.message || '下载资料失败')
  } finally {
    downloading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page material-reviews">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">MATERIAL REVIEW</span>
        <h1>资料审核</h1>
        <p>审核教师上传的课程资料，通过后自动索引到对应课程知识库。</p>
      </div>
      <div v-if="pendingCount !== null" class="pending-chip">
        <strong>{{ pendingCount }}</strong>
        <span>待审核资料</span>
      </div>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-input
          v-model="keyword"
          class="keyword-input"
          placeholder="搜索资料名称"
          :prefix-icon="Search"
          clearable
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="statusFilter" class="filter-select" @change="search">
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-select
          v-model="indexFilter"
          class="filter-select"
          placeholder="全部索引状态"
          clearable
          @change="search"
        >
          <el-option
            v-for="item in indexOptions"
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
      <el-table v-loading="loading" :data="items">
        <el-table-column label="资料" min-width="240">
          <template #default="{ row }">
            <div class="material-cell">
              <span class="file-badge">{{ fileTypeLabel(row.file_type) }}</span>
              <div>
                <strong>{{ row.title }}</strong>
                <small>{{ row.source_filename }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="课程" min-width="160">
          <template #default="{ row }">
            <div class="course-cell">
              <span>{{ row.course_title }}</span>
              <small>{{ row.chapter_title || '未关联章节' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="上传者" width="120">
          <template #default="{ row }">{{ row.uploader?.username || '—' }}</template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="审核状态" width="100">
          <template #default="{ row }">
            <el-tag :type="materialStatusType(row.status)" effect="light">
              {{ materialStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="索引状态" width="110">
          <template #default="{ row }">
            <div class="index-cell">
              <el-tag :type="indexStatusType(row.index_status)" effect="plain">
                {{ indexStatusLabel(row.index_status) }}
              </el-tag>
              <el-tooltip v-if="row.index_error" :content="row.index_error" placement="top">
                <el-icon class="error-icon"><WarningFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="165">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">
              {{ row.status === 'pending' ? '审核' : '查看' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="没有匹配的资料" :image-size="80" />
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

    <el-dialog v-model="detailVisible" title="资料审核" width="680px">
      <div v-loading="detailLoading" class="review-detail">
        <template v-if="detail">
          <div class="detail-head">
            <div class="detail-title">
              <span class="file-badge">{{ fileTypeLabel(detail.file_type) }}</span>
              <div>
                <h2>{{ detail.title }}</h2>
                <p>{{ detail.source_filename }}</p>
              </div>
            </div>
            <div class="detail-tags">
              <el-tag :type="materialStatusType(detail.status)" effect="light">
                {{ materialStatusLabel(detail.status) }}
              </el-tag>
              <el-tag :type="indexStatusType(detail.index_status)" effect="plain">
                {{ indexStatusLabel(detail.index_status) }}
              </el-tag>
            </div>
          </div>

          <div class="meta-grid">
            <div><span>所属课程</span><strong>{{ detail.course_title }}</strong></div>
            <div><span>关联章节</span><strong>{{ detail.chapter_title || '未关联' }}</strong></div>
            <div><span>上传教师</span><strong>{{ detail.uploader?.username || '—' }}</strong></div>
            <div><span>文件大小</span><strong>{{ formatFileSize(detail.file_size) }}</strong></div>
            <div><span>上传时间</span><strong>{{ formatDateTime(detail.created_at) }}</strong></div>
            <div><span>RAG 文档</span><strong>{{ detail.vector_doc_id || '尚未索引' }}</strong></div>
          </div>

          <div v-if="detail.index_error" class="error-banner">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ detail.index_error }}</span>
          </div>

          <div v-if="detail.review_comment" class="comment-banner">
            审核意见：{{ detail.review_comment }}
          </div>

          <div class="detail-actions">
            <el-button :icon="Download" :loading="downloading" @click="download(detail)">
              下载查看
            </el-button>
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
              <el-button type="danger" plain :loading="reviewing" @click="reject">驳回</el-button>
              <el-button type="success" :loading="reviewing" @click="approve">通过审核</el-button>
            </div>
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.material-reviews {
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
  width: 220px;
}

.filter-select {
  width: 150px;
}

.table-card {
  padding: 8px 8px 18px;
}

.material-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-badge {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 11px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 10px;
  font-weight: 700;
}

.material-cell div,
.course-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.35;
}

.material-cell strong {
  font-size: 14px;
}

.material-cell small,
.course-cell small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-cell span {
  font-size: 13px;
}

.index-cell {
  display: flex;
  align-items: center;
  gap: 5px;
}

.error-icon {
  color: var(--em-danger);
  cursor: help;
}

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
  gap: 18px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-title h2 {
  font-size: 20px;
}

.detail-title p {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.detail-tags {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 20px;
  padding: 16px;
  border-radius: 12px;
  background: #f8faff;
}

.meta-grid div {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.meta-grid span {
  color: var(--em-text-muted);
  font-size: 11px;
}

.meta-grid strong {
  margin-top: 2px;
  font-size: 13px;
}

.error-banner,
.comment-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 14px;
  padding: 11px 14px;
  border-radius: 10px;
  font-size: 12px;
}

.error-banner {
  background: #fef2f2;
  color: #b91c1c;
}

.comment-banner {
  background: #fff9ed;
  color: #a16207;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.review-box {
  margin-top: 18px;
  padding-top: 16px;
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
  .filter-select {
    width: 100%;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }

  .detail-head {
    flex-direction: column;
  }
}
</style>
