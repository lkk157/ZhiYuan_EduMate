<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, FolderOpened, Search } from '@element-plus/icons-vue'

import { listCourses } from '@/api/course'
import { downloadMaterial, listMaterials } from '@/api/material'
import { formatDateTime } from '@/utils/format'
import { fileTypeLabel, formatFileSize } from '@/utils/material'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const courses = ref([])
const courseFilter = ref('')
const keyword = ref('')

async function loadCourses() {
  try {
    const body = await listCourses({ page_size: 100 })
    courses.value = body?.data?.items || []
  } catch {
    courses.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const body = await listMaterials({
      page: page.value,
      page_size: pageSize.value,
      course_id: courseFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载学习资料失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
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

onMounted(async () => {
  await Promise.all([loadCourses(), load()])
})
</script>

<template>
  <div class="em-page student-materials">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">LEARNING MATERIALS</span>
        <h1>学习资料</h1>
        <p>查看并下载已加入课程中通过审核的学习资料。</p>
      </div>
      <div class="total-chip">
        <strong>{{ total }}</strong>
        <span>份资料</span>
      </div>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-select
          v-model="courseFilter"
          class="course-select"
          placeholder="全部课程"
          clearable
          @change="search"
        >
          <el-option
            v-for="course in courses"
            :key="course.id"
            :label="course.title"
            :value="course.id"
          />
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
      </div>
    </section>

    <section class="table-card em-card">
      <el-table v-loading="loading" :data="items">
        <el-table-column label="资料" min-width="280">
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
        <el-table-column label="类型 / 大小" width="120">
          <template #default="{ row }">
            {{ fileTypeLabel(row.file_type) }} · {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="下载" width="80" align="center">
          <template #default="{ row }">{{ row.download_count }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Download" @click="download(row)">
              下载
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="table-empty">
            <div class="empty-icon"><el-icon><FolderOpened /></el-icon></div>
            <h3>还没有可查看的资料</h3>
            <p>加入课程后，教师上传并通过审核的资料会显示在这里。</p>
          </div>
        </template>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.student-materials {
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

.course-select {
  width: 220px;
}

.keyword-input {
  width: 240px;
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

.time-text {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 14px 0;
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 44px 20px;
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
  font-size: 26px;
}

.table-empty h3 {
  margin-top: 14px;
  font-size: 17px;
}

.table-empty p {
  margin-top: 4px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .course-select,
  .keyword-input {
    width: 100%;
  }
}
</style>
