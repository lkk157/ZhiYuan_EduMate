<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Collection,
  CopyDocument,
  Delete,
  EditPen,
  Key,
  Plus,
  Promotion,
  Reading,
  Refresh,
  UserFilled,
} from '@element-plus/icons-vue'

import {
  addStudent,
  createChapter,
  createKnowledge,
  deleteChapter,
  deleteKnowledge,
  getCourse,
  listCourseStudents,
  removeStudent,
  rotateInvite,
  submitCourse,
  toggleInvite,
  updateChapter,
  updateCourse,
  updateKnowledge,
} from '@/api/course'
import {
  COURSE_STATUS_META,
  canEditCourse,
  canSubmitCourse,
  courseStatusLabel,
  courseStatusType,
  enrollmentSourceLabel,
} from '@/utils/course'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const course = ref(null)
const students = ref([])
const studentsLoading = ref(false)
const studentInput = ref('')
const addingStudent = ref(false)

const canEdit = computed(() => canEditCourse(course.value?.status))
const canSubmit = computed(() => canSubmitCourse(course.value?.status))
const statusMeta = computed(() => COURSE_STATUS_META[course.value?.status] || {})

const courseDialogVisible = ref(false)
const courseFormRef = ref()
const savingCourse = ref(false)
const courseForm = reactive({ title: '', description: '' })

const chapterDialogVisible = ref(false)
const chapterMode = ref('create')
const chapterFormRef = ref()
const savingChapter = ref(false)
const editingChapter = ref(null)
const chapterForm = reactive({ title: '', description: '', order_no: 0 })

const knowledgeDialogVisible = ref(false)
const knowledgeMode = ref('create')
const knowledgeFormRef = ref()
const savingKnowledge = ref(false)
const knowledgeChapter = ref(null)
const editingKnowledge = ref(null)
const knowledgeForm = reactive({ name: '', description: '', difficulty: 3 })

const chapterRules = {
  title: [
    { required: true, message: '请输入章节标题', trigger: 'blur' },
    { max: 100, message: '章节标题不能超过 100 个字符', trigger: 'blur' },
  ],
}

const knowledgeRules = {
  name: [
    { required: true, message: '请输入知识点名称', trigger: 'blur' },
    { max: 100, message: '知识点名称不能超过 100 个字符', trigger: 'blur' },
  ],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }],
}

async function loadCourse() {
  loading.value = true
  try {
    const body = await getCourse(route.params.id)
    course.value = body?.data || null
    if (course.value) {
      await loadStudents()
    }
  } catch (error) {
    ElMessage.error(error?.message || '加载课程失败')
  } finally {
    loading.value = false
  }
}

async function loadStudents() {
  if (!course.value) return
  studentsLoading.value = true
  try {
    const body = await listCourseStudents(course.value.id, { page_size: 100 })
    students.value = body?.data?.items || []
  } catch (error) {
    ElMessage.error(error?.message || '加载学生名单失败')
  } finally {
    studentsLoading.value = false
  }
}

function openCourseEdit() {
  Object.assign(courseForm, {
    title: course.value.title,
    description: course.value.description || '',
  })
  courseDialogVisible.value = true
}

async function saveCourseInfo() {
  try {
    await courseFormRef.value?.validate()
  } catch {
    return
  }
  savingCourse.value = true
  try {
    const body = await updateCourse(course.value.id, {
      title: courseForm.title.trim(),
      description: courseForm.description.trim() || null,
    })
    course.value = body.data
    courseDialogVisible.value = false
    ElMessage.success('课程信息已更新')
  } catch (error) {
    ElMessage.error(error?.message || '更新课程失败')
  } finally {
    savingCourse.value = false
  }
}

async function submitForReview() {
  try {
    await ElMessageBox.confirm(
      '提交后课程内容将暂时锁定，等待管理员审核。确定继续吗？',
      '提交审核',
      { type: 'warning', confirmButtonText: '提交', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const body = await submitCourse(course.value.id)
    course.value = body.data
    ElMessage.success('课程已提交审核')
  } catch (error) {
    ElMessage.error(error?.message || '提交审核失败')
  }
}

async function copyInviteCode() {
  const code = course.value?.invite_code
  if (!code) return
  try {
    await navigator.clipboard?.writeText(code)
    ElMessage.success('邀请码已复制')
  } catch {
    ElMessage.info(`邀请码：${code}`)
  }
}

async function onInviteToggle(value) {
  try {
    const body = await toggleInvite(course.value.id, value)
    course.value.invite_enabled = body.data.invite_enabled
    ElMessage.success(value ? '邀请码已启用' : '邀请码已停用')
  } catch (error) {
    course.value.invite_enabled = !value
    ElMessage.error(error?.message || '更新邀请码状态失败')
  }
}

async function rotateCode() {
  try {
    await ElMessageBox.confirm(
      '轮换后旧邀请码立即失效，已加入的学生不受影响。确定继续吗？',
      '轮换邀请码',
      { type: 'warning', confirmButtonText: '轮换', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const body = await rotateInvite(course.value.id)
    course.value.invite_code = body.data.invite_code
    ElMessage.success('邀请码已轮换')
  } catch (error) {
    ElMessage.error(error?.message || '轮换邀请码失败')
  }
}

function openChapterCreate() {
  chapterMode.value = 'create'
  editingChapter.value = null
  Object.assign(chapterForm, {
    title: '',
    description: '',
    order_no: course.value?.chapters?.length || 0,
  })
  chapterDialogVisible.value = true
}

function openChapterEdit(chapter) {
  chapterMode.value = 'edit'
  editingChapter.value = chapter
  Object.assign(chapterForm, {
    title: chapter.title,
    description: chapter.description || '',
    order_no: chapter.order_no,
  })
  chapterDialogVisible.value = true
}

async function saveChapter() {
  try {
    await chapterFormRef.value?.validate()
  } catch {
    return
  }
  savingChapter.value = true
  try {
    const payload = {
      title: chapterForm.title.trim(),
      description: chapterForm.description.trim() || null,
      order_no: chapterForm.order_no,
    }
    if (chapterMode.value === 'create') {
      await createChapter(course.value.id, payload)
      ElMessage.success('章节已创建')
    } else {
      await updateChapter(course.value.id, editingChapter.value.id, payload)
      ElMessage.success('章节已更新')
    }
    chapterDialogVisible.value = false
    await loadCourse()
  } catch (error) {
    ElMessage.error(error?.message || '保存章节失败')
  } finally {
    savingChapter.value = false
  }
}

async function removeChapter(chapter) {
  try {
    await ElMessageBox.confirm(
      `删除章节「${chapter.title}」会同时删除其下知识点，确定继续吗？`,
      '删除章节',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteChapter(course.value.id, chapter.id)
    ElMessage.success('章节已删除')
    await loadCourse()
  } catch (error) {
    ElMessage.error(error?.message || '删除章节失败')
  }
}

function openKnowledgeCreate(chapter) {
  knowledgeMode.value = 'create'
  knowledgeChapter.value = chapter
  editingKnowledge.value = null
  Object.assign(knowledgeForm, { name: '', description: '', difficulty: 3 })
  knowledgeDialogVisible.value = true
}

function openKnowledgeEdit(chapter, knowledge) {
  knowledgeMode.value = 'edit'
  knowledgeChapter.value = chapter
  editingKnowledge.value = knowledge
  Object.assign(knowledgeForm, {
    name: knowledge.name,
    description: knowledge.description || '',
    difficulty: knowledge.difficulty,
  })
  knowledgeDialogVisible.value = true
}

async function saveKnowledge() {
  try {
    await knowledgeFormRef.value?.validate()
  } catch {
    return
  }
  savingKnowledge.value = true
  try {
    const payload = {
      name: knowledgeForm.name.trim(),
      description: knowledgeForm.description.trim() || null,
      difficulty: knowledgeForm.difficulty,
    }
    if (knowledgeMode.value === 'create') {
      await createKnowledge(course.value.id, knowledgeChapter.value.id, payload)
      ElMessage.success('知识点已添加')
    } else {
      await updateKnowledge(
        course.value.id,
        knowledgeChapter.value.id,
        editingKnowledge.value.id,
        payload,
      )
      ElMessage.success('知识点已更新')
    }
    knowledgeDialogVisible.value = false
    await loadCourse()
  } catch (error) {
    ElMessage.error(error?.message || '保存知识点失败')
  } finally {
    savingKnowledge.value = false
  }
}

async function removeKnowledge(chapter, knowledge) {
  try {
    await ElMessageBox.confirm(
      `确定删除知识点「${knowledge.name}」吗？`,
      '删除知识点',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteKnowledge(course.value.id, chapter.id, knowledge.id)
    ElMessage.success('知识点已删除')
    await loadCourse()
  } catch (error) {
    ElMessage.error(error?.message || '删除知识点失败')
  }
}

async function submitAddStudent() {
  const username = studentInput.value.trim()
  if (!username) {
    ElMessage.warning('请输入学生用户名')
    return
  }
  addingStudent.value = true
  try {
    const body = await addStudent(course.value.id, username)
    ElMessage.success(body.message || '学生已加入课程')
    studentInput.value = ''
    await loadStudents()
    course.value.student_count = students.value.length
  } catch (error) {
    ElMessage.error(error?.message || '添加学生失败')
  } finally {
    addingStudent.value = false
  }
}

async function removeFromCourse(student) {
  try {
    await ElMessageBox.confirm(
      `确定将「${student.username}」移出课程吗？移出后该学生将无法访问课程内容。`,
      '移出学生',
      { type: 'warning', confirmButtonText: '移出', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await removeStudent(course.value.id, student.student_id)
    ElMessage.success('学生已移出课程')
    await loadStudents()
    course.value.student_count = students.value.length
  } catch (error) {
    ElMessage.error(error?.message || '移出学生失败')
  }
}

function difficultyType(level) {
  if (level <= 2) return 'success'
  if (level === 3) return 'info'
  if (level === 4) return 'warning'
  return 'danger'
}

onMounted(loadCourse)
</script>

<template>
  <div v-loading="loading" class="em-page course-editor">
    <div class="editor-topbar">
      <el-button link :icon="ArrowLeft" @click="router.push('/teacher/courses')">
        返回课程列表
      </el-button>
    </div>

    <template v-if="course">
      <section class="hero em-card">
        <div class="hero-copy">
          <div class="hero-tags">
            <el-tag :type="courseStatusType(course.status)" effect="light" round>
              {{ courseStatusLabel(course.status) }}
            </el-tag>
            <span class="hero-hint">{{ statusMeta.hint }}</span>
          </div>
          <h1>{{ course.title }}</h1>
          <p>{{ course.description || '暂无课程简介' }}</p>
          <div class="hero-stats">
            <span><el-icon><Collection /></el-icon>{{ course.chapter_count }} 章节</span>
            <span><el-icon><Reading /></el-icon>{{ course.knowledge_count }} 知识点</span>
            <span><el-icon><UserFilled /></el-icon>{{ course.student_count }} 学生</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button v-if="canEdit" :icon="EditPen" @click="openCourseEdit">
            编辑课程信息
          </el-button>
          <el-button
            v-if="canSubmit"
            type="primary"
            :icon="Promotion"
            @click="submitForReview"
          >
            提交审核
          </el-button>
        </div>
      </section>

      <div v-if="!canEdit" class="locked-banner">
        <el-icon><Key /></el-icon>
        <span v-if="course.status === 'pending'">
          课程正在审核中，章节与知识点暂时锁定。审核通过或驳回后可继续操作。
        </span>
        <span v-else>
          课程已发布，结构内容已锁定以保持审核一致性；你仍可管理邀请码、轮换代码与学生名单。
        </span>
      </div>

      <div v-if="course.status === 'rejected' && course.review_comment" class="reject-banner">
        <strong>管理员审核意见</strong>
        <span>{{ course.review_comment }}</span>
      </div>

      <div class="editor-grid">
        <section class="chapters-panel em-card">
          <div class="panel-head">
            <div>
              <span class="em-eyebrow">CURRICULUM</span>
              <h2>章节与知识点</h2>
            </div>
            <el-button v-if="canEdit" type="primary" plain :icon="Plus" @click="openChapterCreate">
              添加章节
            </el-button>
          </div>

          <div v-if="course.chapters.length" class="chapter-list">
            <article v-for="(chapter, index) in course.chapters" :key="chapter.id" class="chapter-card">
              <header class="chapter-head">
                <div class="chapter-index">{{ index + 1 }}</div>
                <div class="chapter-title">
                  <h3>{{ chapter.title }}</h3>
                  <p>{{ chapter.description || '暂无章节说明' }}</p>
                </div>
                <div v-if="canEdit" class="chapter-actions">
                  <el-button link type="primary" @click="openChapterEdit(chapter)">编辑</el-button>
                  <el-button link type="danger" @click="removeChapter(chapter)">删除</el-button>
                </div>
              </header>

              <div class="knowledge-list">
                <div
                  v-for="knowledge in chapter.knowledges"
                  :key="knowledge.id"
                  class="knowledge-item"
                >
                  <div class="knowledge-main">
                    <strong>{{ knowledge.name }}</strong>
                    <small>{{ knowledge.description || '暂无说明' }}</small>
                  </div>
                  <el-tag size="small" :type="difficultyType(knowledge.difficulty)" effect="light">
                    难度 {{ knowledge.difficulty }}
                  </el-tag>
                  <div v-if="canEdit" class="knowledge-actions">
                    <el-button link type="primary" @click="openKnowledgeEdit(chapter, knowledge)">
                      编辑
                    </el-button>
                    <el-button link type="danger" @click="removeKnowledge(chapter, knowledge)">
                      删除
                    </el-button>
                  </div>
                </div>

                <p v-if="!chapter.knowledges.length" class="knowledge-empty">
                  暂无知识点
                </p>
              </div>

              <el-button
                v-if="canEdit"
                class="add-knowledge"
                link
                type="primary"
                :icon="Plus"
                @click="openKnowledgeCreate(chapter)"
              >
                添加知识点
              </el-button>
            </article>
          </div>

          <el-empty v-else description="还没有章节，先添加课程章节" :image-size="90">
            <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openChapterCreate">
              添加章节
            </el-button>
          </el-empty>
        </section>

        <aside class="side-panel">
          <section class="invite-card em-card">
            <div class="panel-head">
              <div>
                <span class="em-eyebrow">INVITATION</span>
                <h2>课程邀请码</h2>
              </div>
              <el-switch
                v-model="course.invite_enabled"
                @change="onInviteToggle"
              />
            </div>
            <p class="side-hint">
              学生凭邀请码加入课程。仅课程发布且邀请码启用时有效。
            </p>
            <div class="invite-code">{{ course.invite_code || '—' }}</div>
            <div class="invite-actions">
              <el-button :icon="CopyDocument" @click="copyInviteCode">复制</el-button>
              <el-button :icon="Refresh" @click="rotateCode">轮换</el-button>
            </div>
          </section>

          <section class="roster-card em-card">
            <div class="panel-head">
              <div>
                <span class="em-eyebrow">ROSTER</span>
                <h2>学生名单</h2>
              </div>
              <el-tag effect="plain" round>{{ students.length }} 人</el-tag>
            </div>

            <div class="student-add">
              <el-input
                v-model="studentInput"
                placeholder="输入学生用户名"
                :disabled="course.status !== 'approved'"
                @keyup.enter="submitAddStudent"
              />
              <el-button
                type="primary"
                :loading="addingStudent"
                :disabled="course.status !== 'approved'"
                @click="submitAddStudent"
              >
                添加
              </el-button>
            </div>
            <p v-if="course.status !== 'approved'" class="side-hint">
              课程发布后才能添加学生。
            </p>

            <div v-loading="studentsLoading" class="student-list">
              <div v-for="student in students" :key="student.student_id" class="student-item">
                <div class="student-avatar">
                  {{ student.username.slice(0, 1).toUpperCase() }}
                </div>
                <div class="student-meta">
                  <strong>{{ student.username }}</strong>
                  <small>{{ student.email || '未设置邮箱' }}</small>
                </div>
                <div class="student-side">
                  <span class="source-tag">{{ enrollmentSourceLabel(student.source) }}</span>
                  <el-button link type="danger" :icon="Delete" @click="removeFromCourse(student)" />
                </div>
              </div>
              <p v-if="!students.length" class="roster-empty">暂无学生加入</p>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <el-dialog v-model="courseDialogVisible" title="编辑课程信息" width="540px">
      <el-form ref="courseFormRef" :model="courseForm" :rules="chapterRules" label-position="top">
        <el-form-item label="课程名称" prop="title">
          <el-input v-model="courseForm.title" />
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input
            v-model="courseForm.description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCourse" @click="saveCourseInfo">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="chapterDialogVisible"
      :title="chapterMode === 'create' ? '添加章节' : '编辑章节'"
      width="520px"
    >
      <el-form ref="chapterFormRef" :model="chapterForm" :rules="chapterRules" label-position="top">
        <el-form-item label="章节标题" prop="title">
          <el-input v-model="chapterForm.title" placeholder="例如：第一章 绪论" />
        </el-form-item>
        <el-form-item label="章节说明">
          <el-input
            v-model="chapterForm.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="排序序号">
          <el-input-number v-model="chapterForm.order_no" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingChapter" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="knowledgeDialogVisible"
      :title="knowledgeMode === 'create' ? '添加知识点' : '编辑知识点'"
      width="520px"
    >
      <el-form
        ref="knowledgeFormRef"
        :model="knowledgeForm"
        :rules="knowledgeRules"
        label-position="top"
      >
        <el-form-item label="知识点名称" prop="name">
          <el-input v-model="knowledgeForm.name" placeholder="例如：监督学习" />
        </el-form-item>
        <el-form-item label="知识点说明">
          <el-input
            v-model="knowledgeForm.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="难度（1-5）" prop="difficulty">
          <el-rate v-model="knowledgeForm.difficulty" :max="5" show-score />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="knowledgeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingKnowledge" @click="saveKnowledge">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.course-editor {
  display: grid;
  gap: 18px;
}

.editor-topbar {
  margin-bottom: -4px;
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
  background:
    radial-gradient(circle at 92% 12%, rgba(22, 119, 255, 0.08), transparent 36%),
    #fff;
}

.hero-tags {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hero-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

.hero h1 {
  margin-top: 14px;
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.hero p {
  max-width: 760px;
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 16px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.hero-stats span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.hero-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
}

.locked-banner,
.reject-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 16px;
  border-radius: 12px;
  font-size: 13px;
}

.locked-banner {
  background: #fff9ed;
  color: #a16207;
}

.locked-banner .el-icon {
  margin-top: 2px;
}

.reject-banner {
  flex-direction: column;
  gap: 3px;
  background: #fef2f2;
  color: #b91c1c;
}

.reject-banner strong {
  font-size: 12px;
}

.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.chapters-panel,
.invite-card,
.roster-card {
  padding: 22px 24px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.panel-head h2 {
  margin-top: 4px;
  font-size: 18px;
}

.chapter-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.chapter-card {
  padding: 16px 18px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fbfdff;
}

.chapter-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.chapter-index {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-weight: 700;
}

.chapter-title {
  min-width: 0;
  flex: 1;
}

.chapter-title h3 {
  font-size: 15px;
}

.chapter-title p {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.chapter-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 2px;
}

.knowledge-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-left: 46px;
}

.knowledge-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #eef3fa;
}

.knowledge-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  line-height: 1.35;
}

.knowledge-main strong {
  font-size: 13px;
}

.knowledge-main small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.knowledge-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 2px;
}

.knowledge-empty {
  padding: 10px 0;
  color: var(--em-text-muted);
  font-size: 12px;
}

.add-knowledge {
  margin: 10px 0 0 46px;
}

.side-panel {
  display: grid;
  gap: 18px;
}

.side-hint {
  margin-top: 8px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.invite-code {
  margin-top: 16px;
  padding: 16px;
  border: 1px dashed #bcd7fb;
  border-radius: 12px;
  background: var(--em-primary-softer);
  color: var(--em-primary);
  font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-align: center;
}

.invite-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.invite-actions :deep(.el-button) {
  flex: 1;
}

.student-add {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.student-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  min-height: 50px;
}

.student-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 11px;
  background: #f8faff;
}

.student-avatar {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #74b4ff);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.student-meta {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  line-height: 1.3;
}

.student-meta strong {
  font-size: 13px;
}

.student-meta small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.student-side {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}

.source-tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef4fc;
  color: #607790;
  font-size: 10px;
}

.roster-empty {
  padding: 16px 0;
  color: var(--em-text-muted);
  font-size: 12px;
  text-align: center;
}

@media (max-width: 1180px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero {
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
  }

  .knowledge-list {
    padding-left: 0;
  }

  .add-knowledge {
    margin-left: 0;
  }
}
</style>
