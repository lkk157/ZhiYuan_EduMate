<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

import { listAuditLogs } from '@/api/admin'
import { detailEntries, formatDateTime } from '@/utils/format'

const ACTION_LABELS = {
  'auth.login.success': '登录成功',
  'auth.login.failed': '登录失败',
  'user.create': '创建用户',
  'user.update': '更新用户',
  'user.enable': '启用用户',
  'user.disable': '禁用用户',
  'user.password.reset': '重置密码',
  'course.create': '创建课程',
  'course.update': '更新课程',
  'course.submit': '提交课程审核',
  'course.approve': '课程审核通过',
  'course.reject': '课程审核驳回',
  'course.invite.rotate': '轮换邀请码',
  'course.invite.toggle': '启停邀请码',
  'course.student.add': '添加学生',
  'course.student.remove': '移出学生',
  'course.join': '加入课程',
  'material.upload': '上传资料',
  'material.approve': '资料审核通过',
  'material.reject': '资料审核驳回',
  'material.index.retry': '重试资料索引',
  'material.delete': '删除资料',
}

const actionOptions = Object.entries(ACTION_LABELS).map(([value, label]) => ({
  value,
  label,
}))

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', action: '', status: '' })

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

async function load() {
  loading.value = true
  try {
    const body = await listAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      action: filters.action || undefined,
      status: filters.status || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载审计日志失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.keyword = ''
  filters.action = ''
  filters.status = ''
  search()
}

function onSizeChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="em-page audit-page">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">AUDIT TRAIL</span>
        <h1>审计日志</h1>
        <p>记录登录、用户治理等关键操作；敏感字段在入库与展示时自动脱敏。</p>
      </div>
      <div class="audit-total">
        <strong>{{ total }}</strong>
        <span>条记录</span>
      </div>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-input
          v-model="filters.keyword"
          class="keyword-input"
          placeholder="搜索操作人或动作"
          :prefix-icon="Search"
          clearable
          @keyup.enter="search"
          @clear="search"
        />
        <el-select
          v-model="filters.action"
          placeholder="全部动作"
          clearable
          class="action-select"
        >
          <el-option
            v-for="item in actionOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-select
          v-model="filters.status"
          placeholder="全部结果"
          clearable
          class="filter-select"
        >
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failure" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section v-loading="loading" class="timeline-card em-card">
      <el-timeline v-if="items.length" class="audit-timeline">
        <el-timeline-item
          v-for="log in items"
          :key="log.id"
          :timestamp="formatDateTime(log.created_at)"
          placement="top"
          :type="log.status === 'success' ? 'primary' : 'danger'"
          :hollow="log.status !== 'success'"
        >
          <article class="audit-item">
            <div class="audit-item-head">
              <div class="audit-title">
                <span
                  class="action-badge"
                  :class="log.status === 'success' ? 'is-success' : 'is-failure'"
                >
                  {{ actionLabel(log.action) }}
                </span>
                <strong>{{ log.username || '匿名' }}</strong>
                <span class="action-code">{{ log.action }}</span>
              </div>
              <el-tag
                :type="log.status === 'success' ? 'success' : 'danger'"
                effect="light"
              >
                {{ log.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </div>

            <div class="audit-meta">
              <span v-if="log.target_type">
                对象：{{ log.target_type }}
                <template v-if="log.target_id">#{{ log.target_id }}</template>
              </span>
              <span v-if="log.ip">IP：{{ log.ip }}</span>
              <span>记录 #{{ log.id }}</span>
            </div>

            <div v-if="detailEntries(log.detail).length" class="audit-detail">
              <span
                v-for="[key, value] in detailEntries(log.detail)"
                :key="key"
                class="detail-chip"
              >
                <em>{{ key }}</em>
                {{ value }}
              </span>
            </div>
          </article>
        </el-timeline-item>
      </el-timeline>

      <el-empty
        v-else-if="!loading"
        description="暂无匹配的审计记录"
        :image-size="90"
      />

      <div v-if="items.length" class="table-footer">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="load"
          @size-change="onSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.audit-page {
  display: grid;
  gap: 18px;
}

.audit-total {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 12px 20px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--em-shadow-card);
}

.audit-total strong {
  color: var(--em-primary);
  font-size: 24px;
  font-weight: 750;
}

.audit-total span {
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

.keyword-input {
  width: 240px;
}

.action-select {
  width: 170px;
}

.filter-select {
  width: 130px;
}

.timeline-card {
  min-height: 320px;
  padding: 28px 30px 18px;
}

.audit-timeline {
  padding-left: 4px;
}

.audit-item {
  padding: 16px 20px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fbfdff;
}

.audit-item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.audit-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.audit-title strong {
  font-size: 14px;
}

.action-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.action-badge.is-success {
  background: #e9fbf1;
  color: #15803d;
}

.action-badge.is-failure {
  background: #fef0ef;
  color: #dc2626;
}

.action-code {
  color: var(--em-text-muted);
  font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 11px;
}

.audit-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 10px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.audit-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.detail-chip {
  padding: 4px 10px;
  border-radius: 8px;
  background: #f3f7fd;
  color: #52637a;
  font-size: 12px;
}

.detail-chip em {
  margin-right: 4px;
  color: var(--em-text-muted);
  font-style: normal;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
}

@media (max-width: 760px) {
  .keyword-input,
  .action-select,
  .filter-select {
    width: 100%;
  }

  .filter-row :deep(.el-button) {
    flex: 1;
  }

  .timeline-card {
    padding: 22px 16px 14px;
  }
}
</style>
