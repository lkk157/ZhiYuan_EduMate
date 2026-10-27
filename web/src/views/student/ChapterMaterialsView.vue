<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Collection,
  Download,
  FolderOpened,
  Reading,
  View,
} from '@element-plus/icons-vue'

import { getCourse } from '@/api/course'
import { downloadMaterial, listMaterials } from '@/api/material'
import MaterialPreviewDialog from '@/components/MaterialPreviewDialog.vue'
import { fileTypeLabel, formatFileSize } from '@/utils/material'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const course = ref(null)
const materials = ref([])
const previewVisible = ref(false)
const previewItem = ref(null)

const chapter = computed(() => {
  const chapterId = Number(route.params.chapterId)
  return course.value?.chapters?.find((item) => item.id === chapterId) || null
})

function difficultyType(level) {
  if (level <= 2) return 'success'
  if (level === 3) return 'info'
  if (level === 4) return 'warning'
  return 'danger'
}

async function load() {
  loading.value = true
  try {
    const body = await getCourse(route.params.courseId)
    course.value = body?.data || null
    if (!chapter.value) {
      ElMessage.error('章节不存在或已被移除')
      router.replace(`/student/courses/${route.params.courseId}`)
      return
    }
    const listed = await listMaterials({
      course_id: route.params.courseId,
      chapter_id: route.params.chapterId,
      page_size: 100,
    })
    materials.value = listed?.data?.items || []
  } catch (error) {
    ElMessage.error(error?.message || '加载章节资料失败')
  } finally {
    loading.value = false
  }
}

function openPreview(material) {
  previewItem.value = material
  previewVisible.value = true
}

async function download(material) {
  try {
    const blob = await downloadMaterial(material.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = material.source_filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
    material.download_count += 1
  } catch (error) {
    ElMessage.error(error?.message || '下载资料失败')
  }
}

function backToCourse() {
  router.push(`/student/courses/${route.params.courseId}`)
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="em-page chapter-materials">
    <div class="editor-topbar">
      <el-button link :icon="ArrowLeft" @click="backToCourse">
        返回课程详情
      </el-button>
    </div>
    

    <template v-if="chapter">
      <section class="hero em-card">
        <div class="hero-index">{{ chapter.order_no + 1 }}</div>
        <div class="hero-copy">
          <span class="em-eyebrow">CHAPTER MATERIALS</span>
          <h1>{{ chapter.title }}</h1>
          <p>{{ chapter.description || '暂无章节说明' }}</p>
          <div class="hero-meta">
            <span><el-icon><Collection /></el-icon>{{ course.title }}</span>
            <span><el-icon><Reading /></el-icon>{{ chapter.knowledges.length }} 知识点</span>
            <span><el-icon><FolderOpened /></el-icon>{{ materials.length }} 份资料</span>
          </div>
        </div>
      </section>

      <section v-if="chapter.knowledges.length" class="knowledge-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">KNOWLEDGE POINTS</span>
            <h2>本章知识点</h2>
          </div>
        </div>
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
        </div>
      </section>

      <div class="section-head">
        <div>
          <span class="em-eyebrow">MATERIALS</span>
          <h2>章节资料</h2>
        </div>
        <span class="section-note">{{ materials.length }} 份已发布资料</span>
      </div>

      <section v-if="materials.length" class="material-grid">
        <article v-for="material in materials" :key="material.id" class="material-card em-card">
          <span class="file-badge">{{ fileTypeLabel(material.file_type) }}</span>
          <div class="material-info">
            <strong>{{ material.title }}</strong>
            <small>{{ material.source_filename }}</small>
            <span>
              {{ formatFileSize(material.file_size) }} · 浏览 {{ material.view_count }} · 下载
              {{ material.download_count }}
            </span>
            <span v-if="material.knowledge_id" class="knowledge-tag">
              {{ material.knowledge_title || '关联知识点' }}
            </span>
          </div>
          <div class="material-actions">
            <el-button type="primary" plain :icon="View" @click="openPreview(material)">
              预览
            </el-button>
            <el-button type="primary" plain :icon="Download" @click="download(material)">
              下载
            </el-button>
          </div>
        </article>
      </section>

      <div v-else class="empty-card em-card">
        <div class="empty-icon"><el-icon><FolderOpened /></el-icon></div>
        <h3>本章暂无资料</h3>
        <p>教师为该章节上传并通过审核的资料会显示在这里。</p>
      </div>
    </template>

    <MaterialPreviewDialog v-model="previewVisible" :material="previewItem" />
  </div>
</template>

<style scoped>
.chapter-materials {
  display: grid;
  gap: 18px;
}

.hero {
  display: flex;
  align-items: flex-start;
  gap: 22px;
  padding: 28px 32px;
  background:
    radial-gradient(circle at 92% 12%, rgba(22, 119, 255, 0.09), transparent 38%),
    #fff;
}

.hero-index {
  display: grid;
  width: 64px;
  height: 64px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 18px;
  background: linear-gradient(135deg, #dbeafe, #eff6ff);
  color: #2b5f9e;
  font-size: 26px;
  font-weight: 750;
}

.hero-copy h1 {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.hero-copy p {
  max-width: 780px;
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 14px;
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

.knowledge-card {
  padding: 22px 24px;
}

.knowledge-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
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

.material-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.material-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

.file-badge {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 10px;
  font-weight: 700;
}

.material-info {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  line-height: 1.35;
}

.material-info strong {
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-info small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-info span {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 10px;
}

.knowledge-tag {
  color: var(--em-primary) !important;
}

.material-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 6px;
}

.material-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.empty-card {
  display: flex;
  min-height: 220px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 18px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 25px;
}

.empty-card h3 {
  margin-top: 14px;
  font-size: 16px;
}

.empty-card p {
  margin-top: 4px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .hero {
    flex-direction: column;
  }

  .material-grid {
    grid-template-columns: 1fr;
  }
}
</style>
