<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

import { listCourses } from '@/api/course'
import { listKnowledgeBases } from '@/api/knowledgeBase'
import { listQaHistory } from '@/api/qa'
import { formatDateTime } from '@/utils/format'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const scope = ref('')
const courseId = ref(null)
const knowledgeBaseId = ref(null)
const courses = ref([])
const knowledgeBases = ref([])

const scopeOptions = [
  { value: 'course', label: '课程问答' },
  { value: 'personal', label: '个人知识库' },
  { value: 'all', label: '综合检索' },
]

async function loadTargets() {
  try {
    const [courseBody, kbBody] = await Promise.all([
      listCourses({ page_size: 100 }),
      listKnowledgeBases(),
    ])
    courses.value = courseBody?.data?.items || []
    knowledgeBases.value = kbBody?.data?.items || []
  } catch {
    // Filters remain usable without the optional target lists.
  }
}

async function load() {
  loading.value = true
  try {
    const body = await listQaHistory({
      page: page.value,
      page_size: pageSize.value,
      scope: scope.value || undefined,
      course_id: courseId.value || undefined,
      knowledge_base_id: knowledgeBaseId.value || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载问答记录失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  scope.value = ''
  courseId.value = null
  knowledgeBaseId.value = null
  search()
}

function scopeLabel(value) {
  if (value === 'course') return '课程知识库'
  if (value === 'personal') return '个人知识库'
  return '综合检索'
}

function referenceScopeLabel(reference) {
  return reference.scope === 'personal' ? '个人资料' : '课程资料'
}

function scoreText(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return ''
  return `匹配 ${Math.round(value * 100)}%`
}

onMounted(async () => {
  await Promise.all([loadTargets(), load()])
})
</script>

<template>
  <div class="em-page qa-history">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">Q&A HISTORY</span>
        <h1>问答记录</h1>
        <p>回顾你的问题、AI 答案与引用来源；记录仅本人可见。</p>
      </div>
      <div class="total-chip">
        <strong>{{ total }}</strong>
        <span>条记录</span>
      </div>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-select v-model="scope" class="filter-select" placeholder="全部范围" clearable @change="search">
          <el-option v-for="item in scopeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="courseId"
          class="filter-select wide"
          placeholder="全部课程"
          clearable
          @change="search"
        >
          <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.id" />
        </el-select>
        <el-select
          v-model="knowledgeBaseId"
          class="filter-select wide"
          placeholder="全部知识库"
          clearable
          @change="search"
        >
          <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section v-loading="loading" class="history-list">
      <article v-for="record in items" :key="record.id" class="history-card em-card">
        <div class="history-head">
          <div class="question-line">
            <span class="question-mark">Q</span>
            <h3>{{ record.question }}</h3>
          </div>
          <div class="history-tags">
            <el-tag type="primary" effect="plain" size="small">
              {{ scopeLabel(record.scope) }}
            </el-tag>
            <el-tag
              :type="record.status === 'success' ? 'success' : 'warning'"
              effect="light"
              size="small"
            >
              {{ record.status === 'success' ? '正常' : '服务降级' }}
            </el-tag>
            <el-tag v-if="record.status === 'success' && !record.hit" type="info" effect="light" size="small">
              未找到依据
            </el-tag>
          </div>
        </div>

        <div class="history-meta">
          <span>{{ formatDateTime(record.created_at) }}</span>
          <span v-if="record.course_title">课程：{{ record.course_title }}</span>
          <span v-if="record.knowledge_base_name">知识库：{{ record.knowledge_base_name }}</span>
          <span v-if="record.latency_ms">{{ record.latency_ms }} ms</span>
        </div>

        <div class="answer-block">
          <span class="answer-mark">A</span>
          <p>{{ record.answer }}</p>
        </div>

        <p v-if="record.scope_note" class="scope-note">{{ record.scope_note }}</p>

        <div v-if="record.references?.length" class="citations">
          <div v-for="reference in record.references" :key="`${reference.material_id}-${reference.page_no}`" class="citation">
            <div class="citation-head">
              <el-tag :type="reference.scope === 'personal' ? 'success' : 'primary'" effect="light" size="small">
                {{ referenceScopeLabel(reference) }}
              </el-tag>
              <strong>{{ reference.title || reference.file_name }}</strong>
              <span v-if="reference.page_no">第 {{ reference.page_no }} 页</span>
              <span v-if="scoreText(reference.score)">{{ scoreText(reference.score) }}</span>
            </div>
            <small>
              {{ reference.course_title || reference.knowledge_base_name || '' }}
              <template v-if="reference.chapter_title">· {{ reference.chapter_title }}</template>
            </small>
            <p v-if="reference.snippet">{{ reference.snippet }}</p>
          </div>
        </div>
      </article>

      <div v-if="!loading && !items.length" class="empty-card em-card">
        <h3>还没有问答记录</h3>
        <p>去 AI 学伴提出第一个问题，回答与引用会自动保存在这里。</p>
        <router-link to="/student/qa">
          <el-button type="primary">开始提问</el-button>
        </router-link>
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
.qa-history {
  display: grid;
  gap: 18px;
}

.total-chip {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 12px 20px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--em-shadow-card);
}

.total-chip strong {
  color: var(--em-primary);
  font-size: 24px;
  font-weight: 750;
}

.total-chip span {
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

.filter-select {
  width: 140px;
}

.filter-select.wide {
  width: 200px;
}

.history-list {
  display: grid;
  gap: 14px;
  min-height: 160px;
}

.history-card {
  padding: 20px 24px;
}

.history-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.question-line {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.question-mark,
.answer-mark {
  display: grid;
  width: 26px;
  height: 26px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
}

.question-mark {
  background: var(--em-primary-soft);
  color: var(--em-primary);
}

.answer-mark {
  background: #e9fbf1;
  color: #15803d;
}

.question-line h3 {
  font-size: 15px;
  line-height: 1.55;
}

.history-tags {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: 6px;
}

.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 10px 0 0 36px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.answer-block {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fbf9;
}

.answer-block p {
  white-space: pre-wrap;
  color: #3c4f45;
  line-height: 1.7;
}

.scope-note {
  margin: 10px 0 0 36px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.citations {
  display: grid;
  gap: 8px;
  margin: 14px 0 0 36px;
}

.citation {
  padding: 10px 12px;
  border: 1px solid var(--em-border);
  border-radius: 11px;
  background: #fbfdff;
}

.citation-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.citation-head strong {
  font-size: 13px;
}

.citation-head span {
  color: var(--em-text-muted);
  font-size: 11px;
}

.citation small {
  display: block;
  margin-top: 3px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.citation p {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--em-text-secondary);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 50px 20px;
  text-align: center;
}

.empty-card h3 {
  font-size: 18px;
}

.empty-card p {
  margin: 6px 0 16px;
  color: var(--em-text-secondary);
  font-size: 13px;
}

.pagination-row {
  display: flex;
  justify-content: center;
}

@media (max-width: 760px) {
  .filter-select,
  .filter-select.wide {
    width: 100%;
  }

  .history-head {
    flex-direction: column;
  }

  .history-meta,
  .citations,
  .scope-note {
    margin-left: 0;
  }
}
</style>
