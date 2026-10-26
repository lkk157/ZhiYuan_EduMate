<script setup>
import { ref } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

defineProps({
  references: {
    type: Array,
    default: () => [],
  },
})

const open = ref(false)

function scopeLabel(reference) {
  return reference.scope === 'personal' ? '个人资料' : '课程资料'
}

function scoreText(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return ''
  return `匹配 ${Math.round(value * 100)}%`
}
</script>

<template>
  <div v-if="references.length" class="source-citations">
    <button
      type="button"
      class="sources-toggle"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="sources-label">引用来源</span>
      <span class="sources-count">{{ references.length }} 条</span>
      <el-icon class="sources-chevron" :class="{ open }"><ArrowDown /></el-icon>
    </button>

    <div v-show="open" class="citations">
      <div
        v-for="reference in references"
        :key="`${reference.material_id}-${reference.page_no}-${reference.snippet}`"
        class="citation"
      >
        <div class="citation-head">
          <el-tag
            :type="reference.scope === 'personal' ? 'success' : 'primary'"
            effect="light"
            size="small"
          >
            {{ scopeLabel(reference) }}
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
  </div>
</template>

<style scoped>
.source-citations {
  display: grid;
  gap: 10px;
}

.sources-toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  width: fit-content;
  padding: 6px 11px;
  border: 1px solid #dce8f8;
  border-radius: 999px;
  background: #f8fbff;
  color: #4b6f9b;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.sources-toggle:hover {
  border-color: #b9d4ff;
  background: #f1f7ff;
}

.sources-label {
  font-weight: 600;
}

.sources-count {
  color: var(--em-text-muted);
  font-size: 11px;
}

.sources-chevron {
  font-size: 12px;
  transition: transform 0.18s ease;
}

.sources-chevron.open {
  transform: rotate(180deg);
}

.citations {
  display: grid;
  gap: 10px;
}

.citation {
  padding: 10px 12px;
  border: 1px solid var(--em-border);
  border-radius: 11px;
  background: #fff;
}

.citation-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.citation-head strong {
  color: var(--em-text);
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
  margin-top: 6px;
  overflow: hidden;
  color: var(--em-text-secondary);
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
</style>
