<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Collection,
  Notebook,
  Reading,
  Right,
  UserFilled,
} from '@element-plus/icons-vue'

import { joinCourse, listCourses } from '@/api/course'
import { formatDateTime } from '@/utils/format'

const loading = ref(false)
const courses = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(9)
const inviteInput = ref('')
const joining = ref(false)

async function load() {
  loading.value = true
  try {
    const body = await listCourses({ page: page.value, page_size: pageSize.value })
    courses.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载课程失败')
  } finally {
    loading.value = false
  }
}

async function submitJoin() {
  const code = inviteInput.value.trim()
  if (!code) {
    ElMessage.warning('请输入课程邀请码')
    return
  }
  joining.value = true
  try {
    const body = await joinCourse(code)
    ElMessage.success(body.message || '已加入课程')
    inviteInput.value = ''
    page.value = 1
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '加入课程失败')
  } finally {
    joining.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page student-courses">
    <section class="join-hero em-card">
      <div class="join-copy">
        <span class="em-eyebrow">JOIN A COURSE</span>
        <h1>我的课程</h1>
        <p>输入教师提供的邀请码加入课程，查看章节、知识点与课程资料。</p>
      </div>
      <div class="join-form">
        <el-input
          v-model="inviteInput"
          size="large"
          placeholder="输入课程邀请码"
          maxlength="16"
          clearable
          @keyup.enter="submitJoin"
        />
        <el-button
          type="primary"
          size="large"
          :loading="joining"
          @click="submitJoin"
        >
          加入课程
        </el-button>
      </div>
    </section>

    <div class="section-head">
      <div>
        <span class="em-eyebrow">ENROLLED COURSES</span>
        <h2>已加入的课程</h2>
      </div>
      <span class="section-count">共 {{ total }} 门</span>
    </div>

    <section v-loading="loading" class="course-grid">
      <router-link
        v-for="course in courses"
        :key="course.id"
        :to="`/student/courses/${course.id}`"
        class="course-card em-card"
      >
        <div class="course-cover">
          <span class="cover-letter">{{ course.title.slice(0, 1) }}</span>
          <el-tag type="success" effect="dark" round>已加入</el-tag>
        </div>
        <div class="course-body">
          <div class="course-title-row">
            <h3>{{ course.title }}</h3>
            <el-icon class="go-icon"><Right /></el-icon>
          </div>
          <p class="course-desc">{{ course.description || '暂无课程简介' }}</p>
          <div class="course-meta">
            <span>教师 {{ course.teacher.username }}</span>
            <span>加入于 {{ formatDateTime(course.created_at) }}</span>
          </div>
          <div class="course-stats">
            <span><el-icon><Collection /></el-icon>{{ course.chapter_count }} 章节</span>
            <span><el-icon><Reading /></el-icon>{{ course.knowledge_count }} 知识点</span>
            <span><el-icon><UserFilled /></el-icon>{{ course.student_count }} 同学</span>
          </div>
        </div>
      </router-link>

      <div v-if="!loading && !courses.length" class="empty-card em-card">
        <div class="empty-icon"><el-icon><Notebook /></el-icon></div>
        <h3>还没有加入课程</h3>
        <p>向教师获取邀请码，在上方输入即可加入课程。</p>
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
  </div>
</template>

<style scoped>
.student-courses {
  display: grid;
  gap: 20px;
}

.join-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: 30px 34px;
  background:
    radial-gradient(circle at 90% 15%, rgba(22, 119, 255, 0.1), transparent 36%),
    linear-gradient(135deg, #ffffff, #f4f9ff);
}

.join-copy h1 {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.join-copy p {
  margin-top: 6px;
  color: var(--em-text-secondary);
}

.join-form {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
}

.join-form :deep(.el-input) {
  width: 230px;
}

.join-form :deep(.el-input__wrapper) {
  height: 44px;
  border-radius: 12px;
  background: #fff;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 20px;
}

.section-count {
  color: var(--em-text-muted);
  font-size: 12px;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  min-height: 180px;
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
  display: flex;
  height: 104px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 20px;
  background:
    radial-gradient(circle at 85% 20%, rgba(255, 255, 255, 0.5), transparent 40%),
    linear-gradient(135deg, #dbeafe, #eff6ff);
}

.cover-letter {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.84);
  color: #2b5f9e;
  font-size: 23px;
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
}

.go-icon {
  color: var(--em-primary);
}

.course-desc {
  display: -webkit-box;
  min-height: 40px;
  margin-top: 8px;
  overflow: hidden;
  color: var(--em-text-secondary);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.course-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.course-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--em-border);
  color: var(--em-text-muted);
  font-size: 12px;
}

.course-stats span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
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
  margin-top: 6px;
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

@media (max-width: 860px) {
  .join-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .join-form {
    width: 100%;
  }

  .join-form :deep(.el-input) {
    flex: 1;
    width: auto;
  }
}

@media (max-width: 660px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
