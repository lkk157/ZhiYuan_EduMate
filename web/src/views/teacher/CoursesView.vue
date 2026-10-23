<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  EditPen,
  Plus,
  Promotion,
  Reading,
  User,
} from '@element-plus/icons-vue'

import {
  createCourse,
  listCourses,
  submitCourse,
  updateCourse,
} from '@/api/course'
import {
  COURSE_STATUS_META,
  canEditCourse,
  canSubmitCourse,
  courseStatusLabel,
  courseStatusType,
} from '@/utils/course'
import { formatDateTime } from '@/utils/format'

const router = useRouter()

const loading = ref(false)
const courses = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(9)
const statusFilter = ref('')

const dialogVisible = ref(false)
const dialogMode = ref('create')
const saving = ref(false)
const formRef = ref()
const editing = ref(null)
const form = reactive({ title: '', description: '' })

const formRules = {
  title: [
    { required: true, message: '请输入课程名称', trigger: 'blur' },
    { min: 2, max: 100, message: '课程名称长度为 2-100 个字符', trigger: 'blur' },
  ],
}

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
      status: statusFilter.value || undefined,
    })
    courses.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载课程失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  load()
}

function openCreate() {
  dialogMode.value = 'create'
  editing.value = null
  Object.assign(form, { title: '', description: '' })
  dialogVisible.value = true
}

function openEdit(course) {
  dialogMode.value = 'edit'
  editing.value = course
  Object.assign(form, { title: course.title, description: course.description || '' })
  dialogVisible.value = true
}

async function saveCourse() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      const body = await createCourse({
        title: form.title.trim(),
        description: form.description.trim() || null,
      })
      ElMessage.success('课程已创建，请继续添加章节与知识点')
      dialogVisible.value = false
      router.push(`/teacher/courses/${body.data.id}`)
    } else {
      await updateCourse(editing.value.id, {
        title: form.title.trim(),
        description: form.description.trim() || null,
      })
      ElMessage.success('课程信息已更新')
      dialogVisible.value = false
      await load()
    }
  } catch (error) {
    ElMessage.error(error?.message || '保存课程失败')
  } finally {
    saving.value = false
  }
}

async function submitForReview(course) {
  try {
    await ElMessageBox.confirm(
      `确定提交「${course.title}」进行审核吗？提交后课程内容将暂时锁定。`,
      '提交审核',
      { type: 'warning', confirmButtonText: '提交', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await submitCourse(course.id)
    ElMessage.success('课程已提交审核')
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '提交审核失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page teacher-courses">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">COURSE STUDIO</span>
        <h1>课程管理</h1>
        <p>创建课程、维护章节与知识点，提交管理员审核后即可邀请学生加入。</p>
      </div>
      <el-button type="primary" size="large" :icon="Plus" @click="openCreate">
        创建课程
      </el-button>
    </div>

    <section class="toolbar em-card">
      <div class="toolbar-left">
        <el-select
          v-model="statusFilter"
          placeholder="全部状态"
          clearable
          class="status-select"
          @change="onFilterChange"
        >
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <span class="toolbar-count">共 {{ total }} 门课程</span>
      </div>
      <span class="toolbar-hint">草稿与已驳回课程可编辑；待审核课程内容锁定。</span>
    </section>

    <section v-loading="loading" class="course-grid">
      <article v-for="course in courses" :key="course.id" class="course-card em-card">
        <div class="course-cover" :class="`cover-${course.status}`">
          <span class="cover-letter">{{ course.title.slice(0, 1) }}</span>
          <el-tag :type="courseStatusType(course.status)" effect="dark" round>
            {{ courseStatusLabel(course.status) }}
          </el-tag>
        </div>

        <div class="course-body">
          <div class="course-title-row">
            <h3>{{ course.title }}</h3>
            <span class="course-date">{{ formatDateTime(course.created_at) }}</span>
          </div>
          <p class="course-desc">{{ course.description || '暂无课程简介' }}</p>

          <div class="course-stats">
            <span><el-icon><Collection /></el-icon>{{ course.chapter_count }} 章节</span>
            <span><el-icon><Reading /></el-icon>{{ course.knowledge_count }} 知识点</span>
            <span><el-icon><User /></el-icon>{{ course.student_count }} 学生</span>
          </div>

          <div v-if="course.status === 'rejected' && course.review_comment" class="review-note">
            <strong>审核意见</strong>
            <span>{{ course.review_comment }}</span>
          </div>

          <div class="course-actions">
            <router-link :to="`/teacher/courses/${course.id}`" class="manage-link">
              <el-button type="primary" plain>
                管理课程
              </el-button>
            </router-link>
            <el-button
              v-if="canEditCourse(course.status)"
              :icon="EditPen"
              @click="openEdit(course)"
            >
              编辑
            </el-button>
            <el-button
              v-if="canSubmitCourse(course.status)"
              type="success"
              plain
              :icon="Promotion"
              @click="submitForReview(course)"
            >
              提交审核
            </el-button>
          </div>
        </div>
      </article>

      <div v-if="!loading && !courses.length" class="empty-card em-card">
        <div class="empty-icon"><el-icon><Collection /></el-icon></div>
        <h3>还没有课程</h3>
        <p>创建第一门课程，添加章节与知识点后提交审核。</p>
        <el-button type="primary" :icon="Plus" @click="openCreate">创建课程</el-button>
      </div>
    </section>

    <div v-if="total > pageSize" class="pagination-row">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="load"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '创建课程' : '编辑课程'"
      width="540px"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
        <el-form-item label="课程名称" prop="title">
          <el-input v-model="form.title" placeholder="例如：人工智能基础入门" />
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="介绍课程目标、适用对象与主要内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">
          {{ dialogMode === 'create' ? '创建并编辑' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.teacher-courses {
  display: grid;
  gap: 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-select {
  width: 150px;
}

.toolbar-count {
  color: var(--em-text-secondary);
  font-size: 13px;
}

.toolbar-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  min-height: 220px;
}

.course-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 38px rgba(31, 45, 61, 0.1);
}

.course-cover {
  position: relative;
  display: flex;
  height: 112px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 20px;
  background:
    radial-gradient(circle at 85% 20%, rgba(255, 255, 255, 0.45), transparent 40%),
    linear-gradient(135deg, #dbeafe, #eff6ff);
}

.cover-pending {
  background: linear-gradient(135deg, #fef3c7, #fffbeb);
}

.cover-approved {
  background: linear-gradient(135deg, #d1fae5, #f0fdf4);
}

.cover-rejected {
  background: linear-gradient(135deg, #fee2e2, #fef2f2);
}

.cover-letter {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  color: #2b5f9e;
  font-size: 24px;
  font-weight: 750;
}

.course-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding: 18px 20px 20px;
}

.course-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.course-title-row h3 {
  font-size: 17px;
  line-height: 1.35;
}

.course-date {
  flex: 0 0 auto;
  color: var(--em-text-muted);
  font-size: 11px;
}

.course-desc {
  display: -webkit-box;
  min-height: 42px;
  margin-top: 8px;
  overflow: hidden;
  color: var(--em-text-secondary);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.course-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 14px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.course-stats span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.review-note {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
}

.review-note strong {
  font-size: 11px;
}

.course-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: auto;
  padding-top: 18px;
}

.manage-link {
  display: inline-flex;
}

.empty-card {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 24px;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border-radius: 20px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 28px;
}

.empty-card h3 {
  margin-top: 16px;
  font-size: 18px;
}

.empty-card p {
  margin: 6px 0 18px;
  color: var(--em-text-secondary);
}

.pagination-row {
  display: flex;
  justify-content: center;
}

@media (max-width: 1180px) {
  .course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .course-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-hint {
    display: none;
  }
}
</style>
