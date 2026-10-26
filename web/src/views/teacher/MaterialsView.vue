<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete,
  Download,
  FolderOpened,
  Plus,
  Refresh,
  Search,
  UploadFilled,
  WarningFilled,
} from '@element-plus/icons-vue'

import { getCourse, listCourses } from '@/api/course'
import {
  deleteMaterial,
  downloadMaterial,
  fetchRagHealth,
  listMaterials,
  retryMaterialIndex,
  updateMaterialMapping,
  uploadMaterialsBatch,
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

const courses = ref([])
const courseFilter = ref('')
const statusFilter = ref('')
const indexFilter = ref('')
const keyword = ref('')

const ragHealth = ref(null)

const uploadVisible = ref(false)
const uploading = ref(false)
const fileList = ref([])
const chapterOptions = ref([])
const uploadForm = reactive({
  courseId: '',
  title: '',
  chapterId: null,
})

const route = useRoute()
const mappingVisible = ref(false)
const mappingSaving = ref(false)
const mappingRow = ref(null)
const mappingChapterId = ref(null)
const mappingChapters = ref([])

const statusOptions = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: 'deleted', label: '已删除' },
]
const indexOptions = [
  { value: 'pending', label: '待索引' },
  { value: 'indexing', label: '索引中' },
  { value: 'indexed', label: '已索引' },
  { value: 'failed', label: '索引失败' },
]

let pollTimer = null
const needsPolling = computed(() =>
  items.value.some(
    (item) =>
      item.status === 'approved' && ['pending', 'indexing'].includes(item.index_status),
  ),
)

function syncPolling() {
  if (needsPolling.value && !pollTimer) {
    pollTimer = setInterval(() => loadMaterials(true), 4000)
  } else if (!needsPolling.value && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadCourses() {
  try {
    const body = await listCourses({ page_size: 100, status: 'approved' })
    courses.value = body?.data?.items || []
  } catch (error) {
    ElMessage.error(error?.message || '加载课程失败')
  }
}

async function loadMaterials(silent = false) {
  if (!silent) loading.value = true
  try {
    const body = await listMaterials({
      page: page.value,
      page_size: pageSize.value,
      course_id: courseFilter.value || undefined,
      status: statusFilter.value || undefined,
      index_status: indexFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
    syncPolling()
  } catch (error) {
    if (!silent) ElMessage.error(error?.message || '加载资料失败')
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadHealth() {
  try {
    const body = await fetchRagHealth()
    ragHealth.value = body?.data || null
  } catch {
    ragHealth.value = { status: 'unreachable', error: 'RAG 服务不可用' }
  }
}

function search() {
  page.value = 1
  loadMaterials()
}

function resetFilters() {
  courseFilter.value = ''
  statusFilter.value = ''
  indexFilter.value = ''
  keyword.value = ''
  search()
}

async function fetchChapters(courseId) {
  if (!courseId) return []
  try {
    const body = await getCourse(courseId)
    return body?.data?.chapters || []
  } catch {
    return []
  }
}

async function openUpload(preset = {}) {
  const presetCourseId =
    Number(preset.courseId) || (courses.value.length === 1 ? courses.value[0].id : '')
  Object.assign(uploadForm, {
    courseId: presetCourseId,
    title: '',
    chapterId: null,
  })
  fileList.value = []
  chapterOptions.value = []
  uploadVisible.value = true
  if (presetCourseId) {
    await loadChapters(presetCourseId)
    const presetChapterId = Number(preset.chapterId)
    if (presetChapterId) uploadForm.chapterId = presetChapterId
  }
}

async function loadChapters(courseId) {
  chapterOptions.value = await fetchChapters(courseId)
}

async function onCourseChange(value) {
  uploadForm.chapterId = null
  await loadChapters(value)
}

function onFileChange(uploadFile, uploadFiles) {
  const files = uploadFiles || []
  if (files.length === 1) {
    const name = uploadFile.name || uploadFile.raw?.name || ''
    if (!uploadForm.title) uploadForm.title = name.replace(/\.[^.]+$/, '')
  } else {
    uploadForm.title = ''
  }
}

function onFileRemove(_file, uploadFiles) {
  if (!(uploadFiles || []).length) uploadForm.title = ''
}

async function submitUpload() {
  if (!uploadForm.courseId) {
    ElMessage.warning('请选择课程')
    return
  }
  const files = fileList.value.map((item) => item.raw).filter(Boolean)
  if (!files.length) {
    ElMessage.warning('请选择要上传的资料文件')
    return
  }
  uploading.value = true
  try {
    const body = await uploadMaterialsBatch(uploadForm.courseId, files, {
      title: uploadForm.title.trim(),
      chapterId: uploadForm.chapterId,
    })
    const result = body?.data || {}
    if (result.failed) {
      const names = (result.errors || [])
        .map((item) => item.filename)
        .filter(Boolean)
        .join('、')
      ElMessage.warning(
        `${body.message || '部分文件上传失败'}${names ? `：${names}` : ''}`,
      )
    } else {
      ElMessage.success(body.message || `成功上传 ${result.succeeded} 个资料`)
    }
    uploadVisible.value = false
    page.value = 1
    await loadMaterials()
  } catch (error) {
    ElMessage.error(error?.message || '上传资料失败')
  } finally {
    uploading.value = false
  }
}

async function download(row) {
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
    row.download_count += 1
  } catch (error) {
    ElMessage.error(error?.message || '下载资料失败')
  }
}

async function openMapping(row) {
  mappingRow.value = row
  mappingChapterId.value = row.chapter_id || null
  mappingChapters.value = await fetchChapters(row.course_id)
  mappingVisible.value = true
}

async function saveMapping() {
  if (!mappingRow.value) return
  mappingSaving.value = true
  try {
    await updateMaterialMapping(mappingRow.value.id, {
      chapter_id: mappingChapterId.value || null,
      knowledge_id: null,
    })
    ElMessage.success(mappingChapterId.value ? '资料已关联章节' : '已取消章节关联')
    mappingVisible.value = false
    await loadMaterials()
  } catch (error) {
    ElMessage.error(error?.message || '更新章节关联失败')
  } finally {
    mappingSaving.value = false
  }
}

async function retry(row) {
  try {
    await retryMaterialIndex(row.id)
    ElMessage.success('已重新提交索引')
    await loadMaterials(true)
  } catch (error) {
    ElMessage.error(error?.message || '重试索引失败')
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除资料「${row.title}」吗？删除后学生将无法访问，但 RAG 向量暂不删除。`,
      '删除资料',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteMaterial(row.id)
    ElMessage.success('资料已删除')
    await loadMaterials()
  } catch (error) {
    ElMessage.error(error?.message || '删除资料失败')
  }
}

onMounted(async () => {
  await Promise.all([loadCourses(), loadMaterials(), loadHealth()])

  const presetCourseId = Number(route.query.courseId)
  if (presetCourseId) {
    courseFilter.value = presetCourseId
    await loadMaterials()
    if (route.query.upload === '1') {
      await openUpload({
        courseId: presetCourseId,
        chapterId: route.query.chapterId,
      })
    }
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="em-page teacher-materials">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">MATERIAL LIBRARY</span>
        <h1>资料上传</h1>
        <p>上传课程资料，管理员审核通过后自动写入课程 RAG 知识库。</p>
      </div>
      <div class="header-actions">
        <el-tag
          v-if="ragHealth"
          :type="ragHealth.status === 'ok' ? 'success' : 'danger'"
          effect="light"
          round
        >
          RAG {{ ragHealth.status === 'ok' ? '正常' : '异常' }}
        </el-tag>
        <el-button type="primary" size="large" :icon="Plus" @click="openUpload()">
          上传资料
        </el-button>
      </div>
    </div>

    <div v-if="ragHealth && ragHealth.status !== 'ok'" class="health-banner">
      <el-icon><WarningFilled /></el-icon>
      <span>
        智能问答服务当前不可用（{{ ragHealth.error || '连接失败' }}）。资料仍可上传与审核，索引将在服务恢复后重试。
      </span>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-select
          v-model="courseFilter"
          placeholder="全部课程"
          clearable
          class="course-select"
          @change="search"
        >
          <el-option
            v-for="course in courses"
            :key="course.id"
            :label="course.title"
            :value="course.id"
          />
        </el-select>
        <el-select v-model="statusFilter" placeholder="全部审核状态" clearable class="status-select" @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="indexFilter" placeholder="全部索引状态" clearable class="status-select" @change="search">
          <el-option v-for="item in indexOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-input
          v-model="keyword"
          class="keyword-input"
          placeholder="搜索资料名称"
          :prefix-icon="Search"
          clearable
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section class="table-card em-card">
      <el-table v-loading="loading" :data="items">
        <el-table-column label="资料" min-width="260">
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
        <el-table-column label="课程 / 章节" min-width="180">
          <template #default="{ row }">
            <div class="course-cell">
              <span>{{ row.course_title }}</span>
              <small>{{ row.chapter_title || '未关联章节' }}</small>
            </div>
          </template>
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
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="Download" @click="download(row)">下载</el-button>
              <el-button
                link
                type="primary"
                :icon="FolderOpened"
                @click="openMapping(row)"
              >
                关联章节
              </el-button>
              <el-button
                v-if="row.index_status === 'failed'"
                link
                type="warning"
                :icon="Refresh"
                @click="retry(row)"
              >
                重试
              </el-button>
              <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="还没有上传资料" :image-size="80" />
        </template>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadMaterials()"
        />
      </div>
    </section>

    <el-dialog v-model="mappingVisible" title="关联课程章节" width="480px">
      <el-form label-position="top">
        <el-form-item label="资料">
          <div class="mapping-material">
            <strong>{{ mappingRow?.title }}</strong>
            <small>{{ mappingRow?.course_title }}</small>
          </div>
        </el-form-item>
        <el-form-item label="所属章节">
          <el-select v-model="mappingChapterId" class="full-width" placeholder="未关联章节" clearable>
            <el-option
              v-for="chapter in mappingChapters"
              :key="chapter.id"
              :label="chapter.title"
              :value="chapter.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="dialog-hint">
        关联后学生可在对应章节页看到该资料；清空章节即取消关联，资料仍保留在课程资料库中。
      </p>
      <template #footer>
        <el-button @click="mappingVisible = false">取消</el-button>
        <el-button type="primary" :loading="mappingSaving" @click="saveMapping">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="uploadVisible" title="上传课程资料（支持批量）" width="560px">
      <el-form label-position="top">
        <el-form-item label="所属课程" required>
          <el-select v-model="uploadForm.courseId" class="full-width" placeholder="选择已发布课程" @change="onCourseChange">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.id" />
          </el-select>
          <p v-if="!courses.length" class="form-hint">暂无可上传资料的已发布课程</p>
        </el-form-item>
        <el-form-item label="资料标题（单文件时生效）">
          <el-input
            v-model="uploadForm.title"
            placeholder="单文件可自定义标题；多文件自动使用文件名"
            maxlength="200"
            :disabled="fileList.length > 1"
          />
        </el-form-item>
        <el-form-item label="关联章节（选填）">
          <el-select
            v-model="uploadForm.chapterId"
            class="full-width"
            placeholder="选择章节"
            clearable
            :disabled="!uploadForm.courseId"
          >
            <el-option
              v-for="chapter in chapterOptions"
              :key="chapter.id"
              :label="chapter.title"
              :value="chapter.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            v-model:file-list="fileList"
            drag
            multiple
            class="uploader"
            accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg"
            :auto-upload="false"
            :limit="10"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到这里，或 <em>点击选择（可多选）</em></div>
            <template #tip>
              <div class="el-upload__tip">
                一次最多 10 个文件，单个不超过 200MB；支持 PDF / DOCX / PPTX / PNG / JPG / JPEG。多文件时自动使用文件名作为标题。
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <p class="dialog-hint">
        批量上传会逐个保存并提交审核；部分文件失败不会影响已成功的文件。审核通过后自动后台索引到课程知识库。
      </p>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          {{ fileList.length ? `上传 ${fileList.length} 个资料并提交审核` : '上传并提交审核' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.teacher-materials {
  display: grid;
  gap: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.health-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff9ed;
  color: #a16207;
  font-size: 13px;
}

.health-banner .el-icon {
  margin-top: 2px;
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

.course-select {
  width: 210px;
}

.status-select {
  width: 140px;
}

.keyword-input {
  width: 200px;
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

.row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 14px 0;
}

.full-width {
  width: 100%;
}

.mapping-material {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mapping-material strong {
  font-size: 14px;
}

.mapping-material small {
  color: var(--em-text-muted);
  font-size: 12px;
}

.uploader {
  width: 100%;
}

.upload-icon {
  color: var(--em-primary);
  font-size: 42px;
}

.form-hint,
.dialog-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

.dialog-hint {
  margin-top: 4px;
}

@media (max-width: 760px) {
  .course-select,
  .status-select,
  .keyword-input {
    width: 100%;
  }

  .header-actions {
    flex-direction: column;
    align-items: flex-end;
  }
}
</style>
