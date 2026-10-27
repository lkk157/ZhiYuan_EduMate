<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Collection,
  FolderOpened,
  Reading,
  Right,
  UserFilled,
} from '@element-plus/icons-vue'

import { getCourse } from '@/api/course'
import { listMaterials } from '@/api/material'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const course = ref(null)
const materialCounts = ref({})

function difficultyType(level) {
  if (level <= 2) return 'success'
  if (level === 3) return 'info'
  if (level === 4) return 'warning'
  return 'danger'
}

function chapterMaterialCount(chapterId) {
  return materialCounts.value[chapterId] || 0
}

async function load() {
  loading.value = true
  try {
    const body = await getCourse(route.params.id)
    course.value = body?.data || null
    await loadMaterialCounts()
  } catch (error) {
    ElMessage.error(error?.message || '加载课程详情失败')
  } finally {
    loading.value = false
  }
}

async function loadMaterialCounts() {
  if (!course.value) return
  try {
    const body = await listMaterials({
      course_id: course.value.id,
      page_size: 100,
    })
    const counts = {}
    for (const material of body?.data?.items || []) {
      if (material.chapter_id) {
        counts[material.chapter_id] = (counts[material.chapter_id] || 0) + 1
      }
    }
    materialCounts.value = counts
  } catch {
    materialCounts.value = {}
  }
}

function openChapter(chapter) {
  router.push({
    name: 'student-chapter',
    params: { courseId: course.value.id, chapterId: chapter.id },
  })
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="em-page course-detail">
    <div class="editor-topbar">
      <el-button link :icon="ArrowLeft" @click="router.push('/student/courses')">
        返回我的课程
      </el-button>
    </div>
    

    <template v-if="course">
      <section class="hero em-card">
        <div class="hero-letter">{{ course.title.slice(0, 1) }}</div>
        <div class="hero-copy">
          <span class="em-eyebrow">COURSE DETAIL</span>
          <h1>{{ course.title }}</h1>
          <p>{{ course.description || '暂无课程简介' }}</p>
          <div class="hero-meta">
            <span>教师：{{ course.teacher.username }}</span>
            <span><el-icon><Collection /></el-icon>{{ course.chapter_count }} 章节</span>
            <span><el-icon><Reading /></el-icon>{{ course.knowledge_count }} 知识点</span>
            <span><el-icon><UserFilled /></el-icon>{{ course.student_count }} 位同学</span>
          </div>
        </div>
      </section>

      <div class="section-head">
        <div>
          <span class="em-eyebrow">CURRICULUM</span>
          <h2>课程章节</h2>
        </div>
        <span class="section-note">点击章节查看对应学习资料</span>
      </div>

      <section v-if="course.chapters.length" class="chapter-list">
        <article
          v-for="(chapter, index) in course.chapters"
          :key="chapter.id"
          class="chapter-card em-card"
          role="button"
          tabindex="0"
          @click="openChapter(chapter)"
          @keyup.enter="openChapter(chapter)"
        >
          <header>
            <div class="chapter-index">{{ index + 1 }}</div>
            <div class="chapter-title">
              <h3>{{ chapter.title }}</h3>
              <p>{{ chapter.description || '暂无章节说明' }}</p>
            </div>
            <div class="chapter-action">
              <span class="material-count">
                <el-icon><FolderOpened /></el-icon>
                {{ chapterMaterialCount(chapter.id) }} 份资料
              </span>
              <el-icon class="chapter-arrow"><Right /></el-icon>
            </div>
          </header>
          <div class="knowledge-list">
            <div v-for="knowledge in chapter.knowledges" :key="knowledge.id" class="knowledge-item">
              <div class="knowledge-dot" />
              <div class="knowledge-main">
                <strong>{{ knowledge.name }}</strong>
                <small>{{ knowledge.description || '暂无说明' }}</small>
              </div>
              <el-tag size="small" :type="difficultyType(knowledge.difficulty)" effect="light">
                难度 {{ knowledge.difficulty }}
              </el-tag>
            </div>
            <p v-if="!chapter.knowledges.length" class="knowledge-empty">本章暂无知识点</p>
          </div>
        </article>
      </section>

      <el-empty v-else description="课程还没有章节内容" :image-size="100" />
    </template>
  </div>
</template>

<style scoped>
.course-detail {
  display: grid;
  gap: 18px;
}

.hero {
  display: flex;
  align-items: flex-start;
  gap: 26px;
  padding: 30px 34px;
  background:
    radial-gradient(circle at 92% 12%, rgba(22, 119, 255, 0.09), transparent 38%),
    #fff;
}

.hero-letter {
  display: grid;
  width: 82px;
  height: 82px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 22px;
  background: linear-gradient(135deg, #dbeafe, #eff6ff);
  color: #2b5f9e;
  font-size: 36px;
  font-weight: 750;
}

.hero-copy h1 {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.hero-copy p {
  max-width: 820px;
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 16px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.hero-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 20px;
}

.section-note {
  color: var(--em-text-muted);
  font-size: 12px;
}

.chapter-list {
  display: grid;
  gap: 14px;
}

.chapter-card {
  padding: 20px 22px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.chapter-card:hover,
.chapter-card:focus-visible {
  border-color: #bcd7ff;
  box-shadow: 0 12px 30px rgba(22, 119, 255, 0.12);
  outline: none;
  transform: translateY(-2px);
}

.chapter-card header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.chapter-title {
  min-width: 0;
  flex: 1;
}

.chapter-index {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 11px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-weight: 700;
}

.chapter-card h3 {
  font-size: 16px;
}

.chapter-card header p {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.chapter-action {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
}

.material-count {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #f1f6fd;
  color: #5f7796;
  font-size: 11px;
}

.chapter-arrow {
  color: var(--em-primary);
}

.knowledge-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  padding-left: 48px;
}

.knowledge-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border: 1px solid #eef3fa;
  border-radius: 11px;
  background: #fbfdff;
}

.knowledge-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--em-primary);
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

.knowledge-empty {
  padding: 8px 0;
  color: var(--em-text-muted);
  font-size: 12px;
}

@media (max-width: 760px) {
  .hero {
    flex-direction: column;
  }

  .knowledge-list {
    padding-left: 0;
  }

  .chapter-action {
    flex-direction: column;
    align-items: flex-end;
  }
}
</style>
