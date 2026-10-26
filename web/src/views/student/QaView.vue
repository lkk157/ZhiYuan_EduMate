<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Promotion, User } from '@element-plus/icons-vue'

import { listCourses } from '@/api/course'
import { listKnowledgeBases } from '@/api/knowledgeBase'
import { askQuestion } from '@/api/qa'
import SourceCitations from '@/components/SourceCitations.vue'

const scope = ref('course')
const courses = ref([])
const knowledgeBases = ref([])
const courseId = ref(null)
const knowledgeBaseId = ref(null)
const question = ref('')
const sending = ref(false)
const chatRef = ref(null)
const messages = ref([
  {
    role: 'assistant',
    welcome: true,
    content:
      '你好，我是 AI 学伴。选择课程或个人知识库后提问，我会在资料中查找依据并附上引用来源。',
  },
])

const scopeOptions = [
  { value: 'course', label: '课程知识库', icon: 'Reading' },
  { value: 'personal', label: '个人知识库', icon: 'Files' },
  { value: 'all', label: '综合检索', icon: 'Search' },
]

const suggestions = [
  '什么是监督学习？',
  '单链表插入的时间复杂度是多少？',
  '过拟合和欠拟合有什么区别？',
]

const showCourseSelect = computed(() => ['course', 'all'].includes(scope.value))
const showKbSelect = computed(() => ['personal', 'all'].includes(scope.value))
const scopeHint = computed(() => {
  if (scope.value === 'course') {
    return '仅检索所选课程中已审核并索引的资料。'
  }
  if (scope.value === 'personal') {
    return '仅检索你在所选个人知识库中上传的资料，内容仅自己可见。'
  }
  return '同时检索所选课程与个人知识库；至少选择其中一个。'
})

async function loadTargets() {
  try {
    const [courseBody, kbBody] = await Promise.all([
      listCourses({ page_size: 100 }),
      listKnowledgeBases(),
    ])
    courses.value = courseBody?.data?.items || []
    knowledgeBases.value = kbBody?.data?.items || []
    courseId.value = courses.value[0]?.id ?? null
    knowledgeBaseId.value = knowledgeBases.value[0]?.id ?? null
    if (!courses.value.length && knowledgeBases.value.length) {
      scope.value = 'personal'
    }
  } catch (error) {
    ElMessage.error(error?.message || '加载问答范围失败')
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function fillSuggestion(text) {
  question.value = text
}

function buildPayload(text) {
  const payload = { question: text, scope: scope.value }
  if (scope.value === 'course' || scope.value === 'all') {
    if (courseId.value) payload.course_id = courseId.value
  }
  if (scope.value === 'personal' || scope.value === 'all') {
    if (knowledgeBaseId.value) payload.knowledge_base_id = knowledgeBaseId.value
  }
  return payload
}

function validateTarget() {
  if (scope.value === 'course' && !courseId.value) {
    ElMessage.warning('请先选择课程')
    return false
  }
  if (scope.value === 'personal' && !knowledgeBaseId.value) {
    ElMessage.warning('请先选择个人知识库')
    return false
  }
  if (scope.value === 'all' && !courseId.value && !knowledgeBaseId.value) {
    ElMessage.warning('综合检索至少选择一个课程或知识库')
    return false
  }
  return true
}

async function send() {
  const text = question.value.trim()
  if (!text) {
    ElMessage.warning('请输入问题')
    return
  }
  if (!validateTarget()) return

  messages.value.push({ role: 'user', content: text, time: new Date() })
  question.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const body = await askQuestion(buildPayload(text))
    messages.value.push({
      role: 'assistant',
      content: body?.data?.answer || '未获取到答案',
      record: body?.data || null,
      time: new Date(),
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: error?.message || '问答失败，请稍后重试',
      error: true,
      time: new Date(),
    })
    ElMessage.error(error?.message || '问答失败')
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

onMounted(loadTargets)
</script>

<template>
  <div class="em-page qa-page">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">AI COMPANION</span>
        <h1>AI 学伴问答</h1>
        <p>基于课程资料与个人知识库回答问题，并给出可追溯的引用来源。</p>
      </div>
    </div>

    <section class="scope-card em-card">
      <div class="scope-tabs">
        <button
          v-for="item in scopeOptions"
          :key="item.value"
          type="button"
          class="scope-tab"
          :class="{ active: scope === item.value }"
          @click="scope = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="scope-controls">
        <el-select
          v-if="showCourseSelect"
          v-model="courseId"
          class="scope-select"
          :placeholder="scope === 'all' ? '课程（可选）' : '选择课程'"
          :clearable="scope === 'all'"
        >
          <el-option
            v-for="course in courses"
            :key="course.id"
            :label="course.title"
            :value="course.id"
          />
        </el-select>
        <el-select
          v-if="showKbSelect"
          v-model="knowledgeBaseId"
          class="scope-select"
          :placeholder="scope === 'all' ? '个人知识库（可选）' : '选择个人知识库'"
          :clearable="scope === 'all'"
        >
          <el-option
            v-for="kb in knowledgeBases"
            :key="kb.id"
            :label="kb.name"
            :value="kb.id"
          />
        </el-select>
        <span class="scope-hint">{{ scopeHint }}</span>
      </div>
    </section>

    <section class="chat-card em-card">
      <div ref="chatRef" class="message-list">
        <article
          v-for="(message, index) in messages"
          :key="index"
          class="message"
          :class="message.role"
        >
          <div v-if="message.role === 'assistant'" class="message-avatar">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="message-body">
            <div v-if="message.role === 'assistant' && !message.welcome" class="message-meta">
              <el-tag v-if="message.error" type="danger" effect="light" size="small">
                请求失败
              </el-tag>
              <el-tag
                v-else-if="message.record?.status === 'degraded'"
                type="warning"
                effect="light"
                size="small"
              >
                服务降级
              </el-tag>
              <el-tag
                v-else-if="message.record && !message.record.hit"
                type="info"
                effect="light"
                size="small"
              >
                未找到依据
              </el-tag>
              <el-tag
                v-else-if="message.record"
                type="success"
                effect="light"
                size="small"
              >
                已找到依据
              </el-tag>
              <span v-if="message.record?.latency_ms">
                {{ message.record.latency_ms }} ms
              </span>
            </div>
            <p class="message-text">{{ message.content }}</p>

            <p v-if="message.record?.scope_note" class="scope-note">
              {{ message.record.scope_note }}
            </p>

            <SourceCitations
              v-if="message.record?.references?.length"
              class="message-sources"
              :references="message.record.references"
            />
          </div>
          <div v-if="message.role === 'user'" class="message-avatar user-avatar">
            <el-icon><User /></el-icon>
          </div>
        </article>

        <article v-if="sending" class="message assistant">
          <div class="message-avatar"><el-icon><ChatDotRound /></el-icon></div>
          <div class="message-body">
            <div class="typing"><span /><span /><span /></div>
          </div>
        </article>
      </div>

      <div class="suggestions">
        <button
          v-for="item in suggestions"
          :key="item"
          type="button"
          class="suggestion"
          @click="fillSuggestion(item)"
        >
          {{ item }}
        </button>
      </div>

      <div class="composer">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          resize="none"
          placeholder="输入你的问题，例如：什么是监督学习？"
          @keydown.enter.exact.prevent="send"
        />
        <div class="composer-actions">
          <span class="composer-hint">Enter 发送，Shift + Enter 换行</span>
          <el-button
            type="primary"
            class="send-button"
            :icon="Promotion"
            :loading="sending"
            @click="send"
          >
            发送
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.qa-page {
  display: grid;
  gap: 18px;
}

.scope-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 20px;
}

.scope-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: #f1f6fd;
}

.scope-tab {
  padding: 8px 18px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #62738a;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.scope-tab.active {
  background: #fff;
  color: var(--em-primary);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.16);
}

.scope-controls {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.scope-select {
  width: 200px;
}

.scope-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

.chat-card {
  display: flex;
  min-height: 560px;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  display: flex;
  max-height: 520px;
  flex: 1;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  padding: 26px 28px 18px;
}

.message {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message.user {
  justify-content: flex-end;
}

.message-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--em-primary), #61a5ff);
  color: #fff;
  font-size: 17px;
}

.user-avatar {
  background: linear-gradient(135deg, #22c55e, #7ee2a0);
}

.message-body {
  max-width: min(760px, 78%);
  padding: 14px 16px;
  border-radius: 16px;
  background: #f6f9fe;
  border: 1px solid #e8f0fb;
}

.message.user .message-body {
  background: linear-gradient(135deg, var(--em-primary), #4c93ff);
  border-color: transparent;
  color: #fff;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--em-text-muted);
  font-size: 11px;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
}

.scope-note {
  margin-top: 8px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.message-sources {
  margin-top: 14px;
}

.typing {
  display: flex;
  gap: 5px;
  padding: 6px 2px;
}

.typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #9db7d8;
  animation: bounce 1.2s infinite ease-in-out;
}

.typing span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  40% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 28px 12px;
}

.suggestion {
  padding: 6px 12px;
  border: 1px solid var(--em-border);
  border-radius: 999px;
  background: #fff;
  color: var(--em-text-secondary);
  cursor: pointer;
  font-size: 12px;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.suggestion:hover {
  border-color: #b9d4ff;
  color: var(--em-primary);
}

.composer {
  padding: 14px 20px 18px;
  border-top: 1px solid var(--em-border);
  background: #fbfdff;
}

.composer :deep(.el-textarea__inner) {
  border-radius: 14px;
  background: #fff;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.composer-hint {
  color: var(--em-text-muted);
  font-size: 11px;
}

.send-button {
  min-width: 104px;
  border-radius: 11px;
}

@media (max-width: 860px) {
  .scope-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .scope-controls {
    width: 100%;
    justify-content: flex-start;
  }

  .scope-select {
    width: 100%;
  }

  .message-body {
    max-width: 100%;
  }

  .message-list {
    padding-inline: 18px;
  }
}
</style>
