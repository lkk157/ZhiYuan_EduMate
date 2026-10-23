<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Aim,
  ChatDotRound,
  Collection,
  FolderOpened,
  Notebook,
  Reading,
  Star,
} from '@element-plus/icons-vue'

import { getStudentHome } from '@/api/home'
import { markMaterialViewed } from '@/api/material'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'
import { fileTypeLabel } from '@/utils/material'

const auth = useAuthStore()
const router = useRouter()

function emptyHome() {
  return {
    stats: {
      course_count: 0,
      weekly_questions: 0,
      recommendation_count: 0,
      personal_material_count: 0,
      average_mastery: null,
    },
    courses: [],
    hot: [],
    recommendations: { seed: null, same_chapter: [], similar: [] },
    recent_personal: [],
  }
}

const loading = ref(false)
const home = ref(emptyHome())

const stats = computed(() => [
  {
    label: '在学课程',
    value: home.value.stats.course_count,
    hint: '已加入的课程',
    icon: 'Notebook',
    tone: 'blue',
  },
  {
    label: '本周问答',
    value: home.value.stats.weekly_questions,
    hint: '近 7 天提问次数',
    icon: 'ChatDotRound',
    tone: 'green',
  },
  {
    label: '推荐资料',
    value: home.value.stats.recommendation_count,
    hint: '热门 / 同章节 / 相似',
    icon: 'Star',
    tone: 'orange',
  },
  {
    label: '个人资料',
    value: home.value.stats.personal_material_count,
    hint: '我的知识库',
    icon: 'FolderOpened',
    tone: 'purple',
  },
])

const recommendationGroups = computed(() =>
  [
    {
      key: 'same_chapter',
      title: '同章节推荐',
      description: '和你最近浏览的资料处在同一章节',
      items: home.value.recommendations.same_chapter,
    },
    {
      key: 'similar',
      title: '相似资料',
      description: '和你最近浏览的资料共享知识点',
      items: home.value.recommendations.similar,
    },
  ].filter((group) => group.items.length > 0),
)

const hasCourses = computed(() => home.value.courses.length > 0)
const hasRecommendations = computed(
  () => home.value.recommendations.same_chapter.length > 0 || home.value.recommendations.similar.length > 0,
)

const tips = [
  '先浏览课程章节，再向 AI 学伴提问，答案会附带资料引用。',
  '浏览资料后，首页会生成同章节与相似资料推荐。',
  '把个人学习资料放进知识库，问答时可以选择个人库范围。',
]

async function load() {
  loading.value = true
  try {
    const body = await getStudentHome()
    home.value = { ...emptyHome(), ...(body?.data || {}) }
    home.value.recommendations = {
      seed: null,
      same_chapter: [],
      similar: [],
      ...(body?.data?.recommendations || {}),
    }
  } catch (error) {
    ElMessage.error(error?.message || '加载首页数据失败')
  } finally {
    loading.value = false
  }
}

async function openMaterial(item) {
  try {
    await markMaterialViewed(item.id)
  } catch {
    // View tracking is best effort; navigation must still work.
  }
  if (item.course_id) {
    router.push(`/student/courses/${item.course_id}`)
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="em-page student-home">
    <section class="hero em-card">
      <div class="hero-copy">
        <span class="em-eyebrow">STUDENT SPACE</span>
        <h1>你好，{{ auth.displayName }} 👋</h1>
        <p>从课程资料出发，向 AI 学伴提问，让每一次学习都有据可循。</p>
        <div class="hero-actions">
          <router-link to="/student/qa">
            <el-button type="primary" size="large">
              <el-icon><ChatDotRound /></el-icon>
              开始提问
            </el-button>
          </router-link>
          <router-link to="/student/courses">
            <el-button size="large" plain>浏览课程</el-button>
          </router-link>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-orbit orbit-one" />
        <div class="hero-orbit orbit-two" />
        <div class="hero-badge">
          <el-icon><Reading /></el-icon>
          <span>知识库问答</span>
        </div>
        <div class="hero-badge hero-badge-alt">
          <el-icon><Aim /></el-icon>
          <span>个性化推荐</span>
        </div>
      </div>
    </section>

    <section class="stat-grid">
      <article v-for="item in stats" :key="item.label" class="stat-card em-card">
        <div class="stat-icon" :class="`tone-${item.tone}`">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <div class="section-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">MY COURSES</span>
            <h2>学习课表</h2>
          </div>
          <router-link to="/student/courses" class="section-link">
            查看全部
          </router-link>
        </div>

        <div v-if="hasCourses" class="course-list">
          <router-link
            v-for="course in home.courses"
            :key="course.id"
            :to="`/student/courses/${course.id}`"
            class="course-row"
          >
            <span class="course-letter">{{ course.title.slice(0, 1) }}</span>
            <div class="course-main">
              <strong>{{ course.title }}</strong>
              <small>
                教师 {{ course.teacher.username }} · {{ course.chapter_count }} 章节 ·
                {{ course.knowledge_count }} 知识点
              </small>
            </div>
            <el-icon class="course-arrow"><Collection /></el-icon>
          </router-link>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon"><el-icon><Notebook /></el-icon></div>
          <h3>还没有加入课程</h3>
          <p>输入教师提供的邀请码加入课程后，这里会显示你的学习课表。</p>
          <router-link to="/student/courses">
            <el-button plain type="primary">去加入课程</el-button>
          </router-link>
        </div>
      </div>

      <div class="section-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">HOT MATERIALS</span>
            <h2>热门资料</h2>
          </div>
          <span class="section-note">已选课程内</span>
        </div>

        <div v-if="home.hot.length" class="material-list">
          <button
            v-for="item in home.hot"
            :key="item.id"
            type="button"
            class="material-row"
            @click="openMaterial(item)"
          >
            <span class="file-badge">{{ fileTypeLabel(item.file_type) }}</span>
            <span class="material-main">
              <strong>{{ item.title }}</strong>
              <small>{{ item.reason }}</small>
            </span>
            <span class="material-course">{{ item.course_title }}</span>
          </button>
        </div>

        <div v-else class="empty-state compact">
          <div class="empty-icon warm"><el-icon><FolderOpened /></el-icon></div>
          <h3>暂无热门资料</h3>
          <p>加入课程后，教师发布的已索引资料会出现在这里。</p>
        </div>
      </div>
    </section>

    <section class="section-card em-card">
      <div class="section-head">
        <div>
          <span class="em-eyebrow">RECOMMENDED FOR YOU</span>
          <h2>为你推荐</h2>
        </div>
        <span v-if="home.recommendations.seed" class="section-note">
          基于《{{ home.recommendations.seed.title }}》
        </span>
        <span v-else class="section-note">浏览资料后自动更新</span>
      </div>

      <div v-if="hasRecommendations" class="recommend-grid">
        <div
          v-for="group in recommendationGroups"
          :key="group.key"
          class="recommend-group"
        >
          <header>
            <h3>{{ group.title }}</h3>
            <p>{{ group.description }}</p>
          </header>
          <button
            v-for="item in group.items"
            :key="item.id"
            type="button"
            class="recommend-row"
            @click="openMaterial(item)"
          >
            <span class="file-badge">{{ fileTypeLabel(item.file_type) }}</span>
            <span class="material-main">
              <strong>{{ item.title }}</strong>
              <small>{{ item.chapter_title || '未关联章节' }}</small>
              <em>{{ item.reason }}</em>
            </span>
            <span class="recommend-meta">
              {{ item.course_title }}
              <small>浏览 {{ item.view_count }}</small>
            </span>
          </button>
        </div>
      </div>

      <div v-else class="empty-state compact">
        <div class="empty-icon"><el-icon><Star /></el-icon></div>
        <h3>推荐正在准备</h3>
        <p>
          {{ home.recommendations.seed
            ? '最近浏览的资料暂时没有同章节或同知识点资料。'
            : '浏览课程资料后，这里会出现同章节与相似资料推荐，并说明推荐理由。' }}
        </p>
        <router-link to="/student/materials">
          <el-button plain type="primary">去浏览资料</el-button>
        </router-link>
      </div>
    </section>

    <section class="section-card em-card">
      <div class="section-head">
        <div>
          <span class="em-eyebrow">PERSONAL LIBRARY</span>
          <h2>知识库最近资料</h2>
        </div>
        <router-link to="/student/knowledge-bases" class="section-link">
          管理知识库
        </router-link>
      </div>

      <div v-if="home.recent_personal.length" class="personal-grid">
        <router-link
          v-for="item in home.recent_personal"
          :key="item.id"
          to="/student/knowledge-bases"
          class="personal-card"
        >
          <span class="file-badge">{{ fileTypeLabel(item.file_type) }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.knowledge_base_name }} · {{ formatDateTime(item.created_at) }}</small>
          </div>
          <el-tag
            size="small"
            :type="item.index_status === 'indexed' ? 'success' : 'info'"
            effect="light"
          >
            {{ item.index_status === 'indexed' ? '已索引' : '索引中' }}
          </el-tag>
        </router-link>
      </div>

      <div v-else class="empty-state compact">
        <div class="empty-icon"><el-icon><FolderOpened /></el-icon></div>
        <h3>个人知识库还是空的</h3>
        <p>上传自己的学习资料，问答时可以选择个人知识库范围。</p>
        <router-link to="/student/knowledge-bases">
          <el-button plain type="primary">去创建资料</el-button>
        </router-link>
      </div>
    </section>

    <section class="tips-card em-card">
      <div class="section-head">
        <div>
          <span class="em-eyebrow">LEARNING TIPS</span>
          <h2>学习小贴士</h2>
        </div>
      </div>
      <ul class="tip-list">
        <li v-for="(tip, index) in tips" :key="tip">
          <span class="tip-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span>{{ tip }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.student-home {
  display: grid;
  gap: 22px;
}

.hero {
  position: relative;
  display: grid;
  min-height: 250px;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  overflow: hidden;
  padding: 40px 44px;
  background:
    radial-gradient(circle at 88% 18%, rgba(22, 119, 255, 0.14), transparent 34%),
    linear-gradient(135deg, #ffffff, #f2f8ff);
}

.hero-copy h1 {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 760;
  letter-spacing: -0.035em;
}

.hero-copy p {
  max-width: 520px;
  margin-top: 10px;
  color: var(--em-text-secondary);
  font-size: 15px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 26px;
}

.hero-visual {
  position: relative;
  min-height: 160px;
}

.hero-orbit {
  position: absolute;
  border: 1px dashed rgba(22, 119, 255, 0.22);
  border-radius: 50%;
}

.orbit-one {
  width: 220px;
  height: 220px;
  right: 24px;
  top: 0;
}

.orbit-two {
  width: 140px;
  height: 140px;
  right: 64px;
  top: 40px;
}

.hero-badge {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid #d9e9ff;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--em-shadow-card);
  color: #2f5f96;
  font-size: 13px;
  font-weight: 600;
}

.hero-badge .el-icon {
  color: var(--em-primary);
  font-size: 18px;
}

.hero-badge {
  right: 120px;
  top: 42px;
}

.hero-badge-alt {
  right: 30px;
  top: 116px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
}

.stat-icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 14px;
  font-size: 22px;
}

.tone-blue {
  background: #e8f2ff;
  color: #1677ff;
}

.tone-green {
  background: #e9fbf1;
  color: #16a34a;
}

.tone-orange {
  background: #fff5e6;
  color: #ea8a0a;
}

.tone-purple {
  background: #f1ecff;
  color: #7c5cff;
}

.stat-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.3;
}

.stat-body span {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.stat-body strong {
  margin-top: 2px;
  font-size: 24px;
  font-weight: 750;
}

.stat-body small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
  gap: 18px;
}

.section-card,
.tips-card {
  padding: 24px 26px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 19px;
  font-weight: 700;
}

.section-note {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f6fd;
  color: #6b7a90;
  font-size: 11px;
}

.section-link {
  color: var(--em-primary);
  font-size: 12px;
  font-weight: 600;
}

.course-list,
.material-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.course-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 13px 14px;
  border-radius: 13px;
  background: #f8faff;
  color: inherit;
  transition: background 0.2s ease;
}

.course-row:hover {
  background: #eef5ff;
}

.course-letter {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 18px;
  font-weight: 750;
}

.course-main,
.material-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  text-align: left;
}

.course-main strong,
.material-main strong {
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-main small,
.material-main small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-arrow {
  color: var(--em-text-muted);
}

.material-row,
.recommend-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 12px;
  border: 0;
  border-radius: 12px;
  background: #f8faff;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: background 0.2s ease;
}

.material-row:hover,
.recommend-row:hover {
  background: #eef5ff;
}

.file-badge {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 9px;
  font-weight: 700;
}

.material-course,
.recommend-meta {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  color: var(--em-text-secondary);
  font-size: 11px;
}

.recommend-meta small {
  color: var(--em-text-muted);
  font-size: 10px;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.recommend-group {
  padding: 16px;
  border: 1px solid #e8effa;
  border-radius: 14px;
  background: #fcfeff;
}

.recommend-group header h3 {
  font-size: 15px;
}

.recommend-group header p {
  margin: 3px 0 12px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.recommend-group .recommend-row + .recommend-row {
  margin-top: 8px;
}

.material-main em {
  display: -webkit-box;
  overflow: hidden;
  color: #3f74ad;
  font-size: 11px;
  font-style: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.personal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.personal-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #edf2fa;
  border-radius: 13px;
  background: #fbfdff;
  color: inherit;
}

.personal-card > div {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
}

.personal-card strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.personal-card small {
  overflow: hidden;
  color: var(--em-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  display: flex;
  min-height: 210px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-state.compact {
  min-height: 180px;
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

.empty-icon.warm {
  background: #fff5e6;
  color: #ea8a0a;
}

.empty-state h3 {
  margin-top: 14px;
  font-size: 16px;
}

.empty-state p {
  max-width: 380px;
  margin: 6px 0 16px;
  color: var(--em-text-secondary);
  font-size: 13px;
}

.tip-list {
  display: grid;
  gap: 12px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

.tip-list li {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8faff;
  color: #52637a;
}

.tip-index {
  color: var(--em-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid,
  .recommend-grid,
  .personal-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 28px 24px;
  }

  .hero-visual {
    display: none;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
